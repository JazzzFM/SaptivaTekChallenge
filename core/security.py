"""Security utilities for input validation and sanitization."""

import re
import html
from domain.exceptions import ValidationError

class InputValidator:
    """Validates and sanitizes user inputs."""
    
    # Patterns for potentially dangerous content
    SQL_INJECTION_PATTERNS = [
        r"(?i)(union\s+select|drop\s+table|delete\s+from|insert\s+into)",
        r"(?i)<script[^>]*>.*?</script>",
        r"(?i)(exec\s*\(|eval\s*\()",
    ]
    
    # Control characters and non-printable chars (except basic whitespace)
    CONTROL_CHARS = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]')
    
    @classmethod
    def validate_prompt(cls, prompt: str, max_length: int = 2000) -> str:
        """
        Validate and sanitize a prompt input.
        
        Args:
            prompt: The input prompt
            max_length: Maximum allowed length
            
        Returns:
            Sanitized prompt
            
        Raises:
            ValidationError: If validation fails
        """
        if not prompt:
            raise ValidationError("Prompt cannot be empty")
        
        # Check length
        if len(prompt) > max_length:
            raise ValidationError(f"Prompt too long: {len(prompt)} > {max_length}")
        
        # Remove control characters
        sanitized = cls.CONTROL_CHARS.sub('', prompt)
        
        # Check for suspicious patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, sanitized):
                raise ValidationError("Prompt contains potentially dangerous content")
        
        # Basic HTML escape for safety (but keep readable)
        sanitized = html.escape(sanitized, quote=False)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        if not sanitized:
            raise ValidationError("Prompt is empty after sanitization")
        
        return sanitized
    
    @classmethod
    def sanitize_for_logging(cls, text: str, max_length: int = 100) -> str:
        """
        Sanitize text for safe logging.
        
        Args:
            text: Text to sanitize
            max_length: Maximum length for logs
            
        Returns:
            Sanitized text safe for logging
        """
        if not text:
            return "[empty]"
        
        # Remove control characters
        sanitized = cls.CONTROL_CHARS.sub('', text)
        
        # Escape for safety
        sanitized = html.escape(sanitized, quote=False)
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length-3] + "..."
        
        return sanitized

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self._requests = {}
        self._windows = {}
    
    def is_allowed(self, client_id: str, limit: int, window_seconds: int = 60) -> bool:
        """
        Check if request is allowed based on rate limit.
        
        Args:
            client_id: Unique identifier for the client
            limit: Maximum requests per window
            window_seconds: Time window in seconds
            
        Returns:
            True if request is allowed, False otherwise
        """
        import time
        
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # Clean old entries
        if client_id in self._requests:
            self._requests[client_id] = [
                req_time for req_time in self._requests[client_id] 
                if req_time > window_start
            ]
        else:
            self._requests[client_id] = []
        
        # Check if under limit
        if len(self._requests[client_id]) >= limit:
            return False
        
        # Record this request
        self._requests[client_id].append(current_time)
        return True
    
    def get_stats(self, client_id: str) -> dict:
        """Get rate limiting stats for a client."""
        return {
            "client_id": client_id,
            "current_requests": len(self._requests.get(client_id, [])),
            "has_requests": client_id in self._requests
        }

# Global rate limiter instance
rate_limiter = RateLimiter()