from dataclasses import dataclass


@dataclass(frozen=True)
class PromptRecord:
    id: str
    prompt: str
    response: str
    created_at: str  # ISO8601
