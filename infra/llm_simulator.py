from hashlib import sha256

from domain.ports import LLMProvider


class LLMSimulator(LLMProvider):
    def generate(self, prompt: str) -> str:
        digest = int(sha256(prompt.encode()).hexdigest(), 16)
        seed = digest % 10000
        keywords = " ".join(prompt.lower().split()[:3])
        return f"[SimResponse-{seed}] Respuesta generada sobre: {keywords}"
