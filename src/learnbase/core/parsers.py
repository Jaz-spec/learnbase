"""Parsing utilities for frontmatter fields."""

from datetime import datetime
from typing import Any


def parse_datetime(value: Any, default: datetime) -> datetime:
    """Parse datetime from string or datetime object.

    Args:
        value: Value to parse (datetime, string)
        default: Default value

    Returns:
        Parsed datetime or default
    """
    if value is None:
        return default
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def parse_review(value: Any, default: datetime | None = None) -> datetime | None:
    """Parse datetime from string or datetime object.

    Args:
        value: Value to parse (datetime, string, or None)
        default: Default value if None

    Returns:
        Parsed datetime or default
    """
    if value is None:
        return default
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))

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
