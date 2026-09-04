"""Shared advanced request options for collection-scoped helper APIs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

from lambdadb import utils
from lambdadb.types import OptionalNullable, UNSET


@dataclass
class RequestOptions:
    """Advanced options for one collection-scoped request."""

    retries: OptionalNullable[utils.RetryConfig] = field(default_factory=lambda: UNSET)
    server_url: Optional[str] = None
    timeout_ms: Optional[int] = None
    http_headers: Optional[Mapping[str, str]] = None


def merge_options(
    options: Optional[RequestOptions],
    retries: OptionalNullable[utils.RetryConfig],
    server_url: Optional[str],
    timeout_ms: Optional[int],
    http_headers: Optional[Mapping[str, str]],
) -> Tuple[
    OptionalNullable[utils.RetryConfig],
    Optional[str],
    Optional[int],
    Optional[Mapping[str, str]],
]:
    """Merge an options object with legacy keyword arguments."""
    if options is None:
        return retries, server_url, timeout_ms, http_headers
    merged_retries = options.retries if options.retries is not UNSET else retries
    return (
        merged_retries,
        options.server_url or server_url,
        options.timeout_ms or timeout_ms,
        options.http_headers or http_headers,
    )
