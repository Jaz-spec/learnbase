"""Parsing utilities for frontmatter fields."""

from datetime import datetime
from typing import Any


def _strip_timezone(dt: datetime) -> datetime:
    """Strip timezone info to ensure offset-naive datetime.

    The codebase uses datetime.now() (offset-naive) throughout,
    but YAML parsers may return offset-aware datetimes when loading
    ISO 8601 strings from frontmatter. This helper ensures consistency
    to prevent 'can't compare offset-naive and offset-aware datetimes' errors.

    Args:
        dt: datetime that may or may not have timezone info

    Returns:
        Offset-naive datetime (tzinfo removed if present)
    """
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def parse_datetime(value: Any, default: datetime) -> datetime:
    """Parse datetime from string or datetime object.

    Args:
        value: Value to parse (datetime, string)
        default: Default value

    Returns:
        Parsed datetime or default (always offset-naive)
    """
    if value is None:
        return default
    if isinstance(value, datetime):
        return _strip_timezone(value)
    return _strip_timezone(datetime.fromisoformat(str(value)))


def parse_review(value: Any, default: datetime | None = None) -> datetime | None:
    """Parse datetime from string or datetime object.

    Args:
        value: Value to parse (datetime, string, or None)
        default: Default value if None

    Returns:
        Parsed datetime or default (always offset-naive if not None)
    """
    if value is None:
        return default
    if isinstance(value, datetime):
        return _strip_timezone(value)
    return _strip_timezone(datetime.fromisoformat(str(value)))

def parse_float(value: Any, default: float = 0.0) -> float:
    """Parse float from string or numeric value.

    Args:
        value: Value to parse
        default: Default value if None

    Returns:
        Parsed float or default
    """
    if value is None:
        return default
    return float(value)


def parse_int(value: Any, default: int = 0) -> int:
    """Parse int from string or numeric value.

    Args:
        value: Value to parse
        default: Default value if None

    Returns:
        Parsed int or default
    """
    if value is None:
        return default
    return int(value)


def parse_optional_float(value: Any) -> float | None:
    """Parse optional float from string or numeric value.

    Args:
        value: Value to parse

    Returns:
        Parsed float or None
    """
    if value is None:
        return None
    return float(value)


def parse_list(value: Any, default: list | None = None) -> list:
    """Parse list, returning default if None.

    Args:
        value: Value to parse
        default: Default value if None

    Returns:
        Parsed list or default (empty list if default not provided)
    """
    if value is None:
        return default if default is not None else []
    return list(value)


def parse_dict(value: Any, default: dict | None = None) -> dict:
    """Parse dict, returning default if None.

    Args:
        value: Value to parse
        default: Default value if None

    Returns:
        Parsed dict or default (empty dict if default not provided)
    """
    if value is None:
        return default if default is not None else {}
    return dict(value)


def parse_categories(value: Any, default: list[str] | None = None) -> list[str]:
    """Parse categories list with validation.

    Args:
        value: Value to parse (list of strings)
        default: Default value if None

    Returns:
        Parsed list of category strings or default (empty list if default not provided)
    """
    if value is None:
        return default if default is not None else []

    # Ensure it's a list
    if not isinstance(value, list):
        return [str(value)]

    # Ensure all items are strings
    return [str(item) for item in value]


def parse_workspace(value: Any, default: str = "personal") -> str:
    """Parse and validate workspace enum.

    Args:
        value: Value to parse
        default: Default workspace if None or invalid

    Returns:
        Valid workspace string: "work", "personal", or "contract"
    """
    if value is None:
        return default

    workspace = str(value).lower()
    if workspace in ["work", "personal", "contract"]:
        return workspace

    return default


def parse_confidence(value: Any) -> dict[str, float]:
    """Parse confidence scores dict.

    Args:
        value: Value to parse (dict with string keys and float values)

    Returns:
        Parsed dict with float values or empty dict
    """
    if value is None:
        return {}

    if not isinstance(value, dict):
        return {}

    # Ensure all values are floats
    return {str(k): float(v) for k, v in value.items()}
