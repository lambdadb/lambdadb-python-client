"""Runtime version and SDK metadata."""

from __future__ import annotations

TITLE: str = "lambdadb"
SDK_VERSION: str = "0.9.0.dev2"
OPENAPI_DOC_VERSION: str = "1.1.1"
GEN_VERSION: str = "2.798.0"
API_CONTRACT_REVISION: str = "c8495bf47cd8918cfd546b4742823fd4cf3d0814"


def get_version() -> str:
    """Return SDK package version."""
    return SDK_VERSION


def get_user_agent() -> str:
    """Build user agent string using current package version."""
    version = get_version()
    return f"speakeasy-sdk/python {version} {GEN_VERSION} {OPENAPI_DOC_VERSION} {TITLE}"
