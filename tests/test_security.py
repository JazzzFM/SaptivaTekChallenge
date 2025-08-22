"""Tests for security utilities."""

import pytest
from core.security import InputValidator, RateLimiter
from domain.exceptions import ValidationError


class TestInputValidator:
    def test_validate_prompt_success(self):
        prompt = "This is a valid prompt"
        result = InputValidator.validate_prompt(prompt)
        assert result == prompt

    def test_validate_prompt_empty(self):
        with pytest.raises(ValidationError, match="cannot be empty"):
            InputValidator.validate_prompt("")

    def test_validate_prompt_whitespace_only(self):
        with pytest.raises(ValidationError, match="empty after sanitization"):
            InputValidator.validate_prompt("   ")

    def test_validate_prompt_too_long(self):
        long_prompt = "a" * 2001
        with pytest.raises(ValidationError, match="too long"):
            InputValidator.validate_prompt(long_prompt, max_length=2000)

    def test_validate_prompt_sql_injection(self):
        malicious_prompts = [
            "SELECT * FROM users",
            "DROP TABLE prompts",
            "UNION SELECT password FROM users",
            "<script>alert('xss')</script>",
        ]
        
        for prompt in malicious_prompts:
            with pytest.raises(ValidationError, match="dangerous content"):
                InputValidator.validate_prompt(prompt)

    def test_validate_prompt_control_characters(self):
        prompt_with_control = "Normal text\x00\x0B\x1F with control chars"
        result = InputValidator.validate_prompt(prompt_with_control)
        assert "\x00" not in result
        assert "\x0B" not in result
        assert "\x1F" not in result

    def test_validate_prompt_html_escape(self):
        prompt = "Test with <script> and & symbols"
        result = InputValidator.validate_prompt(prompt)
        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result

    def test_validate_prompt_excessive_whitespace(self):
        prompt = "Text   with    excessive     whitespace"
        result = InputValidator.validate_prompt(prompt)
        assert "   " not in result
        assert result == "Text with excessive whitespace"

    def test_sanitize_for_logging(self):
        text = "Some text with <script> tags"
        result = InputValidator.sanitize_for_logging(text, max_length=20)
        assert len(result) <= 20
        assert "&lt;" in result

    def test_sanitize_for_logging_empty(self):
        result = InputValidator.sanitize_for_logging("")
        assert result == "[empty]"

    def test_sanitize_for_logging_truncation(self):
        long_text = "a" * 200
        result = InputValidator.sanitize_for_logging(long_text, max_length=50)
        assert len(result) <= 50
        assert result.endswith("...")


class TestRateLimiter:
    def setup_method(self):
        self.rate_limiter = RateLimiter()

    def test_rate_limiter_allows_requests_under_limit(self):
        client_id = "test_client"
        
        for i in range(5):
            assert self.rate_limiter.is_allowed(client_id, limit=10, window_seconds=60)

    def test_rate_limiter_blocks_requests_over_limit(self):
        client_id = "test_client"
        
        # Fill up the limit
        for i in range(10):
            assert self.rate_limiter.is_allowed(client_id, limit=10, window_seconds=60)
        
        # Next request should be blocked
        assert not self.rate_limiter.is_allowed(client_id, limit=10, window_seconds=60)

    def test_rate_limiter_different_clients(self):
        # Different clients should have separate limits
        assert self.rate_limiter.is_allowed("client1", limit=2, window_seconds=60)
        assert self.rate_limiter.is_allowed("client2", limit=2, window_seconds=60)
        
        assert self.rate_limiter.is_allowed("client1", limit=2, window_seconds=60)
        assert self.rate_limiter.is_allowed("client2", limit=2, window_seconds=60)
        
        # Both should be at limit now
        assert not self.rate_limiter.is_allowed("client1", limit=2, window_seconds=60)
        assert not self.rate_limiter.is_allowed("client2", limit=2, window_seconds=60)

    def test_rate_limiter_window_reset(self):
        import time
        client_id = "test_client"
        
        # Fill up the limit
        for i in range(3):
            assert self.rate_limiter.is_allowed(client_id, limit=3, window_seconds=1)
        
        # Should be blocked
        assert not self.rate_limiter.is_allowed(client_id, limit=3, window_seconds=1)
        
        # Wait for window to reset
        time.sleep(1.1)
        
        # Should be allowed again
        assert self.rate_limiter.is_allowed(client_id, limit=3, window_seconds=1)

    def test_rate_limiter_get_stats(self):
        client_id = "test_client"
        
        stats_before = self.rate_limiter.get_stats(client_id)
        assert stats_before["current_requests"] == 0
        assert not stats_before["has_requests"]
        
        self.rate_limiter.is_allowed(client_id, limit=10, window_seconds=60)
        
        stats_after = self.rate_limiter.get_stats(client_id)
        assert stats_after["current_requests"] == 1
        assert stats_after["has_requests"]