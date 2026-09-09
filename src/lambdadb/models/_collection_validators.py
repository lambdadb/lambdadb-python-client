"""Shared validation for collection metadata."""

from __future__ import annotations

import re
from typing import Dict, Optional

_BLANK_TAG_VALUE = re.compile(
    r"^[\u0009-\u000d\u001c-\u0020\u1680\u2000-\u2006"
    r"\u2008-\u200a\u2028\u2029\u205f\u3000]*$"
)


def validate_metadata_tags(value: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Validate collection metadata tag limits from the public contract."""
    if value is None:
        return value
    if len(value) > 5:
        raise ValueError("tags may contain at most five entries")
    for key, item in value.items():
        if not 1 <= len(key) <= 63 or any(
            char
            not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-"
            for char in key
        ):
            raise ValueError("tag keys must match ^[A-Za-z0-9_.-]{1,63}$")
        if (
            not 1 <= len(item) <= 127
            or any(char in item for char in ":#,")
            or _BLANK_TAG_VALUE.fullmatch(item)
        ):
            raise ValueError(
                "tag values must be 1-127 characters, contain non-whitespace, "
                "and exclude : # ,"
            )
    return value
