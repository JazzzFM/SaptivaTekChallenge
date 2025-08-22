import threading
from typing import Optional

import torch
from sentence_transformers import SentenceTransformer

from core.logging import get_logger
from domain.exceptions import EmbeddingError
from domain.ports import Embedder

logger = get_logger(__name__)

class SentenceTransformerEmbedder(Embedder):
    _instance: Optional['SentenceTransformerEmbedder'] = None
    _init_lock = threading.Lock()
    _model_lock: threading.Lock
    
    def __new__(cls, model_name: str = "all-MiniLM-L6-v2"):
        # Singleton pattern to avoid loading model multiple times
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
                cls._instance._model_lock = threading.Lock()
            return cls._instance
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        with self._init_lock:
            if getattr(self, '_initialized', False):
                return
            
            try:
                logger.info(f"Loading sentence transformer model: {model_name}")
                self.model = SentenceTransformer(model_name)
                self.model_name = model_name
                
                # Set model to evaluation mode and optimize for inference
                self.model.eval()
                if torch.cuda.is_available():
                    logger.info("CUDA available, moving model to GPU")
                    self.model = self.model.cuda()
                
                self._initialized = True
                logger.info(f"Model {model_name} loaded successfully")
                
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
                raise EmbeddingError(f"Failed to initialize embedder: {str(e)}") from e

    def embed(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")
        
        with self._model_lock:
            try:
                # Use torch.no_grad() for inference to save memory
                with torch.no_grad():
                    embedding = self.model.encode(
                        text.strip(), 
                        convert_to_tensor=True,
                        normalize_embeddings=False  # We'll normalize manually
                    )
                    
                    # Manual L2 normalization for cosine similarity
                    normalized_embedding = torch.nn.functional.normalize(embedding, p=2, dim=0)
                    
                    # Convert to list and validate
                    result = normalized_embedding.cpu().tolist()
                    
                    if not result or len(result) == 0:
                        raise EmbeddingError("Model returned empty embedding")
                    
                    # Validate that all values are finite
                    if not all(isinstance(x, (int, float)) and not (x != x or abs(x) == float('inf')) for x in result):
                        raise EmbeddingError("Model returned invalid embedding values")
                    
                    return result
                    
            except torch.cuda.OutOfMemoryError as e:
                logger.error(f"CUDA out of memory during embedding: {e}")
                raise EmbeddingError("GPU memory exhausted during embedding") from e
            except Exception as e:
                logger.error(f"Failed to generate embedding: {e}")
                raise EmbeddingError(f"Embedding generation failed: {str(e)}") from e
    
    def get_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        if hasattr(self, 'model') and self.model is not None:
            dim = self.model.get_sentence_embedding_dimension()
            return dim if dim is not None else 384
        return 384  # Default dimension
    
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_name": self.model_name,
            "dimension": self.get_dimension(),
            "device": "cuda" if next(self.model.parameters()).is_cuda else "cpu",
            "initialized": self._initialized
        }
