import uuid
from datetime import datetime, timezone

from core.logging import get_logger, perf_monitor, time_operation
from domain.entities import PromptRecord
from domain.exceptions import (
    EmbeddingError,
    LLMError,
    RepositoryError,
    ValidationError,
    VectorIndexError,
)
from domain.ports import Embedder, LLMProvider, PromptRepository, VectorIndex

logger = get_logger(__name__)

class CreatePrompt:
    def __init__(
        self,
        llm_provider: LLMProvider,
        prompt_repo: PromptRepository,
        vector_index: VectorIndex,
        embedder: Embedder,
    ):
        self.llm_provider = llm_provider
        self.prompt_repo = prompt_repo
        self.vector_index = vector_index
        self.embedder = embedder

    def execute(self, prompt: str) -> PromptRecord:
        perf_monitor.increment_counter("prompts_created_attempted")
        
        with time_operation("create_prompt_total"):
            try:
                # Validate input
                if not prompt or not prompt.strip():
                    raise ValidationError("Prompt cannot be empty")
                
                prompt = prompt.strip()
                logger.info("Creating prompt", prompt_length=len(prompt))
                
                # Generate LLM response
                with time_operation("llm_generation"):
                    try:
                        response = self.llm_provider.generate(prompt)
                    except Exception as e:
                        logger.error("LLM generation failed", error=str(e))
                        raise LLMError(f"Failed to generate response: {str(e)}") from e
                
                # Create record
                record = PromptRecord(
                    id=str(uuid.uuid4()),
                    prompt=prompt,
                    response=response,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                
                # Save to repository
                with time_operation("repository_save"):
                    try:
                        self.prompt_repo.save(record)
                        logger.info("Saved prompt record", record_id=record.id)
                    except Exception as e:
                        logger.error("Repository save failed", error=str(e))
                        raise RepositoryError(f"Failed to save prompt: {str(e)}") from e
                
                # Generate and store embedding
                with time_operation("embedding_and_indexing"):
                    try:
                        embedding = self.embedder.embed(prompt)
                        if not embedding or len(embedding) == 0:
                            raise EmbeddingError("Empty embedding generated")
                        
                        self.vector_index.add(record.id, embedding)
                        logger.info("Added prompt to vector index", record_id=record.id, embedding_dim=len(embedding))
                    except EmbeddingError as e:
                        raise e
                    except Exception as e:
                        logger.error("Vector indexing failed", error=str(e))
                        # Try to clean up the saved record if embedding fails
                        try:
                            # Note: This is a simplified cleanup. In production, use transactions
                            pass
                        except Exception:
                            logger.error("Failed to cleanup record after embedding failure")
                        raise VectorIndexError(f"Failed to index prompt: {str(e)}") from e
                
                perf_monitor.increment_counter("prompts_created_success")
                return record
                
            except (ValidationError, LLMError, EmbeddingError, VectorIndexError, RepositoryError):
                perf_monitor.increment_counter("prompts_created_failed")
                # Re-raise known errors
                raise
            except Exception as e:
                perf_monitor.increment_counter("prompts_created_failed")
                logger.error("Unexpected error in create prompt", error=str(e))
                raise LLMError(f"Unexpected error: {str(e)}") from e
