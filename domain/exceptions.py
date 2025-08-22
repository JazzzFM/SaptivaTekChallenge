"""Custom exceptions for the prompt service."""

class PromptServiceError(Exception):
    """Base exception for prompt service errors."""
    pass

class ValidationError(PromptServiceError):
    """Raised when input validation fails."""
    pass

class EmbeddingError(PromptServiceError):
    """Raised when embedding generation fails."""
    pass

class VectorIndexError(PromptServiceError):
    """Raised when vector index operations fail."""
    pass

class RepositoryError(PromptServiceError):
    """Raised when repository operations fail."""
    pass

class LLMError(PromptServiceError):
    """Raised when LLM operations fail."""
    pass

class ConfigurationError(PromptServiceError):
    """Raised when configuration is invalid."""
    pass