"""Errors raised by the Qdrant compatibility adapter."""


class QdrantCompatError(Exception):
    """Base class for Qdrant compatibility errors."""


class QdrantCompatValidationError(ValueError, QdrantCompatError):
    """Raised when Qdrant-style input cannot be converted safely."""


class UnsupportedQdrantFeatureError(NotImplementedError, QdrantCompatError):
    """Raised when a Qdrant feature is outside the supported compatibility subset."""

