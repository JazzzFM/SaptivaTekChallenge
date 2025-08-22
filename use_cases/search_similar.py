from domain.ports import VectorIndex, Embedder, PromptRepository
from domain.entities import PromptRecord
from domain.exceptions import ValidationError, EmbeddingError, VectorIndexError, RepositoryError
from core.logging import get_logger

logger = get_logger(__name__)

class SearchSimilar:
    def __init__(
        self,
        vector_index: VectorIndex,
        embedder: Embedder,
        prompt_repo: PromptRepository,
    ):
        self.vector_index = vector_index
        self.embedder = embedder
        self.prompt_repo = prompt_repo

    def execute(self, query: str, k: int) -> list[PromptRecord]:
        try:
            # Validate input
            if not query or not query.strip():
                raise ValidationError("Query cannot be empty")
            if k <= 0:
                raise ValidationError("k must be positive")
            if k > 100:  # Configurable limit
                raise ValidationError("k cannot exceed 100")
            
            query = query.strip()
            logger.info(f"Searching for {k} similar prompts to query with length: {len(query)}")
            
            # Generate embedding for query
            try:
                embedding = self.embedder.embed(query)
                if not embedding or len(embedding) == 0:
                    raise EmbeddingError("Empty embedding generated for query")
            except Exception as e:
                logger.error(f"Embedding generation failed for query: {e}")
                raise EmbeddingError(f"Failed to generate embedding: {str(e)}") from e
            
            # Search vector index
            try:
                similar_ids = self.vector_index.search(embedding, k)
                logger.info(f"Found {len(similar_ids)} similar ids")
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
                raise VectorIndexError(f"Failed to search vector index: {str(e)}") from e
            
            # Retrieve records from repository
            results = []
            failed_lookups = 0
            
            for id, score in similar_ids:
                try:
                    record = self.prompt_repo.find_by_id(id)
                    if record:
                        results.append(record)
                    else:
                        failed_lookups += 1
                        logger.warning(f"Record not found for id: {id}")
                except Exception as e:
                    failed_lookups += 1
                    logger.error(f"Failed to retrieve record {id}: {e}")
            
            if failed_lookups > 0:
                logger.warning(f"Failed to retrieve {failed_lookups} records")
            
            logger.info(f"Found {len(results)} similar prompts")
            return results
            
        except (ValidationError, EmbeddingError, VectorIndexError, RepositoryError):
            # Re-raise known errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error in search similar: {e}")
            raise VectorIndexError(f"Unexpected error: {str(e)}") from e
