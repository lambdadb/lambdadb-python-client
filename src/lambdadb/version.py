"""Runtime version and SDK metadata."""

from __future__ import annotations

TITLE: str = "lambdadb"
SDK_VERSION: str = "0.15.0"
OPENAPI_DOC_VERSION: str = "1.3.0"
GEN_VERSION: str = "2.798.0"
API_CONTRACT_REVISION: str = "7be299af9cac4195b75feb6e38b5cd7f8989f5a0"


def get_version() -> str:
    """Return SDK package version."""
    return SDK_VERSION


def get_user_agent() -> str:
    """Build user agent string using current package version."""
    version = get_version()
    return f"speakeasy-sdk/python {version} {GEN_VERSION} {OPENAPI_DOC_VERSION} {TITLE}"
