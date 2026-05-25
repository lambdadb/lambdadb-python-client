"""Qdrant-style compatibility client for LambdaDB."""

from .client import QdrantClient, QdrantCompatClient
from .errors import (
    QdrantCompatError,
    QdrantCompatValidationError,
    UnsupportedQdrantFeatureError,
)
from . import models

__all__ = [
    "QdrantClient",
    "QdrantCompatClient",
    "QdrantCompatError",
    "QdrantCompatValidationError",
    "UnsupportedQdrantFeatureError",
    "models",
]

