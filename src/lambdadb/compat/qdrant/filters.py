"""Qdrant filter to LambdaDB query conversion."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Union

from . import models
from .errors import QdrantCompatValidationError, UnsupportedQdrantFeatureError


def _as_model(value: Any, klass):
    if isinstance(value, klass):
        return value
    if isinstance(value, dict):
        return klass.model_validate(value)
    if hasattr(value, "model_dump"):
        return klass.model_validate(value.model_dump(exclude_none=True))
    return value


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    if any(ch.isspace() for ch in escaped) or ":" in escaped or "/" in escaped:
        return f'"{escaped}"'
    return escaped


def _query_string(query: str) -> Dict[str, Dict[str, str]]:
    return {"queryString": {"query": query}}


def _range_query(field: str, range_value: Union[models.Range, Dict[str, Any]]) -> str:
    rng = _as_model(range_value, models.Range)
    lower = "*"
    upper = "*"
    left = "["
    right = "]"
    if rng.gte is not None:
        lower = _format_scalar(rng.gte)
    elif rng.gt is not None:
        lower = _format_scalar(rng.gt)
        left = "{"
    if rng.lte is not None:
        upper = _format_scalar(rng.lte)
    elif rng.lt is not None:
        upper = _format_scalar(rng.lt)
        right = "}"
    return f"{field}:{left}{lower} TO {upper}{right}"


def _match_queries(field: str, match: Any) -> List[Dict[str, Dict[str, str]]]:
    if isinstance(match, dict):
        if "value" in match:
            match = models.MatchValue.model_validate(match)
        elif "any" in match:
            match = models.MatchAny.model_validate(match)
        elif "except" in match:
            match = models.MatchExcept.model_validate(match)
        elif "except_" in match:
            match = models.MatchExcept.model_validate(match)
        elif "text" in match:
            match = models.MatchText.model_validate(match)

    if isinstance(match, models.MatchValue):
        return [_query_string(f"{field}:{_format_scalar(match.value)}")]
    if isinstance(match, models.MatchAny):
        return [_query_string(f"{field}:{_format_scalar(value)}") for value in match.any]
    if isinstance(match, models.MatchExcept):
        return [_query_string(f"{field}:{_format_scalar(value)}") for value in match.except_]
    if isinstance(match, models.MatchText):
        raise UnsupportedQdrantFeatureError("MatchText is not supported in the v1 Qdrant compatibility filter")
    raise UnsupportedQdrantFeatureError(f"Unsupported Qdrant match condition: {match!r}")


def _condition_queries(condition: models.Condition) -> List[Dict[str, Any]]:
    if isinstance(condition, dict):
        if "key" in condition:
            condition = models.FieldCondition.model_validate(condition)
        elif "has_id" in condition:
            condition = models.HasIdCondition.model_validate(condition)
        else:
            raise UnsupportedQdrantFeatureError(f"Unsupported Qdrant filter condition: {condition!r}")

    if isinstance(condition, models.HasIdCondition):
        return [_query_string(f"id:{_format_scalar(value)}") for value in condition.has_id]
    if not isinstance(condition, models.FieldCondition):
        raise UnsupportedQdrantFeatureError(f"Unsupported Qdrant filter condition: {condition!r}")

    queries: List[Dict[str, Any]] = []
    if condition.match is not None:
        queries.extend(_match_queries(condition.key, condition.match))
    if condition.range is not None:
        queries.append(_query_string(_range_query(condition.key, condition.range)))
    if not queries:
        raise QdrantCompatValidationError("FieldCondition must include match or range")
    return queries


def _append_bool_clauses(
    clauses: List[Dict[str, Any]],
    conditions: Iterable[models.Condition],
    occur: str,
) -> None:
    for condition in conditions:
        condition_queries = _condition_queries(condition)
        if isinstance(condition, dict) and "match" in condition:
            raw_match = condition.get("match")
        elif isinstance(condition, models.FieldCondition):
            raw_match = condition.match
        else:
            raw_match = None
        negate_match_except = isinstance(raw_match, models.MatchExcept) or (
            isinstance(raw_match, dict) and ("except" in raw_match or "except_" in raw_match)
        )
        effective_occur = "must_not" if negate_match_except and occur != "must_not" else occur
        for query in condition_queries:
            clauses.append({**query, "occur": effective_occur})


def filter_to_lambdadb(qdrant_filter: Union[models.Filter, Dict[str, Any], None]) -> Dict[str, Any]:
    """Convert a Qdrant filter to a LambdaDB query object."""
    if qdrant_filter is None:
        return {}
    filt = _as_model(qdrant_filter, models.Filter)
    if not isinstance(filt, models.Filter):
        raise QdrantCompatValidationError("query_filter must be a Filter or dict")

    clauses: List[Dict[str, Any]] = []
    if filt.must:
        _append_bool_clauses(clauses, filt.must, "filter")
    if filt.should:
        _append_bool_clauses(clauses, filt.should, "should")
    if filt.must_not:
        _append_bool_clauses(clauses, filt.must_not, "must_not")

    if not clauses:
        return {}
    if len(clauses) == 1:
        clause = dict(clauses[0])
        clause.pop("occur", None)
        return clause
    return {"bool": clauses}
