from sentence_transformers import SentenceTransformer
import torch
from domain.ports import Embedder

class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> list[float]:
        embedding = self.model.encode(text, convert_to_tensor=True)
        normalized_embedding = torch.nn.functional.normalize(embedding, p=2, dim=0)
        return normalized_embedding.tolist()
