"""Qdrant filter to LambdaDB query conversion."""

from __future__ import annotations

import math
import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Union

from pydantic import BaseModel

from . import models
from .conversions import point_ids_to_doc_ids
from .errors import QdrantCompatValidationError, UnsupportedQdrantFeatureError

_PLAIN_TERM = re.compile(r"[a-zA-Z0-9_][a-zA-Z0-9_-]*")
_FIELD_PATH = re.compile(r"\w[\w-]*(?:\.\w[\w-]*)*")
_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,3})?(?:Z|[+-][0-9]{2}:[0-5][0-9])"
)
_OPERATORS = {"AND", "OR", "NOT"}


def _fields(value: Any, label: str, allowed: set[str]) -> Dict[str, Any]:
    if isinstance(value, BaseModel):
        # Inspect the concrete model, including extras and nested model subclasses.
        value = {key: item for key, item in value if item is not None}
    if not isinstance(value, dict):
        raise QdrantCompatValidationError(f"{label} must be a model or dict")
    unsupported = value.keys() - allowed
    if unsupported:
        raise UnsupportedQdrantFeatureError(
            f"Unsupported {label} fields: {', '.join(sorted(map(str, unsupported)))}"
        )
    return value


def _literal(value: str) -> str:
    if _PLAIN_TERM.fullmatch(value) and value not in _OPERATORS:
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _is_signed_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and -(2**63) <= value < 2**63


def _match_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str) or _is_signed_integer(value):
        return _literal(str(value))
    raise QdrantCompatValidationError("MatchValue requires a string, boolean, or signed 64-bit integer")


def _query_string(query: str) -> Dict[str, Any]:
    return {"queryString": {"query": query}}


def _group(queries: List[Dict[str, Any]], occur: str) -> Dict[str, Any]:
    if len(queries) == 1:
        return queries[0]
    return {"bool": [{**query, "occur": occur} for query in queries]}


def _range_bound(value: Any) -> str:
    if _is_signed_integer(value):
        return str(value)
    if isinstance(value, float) and math.isfinite(value):
        # The server's numeric point parser consumes decimal notation.
        return format(Decimal(str(value)), "f")
    if isinstance(value, str) and _TIMESTAMP.fullmatch(value):
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise QdrantCompatValidationError("Range timestamp is invalid") from error
        return _literal(value)
    raise QdrantCompatValidationError("Range bounds must be finite numbers or RFC 3339 timestamps")


def _range_query(field: str, range_value: Any) -> Dict[str, Any]:
    bounds = _fields(range_value, "Range", {"gt", "gte", "lt", "lte"})
    lower = [(key, bounds[key]) for key in ("gt", "gte") if bounds.get(key) is not None]
    upper = [(key, bounds[key]) for key in ("lt", "lte") if bounds.get(key) is not None]
    if len(lower) > 1 or len(upper) > 1 or not (lower or upper):
        raise QdrantCompatValidationError("Range requires one or both bounds, with one operator per side")
    if lower and upper and isinstance(lower[0][1], str) != isinstance(upper[0][1], str):
        raise QdrantCompatValidationError("Range bounds must both be numbers or both be timestamps")
    start = _range_bound(lower[0][1]) if lower else "*"
    end = _range_bound(upper[0][1]) if upper else "*"
    left = "{" if lower and lower[0][0] == "gt" else "["
    right = "}" if upper and upper[0][0] == "lt" else "]"
    return _query_string(f"{field}:{left}{start} TO {end}{right}")


def _match_query(field: str, match: Any) -> Dict[str, Any]:
    fields = _fields(match, "Qdrant match", {"value", "any", "except", "except_", "text"})
    if "except" in fields or "except_" in fields:
        raise UnsupportedQdrantFeatureError("MatchExcept is unsupported for Qdrant filters")
    if len(fields) != 1:
        raise QdrantCompatValidationError("FieldCondition match requires exactly one matcher")
    if "value" in fields:
        return _query_string(f"{field}:{_match_value(fields['value'])}")
    if "any" in fields:
        values = fields["any"]
        if not isinstance(values, list) or not values or not (
            all(isinstance(value, str) for value in values) or all(_is_signed_integer(value) for value in values)
        ):
            raise QdrantCompatValidationError(
                "MatchAny requires a non-empty list of strings or signed 64-bit integers"
            )
        return _group([_query_string(f"{field}:{_match_value(value)}") for value in values], "should")

    value = fields["text"]
    terms = value.split() if isinstance(value, str) else []
    if not terms or not all(term.isalnum() for term in terms):
        raise QdrantCompatValidationError("MatchText requires whitespace-separated alphanumeric terms")
    return _group([_query_string(f"{field}:{_literal(term)}") for term in terms], "filter")


def _condition_query(condition: Any) -> Dict[str, Any]:
    fields = _fields(condition, "Qdrant condition", {"has_id", "key", "match", "range"})
    if "has_id" in fields:
        if len(fields) != 1:
            raise QdrantCompatValidationError("HasIdCondition cannot include other filter fields")
        ids = point_ids_to_doc_ids(fields["has_id"], "HasIdCondition")
        return _group([_query_string(f"id:{_literal(point_id)}") for point_id in ids], "should")

    field = fields.get("key")
    if not isinstance(field, str) or not _FIELD_PATH.fullmatch(field) or field in _OPERATORS:
        raise QdrantCompatValidationError("FieldCondition requires a supported indexed field name")
    if fields.get("match") is not None and fields.get("range") is None:
        return _match_query(field, fields["match"])
    if fields.get("range") is not None and fields.get("match") is None:
        return _range_query(field, fields["range"])
    raise QdrantCompatValidationError("FieldCondition requires exactly one of match or range")


def _clause_queries(conditions: Any, name: str) -> List[Dict[str, Any]]:
    if conditions is None:
        return []
    if not isinstance(conditions, list) or (name == "should" and not conditions):
        raise QdrantCompatValidationError(f"Filter.{name} requires a list of conditions (non-empty for should)")
    return [_condition_query(condition) for condition in conditions]


def filter_to_lambdadb(qdrant_filter: Union[models.Filter, Dict[str, Any], None]) -> Dict[str, Any]:
    """Convert a Qdrant filter to a LambdaDB query object."""
    if qdrant_filter is None:
        return {}
    fields = _fields(qdrant_filter, "Qdrant filter", {"must", "should", "must_not"})
    required = _clause_queries(fields.get("must"), "must")
    alternatives = _clause_queries(fields.get("should"), "should")
    excluded = _clause_queries(fields.get("must_not"), "must_not")
    if alternatives:
        # Qdrant requires one should match even when must is present.
        required.append(_group(alternatives, "should"))
    if excluded:
        # Lucene needs a positive clause in every bool with only exclusions.
        required = required or [_query_string("*:*")]
        return {"bool": [
            *({**query, "occur": "filter"} for query in required),
            *({**query, "occur": "must_not"} for query in excluded),
        ]}
    return _group(required, "filter") if required else {}
