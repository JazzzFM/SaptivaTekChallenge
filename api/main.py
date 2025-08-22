# -*- coding: utf-8 -*-
import atexit
import logging
import time
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from core.container import cleanup_container, get_container
from core.security import InputValidator, rate_limiter
from core.settings import ensure_sqlite_dir, get_settings
from domain.exceptions import (
    EmbeddingError,
    LLMError,
    RepositoryError,
    ValidationError,
    VectorIndexError,
)
from use_cases.create_prompt import CreatePrompt
from use_cases.search_similar import SearchSimilar


def create_app() -> FastAPI:
    settings = get_settings()
    ensure_sqlite_dir(settings.database_url)

    app = FastAPI(
        title="Prompt Service",
        description="A microservice for prompt processing with vector similarity search",
        version="1.0.0"
    )

    # Security middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8080"],  # Configure as needed
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["localhost", "127.0.0.1", "*.example.com", "testserver"]  # Configure as needed, including testserver for tests
    )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=400,
            content={"error": "validation_error", 
                    "detail": str(exc)}
        )

    @app.exception_handler(HTTPException)
    async def http_exc_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={
            "error": "http_error",
            "detail": exc.detail
        })

    # Rate limiting middleware
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if settings.enable_rate_limiting:
            client_ip = request.client.host if request.client else "unknown"
            
            if not rate_limiter.is_allowed(
                client_id=client_ip,
                limit=settings.rate_limit_per_minute,
                window_seconds=60
            ):
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "detail": f"Maximum {settings.rate_limit_per_minute} requests per minute",
                        "error_type": "RateLimitError"
                    }
                )
        
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

    # Register cleanup function
    atexit.register(cleanup_container)

    # Dependencies using DI container
    def get_create_prompt_use_case() -> CreatePrompt:
        container = get_container()
        return container.create_prompt_use_case

    def get_search_similar_use_case() -> SearchSimilar:
        container = get_container()
        return container.search_similar_use_case


    class CreatePromptRequest(BaseModel):
        prompt: str = Field(min_length=1, max_length=settings.max_prompt_length)
        
        @field_validator('prompt')
        @classmethod
        def validate_prompt(cls, v):
            return InputValidator.validate_prompt(v, settings.max_prompt_length)

    class PromptResponse(BaseModel):
        id: str
        prompt: str
        response: str
        created_at: str

    class ErrorResponse(BaseModel):
        error: str
        detail: str
        error_type: str

    @app.post("/prompt")
    def create_prompt(
        request: CreatePromptRequest,
        use_case: CreatePrompt = Depends(get_create_prompt_use_case),
    ):
        try:
            record = use_case.execute(request.prompt)
            return record
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail={"error": "Validation failed", "detail": str(e), "error_type": "ValidationError"},
            ) from e
        except (LLMError, EmbeddingError, VectorIndexError, RepositoryError) as e:
            logging.error(f"Service error in create_prompt: {e}")
            raise HTTPException(
                status_code=500,
                detail={"error": "Service error", "detail": "Internal processing failed", "error_type": type(e).__name__},
            ) from e
        except Exception as e:
            logging.error(f"Unexpected error in create_prompt: {e}")
            raise HTTPException(
                status_code=500,
                detail={"error": "Internal server error", "detail": "An unexpected error occurred", "error_type": "UnknownError"},
            ) from e


    class PaginatedResponse(BaseModel):
        items: List[PromptResponse]
        total: int
        page: int
        page_size: int
        has_next: bool
        has_prev: bool

    @app.get("/similar", response_model=List[PromptResponse], responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    })
    def search_similar(
        query: str = Query(..., min_length=1, max_length=settings.max_prompt_length),
        k: int = Query(3, gt=0, le=settings.max_results),
        use_case: SearchSimilar = Depends(get_search_similar_use_case),
    ):
        try:
            # Validate and sanitize query
            sanitized_query = InputValidator.validate_prompt(query, settings.max_prompt_length)
            records = use_case.execute(sanitized_query, k)
            return records
        except ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail={"error": "Validation failed", "detail": str(e), "error_type": "ValidationError"}
            ) from e
        except (EmbeddingError, VectorIndexError, RepositoryError) as e:
            logging.error(f"Service error in search_similar: {e}")
            raise HTTPException(
                status_code=500,
                detail={"error": "Service error", "detail": "Internal processing failed", "error_type": type(e).__name__}
            ) from e
        except Exception as e:
            logging.error(f"Unexpected error in search_similar: {e}")
            raise HTTPException(
                status_code=500,
                detail={"error": "Internal server error", "detail": "An unexpected error occurred", "error_type": "UnknownError"}
            ) from e

    @app.get("/prompts", response_model=PaginatedResponse, responses={
        400: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    })
    def list_prompts(
        page: int = Query(1, ge=1, description="Page number (1-based)"),
        page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    ):
        """List prompts with pagination."""
        try:
            container = get_container()
            repo = container.prompt_repository
            
            # Calculate offset
            offset = (page - 1) * page_size
            
            # Get paginated results
            if hasattr(repo, 'find_paginated'):
                records, total = repo.find_paginated(offset=offset, limit=page_size)
            else:
                # Fallback: This is a simplified implementation
                # In production, implement proper pagination in the repository
                records = []
                total = 0
            
            # Calculate pagination info
            has_next = (offset + page_size) < total
            has_prev = page > 1
            
            return PaginatedResponse(
                items=records,
                total=total,
                page=page,
                page_size=page_size,
                has_next=has_next,
                has_prev=has_prev
            )
            
        except Exception as e:
            logging.error(f"Failed to list prompts: {e}")
            raise HTTPException(
                status_code=500,
                detail={"error": "Internal server error", "detail": "Failed to retrieve prompts", "error_type": "UnknownError"}
            ) from e

    @app.get("/health")
    def health_check():
        """Basic health check endpoint."""
        return {"status": "healthy", "service": "prompt-service", "timestamp": time.time()}

    @app.get("/health/detailed")
    def detailed_health_check():
        """Detailed health check endpoint with comprehensive status checks."""
        try:
            container = get_container()
            health_status = {"status": "healthy", "service": "prompt-service", "checks": {}}
            overall_healthy = True
            
            # Check database connectivity
            try:
                repo = container.get_repository()
                repo.count()  # Simple DB operation
                health_status["checks"]["database"] = {"status": "healthy", "message": "Database accessible"}
            except Exception as e:
                health_status["checks"]["database"] = {"status": "unhealthy", "message": f"Database error: {str(e)}"}
                overall_healthy = False
            
            # Check vector index
            try:
                vector_index = container.get_vector_index()
                # Try a simple search operation
                test_vector = [0.1] * 384
                vector_index.search(test_vector, k=1)
                health_status["checks"]["vector_index"] = {"status": "healthy", "message": "Vector index accessible"}
            except Exception as e:
                health_status["checks"]["vector_index"] = {"status": "unhealthy", "message": f"Vector index error: {str(e)}"}
                overall_healthy = False
            
            # Check embedder
            try:
                embedder = container.get_embedder()
                embedder.embed("health check test")
                health_status["checks"]["embedder"] = {"status": "healthy", "message": "Embedder functional"}
            except Exception as e:
                health_status["checks"]["embedder"] = {"status": "unhealthy", "message": f"Embedder error: {str(e)}"}
                overall_healthy = False
            
            # Check LLM
            try:
                llm = container.get_llm()
                llm.generate("health check")
                health_status["checks"]["llm"] = {"status": "healthy", "message": "LLM functional"}
            except Exception as e:
                health_status["checks"]["llm"] = {"status": "unhealthy", "message": f"LLM error: {str(e)}"}
                overall_healthy = False
            
            # Overall status
            health_status["status"] = "healthy" if overall_healthy else "unhealthy"
            health_status["timestamp"] = time.time()
            
            if not overall_healthy:
                raise HTTPException(status_code=503, detail=health_status)
            
            return health_status
            
        except HTTPException:
            raise
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "prompt-service",
                "error": str(e),
                "timestamp": time.time()
            }

    @app.get("/health/ready")
    def readiness_check():
        """Readiness check - service is ready to handle requests."""
        try:
            container = get_container()
            
            # Check if service has been properly initialized
            repo = container.get_repository()
            vector_index = container.get_vector_index()
            embedder = container.get_embedder()
            llm = container.get_llm()
            
            # Quick validation that components are ready
            repo.count()
            test_vector = [0.1] * 384
            vector_index.search(test_vector, k=1)
            embedder.embed("ready")
            llm.generate("ready")
            
            return {
                "status": "ready",
                "service": "prompt-service",
                "message": "Service is ready to handle requests",
                "timestamp": time.time()
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "service": "prompt-service",
                    "error": str(e),
                    "timestamp": time.time()
                }
            ) from e

    @app.get("/stats")
    def get_stats():
        """Get detailed service statistics and metrics."""
        try:
            from core.logging import perf_monitor
            container = get_container()
            
            # Get health information
            health_info = container.get_health_info()
            
            # Get performance stats
            performance_stats = perf_monitor.get_stats()
            
            # Get repository stats
            repo = container.get_repository()
            total_records = repo.count() if hasattr(repo, 'count') else 0
            
            # Get embedder info
            embedder = container.get_embedder()
            embedder_info = embedder.get_model_info() if hasattr(embedder, 'get_model_info') else {}
            
            return {
                "service": "prompt-service",
                "status": "active",
                "health": health_info,
                "performance": performance_stats,
                "data": {
                    "total_prompts": total_records,
                    "embedder": embedder_info
                },
                "config": {
                    "vector_backend": settings.vector_backend,
                    "max_prompt_length": settings.max_prompt_length,
                    "max_results": settings.max_results,
                    "rate_limiting_enabled": settings.enable_rate_limiting,
                    "embedding_dim": settings.embedding_dim,
                    "database_url": settings.database_url.split("///")[-1] if "///" in settings.database_url else "in-memory"
                },
                "timestamp": time.time()
            }
            
        except Exception as e:
            logging.error(f"Failed to get stats: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Failed to retrieve service statistics",
                    "detail": str(e),
                    "timestamp": time.time()
                }
            ) from e
    return app

app = create_app()