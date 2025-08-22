from domain.ports import LLMProvider

class SaptivaLLMAdapter(LLMProvider):
    def generate(self, prompt: str) -> str:
        # This is a stub for a future implementation.
        # In a real scenario, this would call the Saptiva LLM API.
        raise NotImplementedError("SaptivaLLMAdapter is not implemented yet.")
