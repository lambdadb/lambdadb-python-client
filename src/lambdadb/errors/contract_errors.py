"""Typed errors added by the Cloud SaaS user contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Type

import httpx
from pydantic import ValidationError

from lambdadb.errors.apierror import APIError
from lambdadb.errors.lambdadberror import LambdaDBError
from lambdadb.types import BaseModel


class _MessageErrorData(BaseModel):
    message: Optional[str] = None


@dataclass(unsafe_hash=True)
class _MessageError(LambdaDBError):
    data: _MessageErrorData = field(hash=False)

    def __init__(
        self,
        data: _MessageErrorData,
        raw_response: httpx.Response,
        body: Optional[str] = None,
    ) -> None:
        fallback = body or raw_response.text
        message = data.message or fallback
        super().__init__(message, raw_response, body)
        object.__setattr__(self, "data", data)


class PayloadTooLargeErrorData(_MessageErrorData):
    """Payload-too-large response body."""


class BadGatewayErrorData(_MessageErrorData):
    """Bad-gateway response body."""


class ServiceUnavailableErrorData(_MessageErrorData):
    """Service-unavailable response body."""


class GatewayTimeoutErrorData(_MessageErrorData):
    """Gateway-timeout response body."""


class CatalogConflictErrorData(_MessageErrorData):
    """Conditional catalog-conflict response body."""


class PayloadTooLargeError(_MessageError):
    """The request exceeds the Gateway transport limit (HTTP 413)."""


class BadGatewayError(_MessageError):
    """An unexpected downstream failure occurred (HTTP 502)."""


class ServiceUnavailableError(_MessageError):
    """A catalog or storage dependency is unavailable (HTTP 503)."""


class GatewayTimeoutError(_MessageError):
    """The Gateway request deadline was exceeded (HTTP 504)."""


class CatalogConflictError(_MessageError):
    """A conditional catalog update conflicted (HTTP 409)."""


_ERROR_TYPES: dict[int, tuple[Type[_MessageErrorData], Type[_MessageError]]] = {
    413: (PayloadTooLargeErrorData, PayloadTooLargeError),
    502: (BadGatewayErrorData, BadGatewayError),
    503: (ServiceUnavailableErrorData, ServiceUnavailableError),
    504: (GatewayTimeoutErrorData, GatewayTimeoutError),
}


def raise_for_contract_status(response: httpx.Response) -> None:
    """Raise a typed error for contract-wide Gateway status responses."""
    mapping = _ERROR_TYPES.get(response.status_code)
    if mapping is None:
        return

    content_type = response.headers.get("content-type", "").split(";", 1)[0]
    if content_type == "application/json":
        try:
            data = mapping[0].model_validate_json(response.content)
        except (ValidationError, ValueError):
            pass
        else:
            raise mapping[1](data, response)

    raise APIError("API error occurred", response, response.text)


def raise_catalog_conflict(response: httpx.Response) -> None:
    """Raise the typed conditional catalog-conflict error."""
    try:
        data = CatalogConflictErrorData.model_validate_json(response.content)
    except (ValidationError, ValueError):
        raise APIError("API error occurred", response, response.text) from None
    raise CatalogConflictError(data, response)
