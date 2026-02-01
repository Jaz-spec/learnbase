"""RAG manager for semantic search using ChromaDB."""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
import hashlib

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not available. Install with: pip install chromadb")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available. Install with: pip install sentence-transformers")

from .note_manager import NoteManager
from .models import Note, ReviewNote, ReferenceNote, EvergreenNote


class RAGManager:
    """Manages vector database operations for semantic search."""

    COLLECTION_NAME = "learnbase_notes"
    DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

    def __init__(
        self,
        note_manager: NoteManager,
        vector_db_dir: Optional[Path] = None,
        embedding_provider: Literal['openai', 'sentence-transformers'] = 'sentence-transformers',
        embedding_model: Optional[str] = None
    ):
        """
        Initialize RAGManager.

        Args:
            note_manager: NoteManager instance for reading notes
            vector_db_dir: Directory for ChromaDB storage (default: ~/.learnbase/vector_db)
            embedding_provider: 'openai' or 'sentence-transformers'
            embedding_model: Model name (default: all-MiniLM-L6-v2 for sentence-transformers)
        """
        self.note_manager = note_manager
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model or self.DEFAULT_EMBEDDING_MODEL

        # Set up vector database directory
        if vector_db_dir is None:
            vector_db_dir = Path.home() / ".learnbase" / "vector_db"
        self.vector_db_dir = Path(vector_db_dir)
        self.vector_db_dir.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = None
        self.collection = None
        self.embedding_function = None

        if not CHROMADB_AVAILABLE:
            logger.error("ChromaDB not available. RAG functionality disabled.")
            return

        try:
            self._initialize_chromadb()
            logger.info(f"Initialized RAGManager with {embedding_provider} embeddings")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}", exc_info=True)

    def _initialize_chromadb(self):
        """Initialize ChromaDB client and collection."""
        # Create persistent client
        self.client = chromadb.PersistentClient(
            path=str(self.vector_db_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Set up embedding function
        if self.embedding_provider == 'openai':
            self.embedding_function = self._create_openai_embedding_function()
        else:  # sentence-transformers
            self.embedding_function = self._create_sentence_transformer_embedding_function()

        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name=self.COLLECTION_NAME,
                embedding_function=self.embedding_function
            )
            logger.debug(f"Loaded existing collection: {self.COLLECTION_NAME}")
        except Exception:
            self.collection = self.client.create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection: {self.COLLECTION_NAME}")

    def _create_sentence_transformer_embedding_function(self):
        """Create sentence-transformers embedding function."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers not installed. Install with: pip install sentence-transformers")

        # ChromaDB has built-in sentence-transformers support
        from chromadb.utils import embedding_functions

        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self.embedding_model
        )

    def _create_openai_embedding_function(self):
        """Create OpenAI embedding function."""
        import os

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        from chromadb.utils import embedding_functions

        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name=self.embedding_model or "text-embedding-3-small"
        )

    def _prepare_document(self, note: Note) -> str:
        """
        Prepare document text for embedding.

        Combines title and body into a single document.

        Args:
            note: Note instance

        Returns:
            Document text for embedding
        """
        return f"{note.title}\n\n{note.body}"

    def _prepare_metadata(self, note: Note) -> Dict[str, Any]:
        """
        Extract metadata from note.

        Metadata is stored separately from embeddings and can be used for filtering.

        Args:
            note: Note instance

        Returns:
            Metadata dictionary
        """
        metadata = {
            "filename": note.filename,
            "title": note.title,
            "created_at": note.created_at.isoformat(),
        }

        # Add note type
        if isinstance(note, ReviewNote):
            metadata["note_type"] = "review"
            # Add review-specific metadata
            if hasattr(note, 'confidence_score') and note.confidence_score is not None:
                metadata["confidence_score"] = note.confidence_score
            if hasattr(note, 'sources') and note.sources:
                metadata["source_count"] = len(note.sources)
            else:
                metadata["source_count"] = 0
        elif isinstance(note, EvergreenNote):
            metadata["note_type"] = "evergreen"
            metadata["source_count"] = 0
        else:  # ReferenceNote
            metadata["note_type"] = "reference"
            metadata["source_count"] = 0

        return metadata

    def is_available(self) -> bool:
        """Check if RAG functionality is available."""
        return CHROMADB_AVAILABLE and self.client is not None and self.collection is not None

    def index_note(self, filename: str) -> bool:
        """
        Index or update a note in the vector database.

        Args:
            filename: Note filename

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("RAG not available")
            return False

        try:
            # Load note
            note = self.note_manager.get_note(filename)
            if not note:
                logger.error(f"Note not found: {filename}")
                return False

            # Prepare document and metadata
            document = self._prepare_document(note)
            metadata = self._prepare_metadata(note)

            # Upsert to collection (add or update)
            self.collection.upsert(
                ids=[filename],
                documents=[document],
                metadatas=[metadata]
            )

            logger.info(f"Indexed note: {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to index note {filename}: {e}", exc_info=True)
            return False

    def search_notes(
        self,
        query: str,
        limit: int = 5,
        min_confidence: Optional[float] = None,
        note_type: Optional[Literal['review', 'reference', 'evergreen']] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for notes using semantic similarity.

        Args:
            query: Search query
            limit: Maximum number of results
            min_confidence: Minimum confidence score filter (only for review notes)
            note_type: Filter by note type

        Returns:
            List of search results with filename, title, similarity, type, etc.
        """
        if not self.is_available():
            logger.error("RAG not available")
            return []

        try:
            # Build metadata filter
            where = {}
            if note_type:
                where["note_type"] = note_type
            if min_confidence is not None:
                where["confidence_score"] = {"$gte": min_confidence}

            # Query collection
            results = self.collection.query(
                query_texts=[query],
                n_results=limit,
                where=where if where else None
            )

            # Format results
            formatted_results = []
            if results and results['ids'] and results['ids'][0]:
                for i, filename in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results['distances'][0][i] if results.get('distances') else None

                    # Convert distance to similarity score (cosine: similarity = 1 - distance)
                    similarity = 1 - distance if distance is not None else None

                    result = {
                        'filename': filename,
                        'title': metadata.get('title', 'Unknown'),
                        'similarity': similarity,
                        'note_type': metadata.get('note_type', 'unknown'),
                        'confidence_score': metadata.get('confidence_score'),
                        'source_count': metadata.get('source_count', 0),
                        'created_at': metadata.get('created_at')
                    }
                    formatted_results.append(result)

            logger.info(f"Search query '{query}' returned {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            return []

    def remove_from_index(self, filename: str) -> bool:
        """
        Remove a note from the vector database.

        Args:
            filename: Note filename

        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.error("RAG not available")
            return False

        try:
            self.collection.delete(ids=[filename])
            logger.info(f"Removed from index: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove {filename} from index: {e}", exc_info=True)
            return False

    def reindex_all_notes(self) -> Dict[str, int]:
        """
        Reindex all notes in the database.

        Clears the collection and rebuilds from scratch.

        Returns:
            Dictionary with stats: total, indexed, failed
        """
        if not self.is_available():
            logger.error("RAG not available")
            return {"total": 0, "indexed": 0, "failed": 0}

        try:
            # Clear collection
            self.client.delete_collection(name=self.COLLECTION_NAME)
            self._initialize_chromadb()

            # Get all notes (review, reference, and evergreen)
            all_notes = self.note_manager.get_all_notes()

            stats = {
                "total": len(all_notes),
                "indexed": 0,
                "failed": 0
            }

            # Index each note
            for note in all_notes:
                if self.index_note(note.filename):
                    stats["indexed"] += 1
                else:
                    stats["failed"] += 1

            logger.info(f"Reindexed all notes: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to reindex all notes: {e}", exc_info=True)
            return {"total": 0, "indexed": 0, "failed": 0}

    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector database.

        Returns:
            Dictionary with indexed_count, embedding_provider, storage_path
        """
        if not self.is_available():
            return {
                "indexed_count": 0,
                "embedding_provider": self.embedding_provider,
                "embedding_model": self.embedding_model,
                "storage_path": str(self.vector_db_dir),
                "available": False,
                "error": "ChromaDB not available"
            }

        try:
            count = self.collection.count()

            return {
                "indexed_count": count,
                "embedding_provider": self.embedding_provider,
                "embedding_model": self.embedding_model,
                "storage_path": str(self.vector_db_dir),
                "available": True
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}", exc_info=True)
            return {
                "indexed_count": 0,
                "embedding_provider": self.embedding_provider,
                "embedding_model": self.embedding_model,
                "storage_path": str(self.vector_db_dir),
                "available": False,
                "error": str(e)
            }
