"""LambdaDB Python client package exports."""

from .version import (
    GEN_VERSION as _GEN_VERSION,
    OPENAPI_DOC_VERSION as _OPENAPI_DOC_VERSION,
    TITLE as _TITLE,
    get_user_agent,
    get_version,
)
from .sdk import *
from .sdkconfiguration import *
from .collection import RequestOptions
from .models import (
    FetchDocsResponse,
    ListDocsResponse,
    QueryCollectionResponse,
)


VERSION: str = get_version()
OPENAPI_DOC_VERSION = _OPENAPI_DOC_VERSION
SPEAKEASY_GENERATOR_VERSION = _GEN_VERSION
USER_AGENT = get_user_agent()

# Backward-compatible legacy exports
__title__ = _TITLE
__version__ = VERSION
__openapi_doc_version__ = OPENAPI_DOC_VERSION
__gen_version__ = SPEAKEASY_GENERATOR_VERSION
__user_agent__ = USER_AGENT
