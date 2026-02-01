"""RAG operation handlers for semantic search."""

import logging
from typing import Any
from mcp.types import TextContent

from ..core.rag_manager import RAGManager

logger = logging.getLogger(__name__)


def handle_index_note(rag_manager: RAGManager, arguments: Any) -> list[TextContent]:
    """Handle index_note tool."""
    filename = arguments.get("filename")

    if not filename:
        return [TextContent(
            type="text",
            text="Error: filename is required"
        )]

    if not rag_manager.is_available():
        return [TextContent(
            type="text",
            text="Error: RAG functionality not available. Install dependencies with: pip install chromadb sentence-transformers"
        )]

    try:
        success = rag_manager.index_note(filename)

        if success:
            return [TextContent(
                type="text",
                text=f"✓ Indexed note: {filename}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"Error: Failed to index note '{filename}'. Check if the note exists."
            )]

    except Exception as e:
        logger.error(f"Error indexing note: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]


def handle_search_notes(rag_manager: RAGManager, arguments: Any) -> list[TextContent]:
    """Handle search_notes tool."""
    query = arguments.get("query")
    limit = arguments.get("limit", 5)
    min_confidence = arguments.get("min_confidence")
    note_type = arguments.get("note_type")

    if not query:
        return [TextContent(
            type="text",
            text="Error: query is required"
        )]

    if not rag_manager.is_available():
        return [TextContent(
            type="text",
            text="Error: RAG functionality not available. Install dependencies with: pip install chromadb sentence-transformers"
        )]

    try:
        results = rag_manager.search_notes(
            query=query,
            limit=limit,
            min_confidence=min_confidence,
            note_type=note_type
        )

        if not results:
            return [TextContent(
                type="text",
                text=f"No results found for query: '{query}'"
            )]

        # Format results as markdown
        lines = [f"# Search Results for: '{query}'", ""]

        for i, result in enumerate(results, 1):
            similarity_pct = result['similarity'] * 100 if result['similarity'] is not None else 0
            lines.append(f"## {i}. {result['title']}")
            lines.append(f"- **File**: {result['filename']}")
            lines.append(f"- **Similarity**: {similarity_pct:.1f}%")
            lines.append(f"- **Type**: {result['note_type']}")

            if result.get('confidence_score') is not None:
                lines.append(f"- **Confidence**: {result['confidence_score']:.2f}")

            if result.get('source_count') is not None and result['source_count'] > 0:
                lines.append(f"- **Sources**: {result['source_count']}")

            lines.append("")

        return [TextContent(
            type="text",
            text="\n".join(lines)
        )]

    except Exception as e:
        logger.error(f"Error searching notes: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]


def handle_remove_from_index(rag_manager: RAGManager, arguments: Any) -> list[TextContent]:
    """Handle remove_from_index tool."""
    filename = arguments.get("filename")

    if not filename:
        return [TextContent(
            type="text",
            text="Error: filename is required"
        )]

    if not rag_manager.is_available():
        return [TextContent(
            type="text",
            text="Error: RAG functionality not available. Install dependencies with: pip install chromadb sentence-transformers"
        )]

    try:
        success = rag_manager.remove_from_index(filename)

        if success:
            return [TextContent(
                type="text",
                text=f"✓ Removed from index: {filename}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"Error: Failed to remove '{filename}' from index"
            )]

    except Exception as e:
        logger.error(f"Error removing from index: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]


def handle_reindex_all_notes(rag_manager: RAGManager, arguments: Any) -> list[TextContent]:
    """Handle reindex_all_notes tool."""
    if not rag_manager.is_available():
        return [TextContent(
            type="text",
            text="Error: RAG functionality not available. Install dependencies with: pip install chromadb sentence-transformers"
        )]

    try:
        stats = rag_manager.reindex_all_notes()

        lines = [
            "# Reindexing Complete",
            "",
            f"- **Total notes**: {stats['total']}",
            f"- **Successfully indexed**: {stats['indexed']}",
            f"- **Failed**: {stats['failed']}"
        ]

        if stats['failed'] > 0:
            lines.append("")
            lines.append("⚠️ Some notes failed to index. Check logs for details.")

        return [TextContent(
            type="text",
            text="\n".join(lines)
        )]

    except Exception as e:
        logger.error(f"Error reindexing notes: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]


def handle_get_index_stats(rag_manager: RAGManager, arguments: Any) -> list[TextContent]:
    """Handle get_index_stats tool."""
    try:
        stats = rag_manager.get_index_stats()

        if not stats.get('available', False):
            error_msg = stats.get('error', 'Unknown error')
            return [TextContent(
                type="text",
                text=f"Error: RAG not available - {error_msg}\n\nInstall dependencies with: pip install chromadb sentence-transformers"
            )]

        lines = [
            "# Vector Database Statistics",
            "",
            f"- **Indexed notes**: {stats['indexed_count']}",
            f"- **Embedding provider**: {stats['embedding_provider']}",
            f"- **Embedding model**: {stats['embedding_model']}",
            f"- **Storage path**: {stats['storage_path']}",
            f"- **Status**: {'Available' if stats['available'] else 'Not Available'}"
        ]

        return [TextContent(
            type="text",
            text="\n".join(lines)
        )]

    except Exception as e:
        logger.error(f"Error getting index stats: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: {e}"
        )]
