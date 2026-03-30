"""Parse active-context/index.md for task categorization."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class ContextParser:
    """Parse active-context/index.md for categorization context."""

    def __init__(self, index_path: Optional[Path] = None):
        """
        Initialize ContextParser.

        Args:
            index_path: Path to index.md (default: ~/.learnbase/active-context/index.md)
        """
        if index_path is None:
            index_path = Path.home() / ".learnbase" / "active-context" / "index.md"

        self.index_path = Path(index_path)

    def get_context(self) -> Dict:
        """
        Parse index.md and return structured context.

        Returns:
            Dictionary with structure:
            {
                'projects': [
                    {
                        'name': 'LearnBase',
                        'workspace': 'personal',
                        'people': ['Dan', 'Sarah'],
                        'keywords': ['learnbase', 'task system', ...]
                    }
                ],
                'people': {
                    'Dan': ['Client X', 'LearnBase'],
                    'Sarah': ['work projects', 'portfolio']
                },
                'current_priorities': [...]
            }

        Raises:
            FileNotFoundError: If index.md doesn't exist
        """
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"Active context index not found: {self.index_path}\n"
                f"Please create an index.md file in ~/.learnbase/active-context/"
            )

        try:
            with open(self.index_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading index.md: {e}")
            raise

        # Parse projects section
        projects = self._parse_projects(content)

        # Parse people section
        people = self._parse_people(content)

        # Parse current context section
        current_priorities = self._parse_current_context(content)

        return {
            'projects': projects,
            'people': people,
            'current_priorities': current_priorities
        }

    def _parse_projects(self, content: str) -> List[Dict]:
        """
        Parse projects from index.md.

        Args:
            content: Full content of index.md

        Returns:
            List of project dictionaries
        """
        projects = []

        # Find Active Projects section
        projects_match = re.search(r'## Active Projects\s*(.*?)(?=##|\Z)', content, re.DOTALL)
        if not projects_match:
            logger.warning("No Active Projects section found in index.md")
            return projects

        projects_section = projects_match.group(1)

        # Parse each project (###  ProjectName (workspace))
        project_pattern = r'###\s+([^\(]+)\s*\(([^)]+)\)\s*(.*?)(?=###|\Z)'
        for match in re.finditer(project_pattern, projects_section, re.DOTALL):
            name = match.group(1).strip()
            workspace = match.group(2).strip()
            details = match.group(3).strip()

            # Extract people
            people = []
            people_match = re.search(r'\*\*People:\*\*\s*([^\n]+)', details)
            if people_match:
                people_text = people_match.group(1)
                # Extract names (comma-separated, may have context in parens)
                people = [
                    p.split('(')[0].strip()
                    for p in people_text.split(',')
                ]

            # Extract keywords from focus and recent
            keywords = []
            keywords.append(name.lower())

            focus_match = re.search(r'\*\*Focus:\*\*\s*([^\n]+)', details)
            if focus_match:
                focus_text = focus_match.group(1).lower()
                keywords.extend(focus_text.split())

            recent_match = re.search(r'\*\*Recent:\*\*\s*([^\n]+)', details)
            if recent_match:
                recent_text = recent_match.group(1).lower()
                keywords.extend(recent_text.split())

            # Clean keywords (remove punctuation, deduplicate)
            keywords = list(set([
                re.sub(r'[^\w\s-]', '', k).strip()
                for k in keywords
                if len(k) > 2
            ]))

            projects.append({
                'name': name,
                'workspace': workspace,
                'people': people,
                'keywords': keywords
            })

        return projects

    def _parse_people(self, content: str) -> Dict[str, List[str]]:
        """
        Parse people section from index.md.

        Args:
            content: Full content of index.md

        Returns:
            Dictionary mapping person name to list of projects/context
        """
        people = {}

        # Find People section
        people_match = re.search(r'## People\s*(.*?)(?=##|\Z)', content, re.DOTALL)
        if not people_match:
            logger.warning("No People section found in index.md")
            return people

        people_section = people_match.group(1)

        # Parse each person (- **Name:** context)
        person_pattern = r'-\s*\*\*([^:]+):\*\*\s*([^\n]+)'
        for match in re.finditer(person_pattern, people_section):
            name = match.group(1).strip()
            context = match.group(2).strip()

            # Extract project references from context
            projects = [
                proj.strip()
                for proj in context.split(',')
            ]

            people[name] = projects

        return people

    def _parse_current_context(self, content: str) -> List[str]:
        """
        Parse current context section from index.md.

        Args:
            content: Full content of index.md

        Returns:
            List of current priority keywords
        """
        priorities = []

        # Find Current Context section
        context_match = re.search(r'## Current Context\s*(.*?)(?=##|\Z)', content, re.DOTALL)
        if not context_match:
            logger.warning("No Current Context section found in index.md")
            return priorities

        context_text = context_match.group(1).lower()

        # Extract keywords (simple word tokenization)
        words = re.findall(r'\b\w+\b', context_text)
        priorities = [w for w in words if len(w) > 3]

        return list(set(priorities))

    # ================================================================
    # Matching Methods
    # ================================================================

    def match_project(self, text: str) -> Tuple[Optional[str], float]:
        """
        Match text to project with confidence score.

        Args:
            text: Text to match (user's task description)

        Returns:
            Tuple of (project_name, confidence) or (None, 0.0) if no match
        """
        try:
            context = self.get_context()
        except FileNotFoundError:
            logger.warning("Index.md not found, cannot match project")
            return None, 0.0

        text_lower = text.lower()
        best_match = None
        best_score = 0.0

        for project in context['projects']:
            score = 0.0

            # Check for exact project name match
            if project['name'].lower() in text_lower:
                score += 0.5

            # Check for keyword matches
            keyword_matches = sum(1 for kw in project['keywords'] if kw in text_lower)
            if keyword_matches > 0:
                score += min(0.5, keyword_matches * 0.1)

            # Check for people mentions
            for person in project['people']:
                if person.lower() in text_lower:
                    score += 0.3
                    break

            if score > best_score:
                best_score = score
                best_match = project['name']

        # Normalize score to 0-1 range
        confidence = min(1.0, best_score)

        return best_match, confidence

    def match_workspace(self, project: Optional[str], text: str) -> Tuple[str, float]:
        """
        Infer workspace from project + text.

        Args:
            project: Project name (if matched)
            text: Text to analyze

        Returns:
            Tuple of (workspace, confidence)
        """
        # If project matched, use its workspace
        if project:
            try:
                context = self.get_context()
                for proj in context['projects']:
                    if proj['name'] == project:
                        return proj['workspace'], 0.9
            except FileNotFoundError:
                pass

        # Otherwise, use keyword matching
        text_lower = text.lower()

        # Check for workspace indicators
        work_keywords = ['work', 'office', 'meeting', 'report', 'presentation', 'team']
        contract_keywords = ['client', 'contract', 'freelance', 'consulting']
        personal_keywords = ['personal', 'home', 'hobby', 'learning', 'study']

        work_score = sum(1 for kw in work_keywords if kw in text_lower)
        contract_score = sum(1 for kw in contract_keywords if kw in text_lower)
        personal_score = sum(1 for kw in personal_keywords if kw in text_lower)

        max_score = max(work_score, contract_score, personal_score)

        if max_score == 0:
            return 'personal', 0.3  # Default to personal with low confidence

        if work_score == max_score:
            return 'work', min(0.7, 0.4 + max_score * 0.1)
        elif contract_score == max_score:
            return 'contract', min(0.7, 0.4 + max_score * 0.1)
        else:
            return 'personal', min(0.7, 0.4 + max_score * 0.1)

    def detect_categories(self, text: str) -> Tuple[List[str], float]:
        """
        Detect categories from text patterns.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (categories, avg_confidence)

        Categories:
        - "call X", "meet with X", "email X" → [people]
        - "idea about", "we should", "what if" → [idea]
        - "implement", "fix", "update", "build" → [project]
        - "remember to", "don't forget", "make sure" → [admin]
        """
        text_lower = text.lower()
        categories = []
        scores = []

        # People category patterns
        people_patterns = [
            r'\b(call|email|meet|contact|message|talk to|reach out to)\b',
            r'\b(with|about)\s+[A-Z][a-z]+',  # Name after preposition
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in people_patterns):
            categories.append('people')
            scores.append(0.9)

        # Idea category patterns
        idea_patterns = [
            r'\b(idea|concept|thought|suggestion)\b',
            r'\b(we should|what if|maybe|consider)\b',
            r'\b(brainstorm|explore|research)\b',
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in idea_patterns):
            categories.append('idea')
            scores.append(0.8)

        # Project category patterns
        project_patterns = [
            r'\b(implement|build|create|develop|fix|update|refactor)\b',
            r'\b(add|remove|change|modify|improve)\b',
            r'\b(deploy|release|launch|ship)\b',
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in project_patterns):
            categories.append('project')
            scores.append(0.85)

        # Admin category patterns
        admin_patterns = [
            r'\b(remember|don\'t forget|make sure|remind)\b',
            r'\b(schedule|book|arrange|organize)\b',
            r'\b(submit|file|send|complete)\b',
        ]
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in admin_patterns):
            categories.append('admin')
            scores.append(0.8)

        # Calculate average confidence
        avg_confidence = sum(scores) / len(scores) if scores else 0.0

        # Default to admin if no categories detected
        if not categories:
            categories = ['admin']
            avg_confidence = 0.5

        return categories, avg_confidence
