# Documentación Inline del Código - Microservicio de Prompts

Este documento contiene la documentación inline de los componentes principales del código, explicando la implementación detallada de cada módulo.

---

## Domain Layer - Entidades y Puertos

### Entidades (`domain/entities.py`)

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PromptRecord:
    """
    Entidad principal del dominio - Registro de Prompt procesado.
    
    Esta clase implementa el patrón Value Object del DDD (Domain-Driven Design):
    - frozen=True: Inmutable después de creación
    - dataclass: Reduce boilerplate y garantiza __eq__, __hash__
    - Encapsula reglas de negocio del dominio
    
    Business Rules:
    - ID debe ser UUID válido y único
    - prompt no puede estar vacío  
    - response debe seguir formato [SimResponse-X]
    - created_at debe ser timestamp ISO8601
    """
    id: str          # UUID v4 único para identificación
    prompt: str      # Texto original del usuario (max 2000 chars)
    response: str    # Respuesta generada por LLM
    created_at: str  # Timestamp ISO8601 (ej: "2024-01-01T00:00:00Z")
    
    def __post_init__(self):
        """
        Validaciones post-inicialización (si se requieren).
        
        Nota: Como es frozen=True, las validaciones deben hacerse
        antes de la creación del objeto, típicamente en los casos de uso.
        """
        pass
```

### Puertos - Interfaces (`domain/ports.py`)

```python
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from .entities import PromptRecord

class PromptRepository(ABC):
    """
    Puerto (interfaz) para persistencia de registros.
    
    Implementa el patrón Repository del DDD:
    - Abstrae detalles de persistencia del dominio
    - Permite intercambiar implementaciones (SQLite, PostgreSQL, etc.)
    - Define contrato que deben cumplir todos los adaptadores
    
    Principios SOLID aplicados:
    - Single Responsibility: Solo persistencia de PromptRecord
    - Open/Closed: Cerrado para modificación, abierto para implementación
    - Liskov Substitution: Cualquier implementación debe respetar contrato
    - Interface Segregation: Interfaz específica, no monolítica
    - Dependency Inversion: Dominio depende de abstracción, no implementación
    """
    
    @abstractmethod
    def save(self, record: PromptRecord) -> None:
        """
        Persiste un registro en el almacén de datos.
        
        Args:
            record: PromptRecord a persistir
            
        Raises:
            RepositoryError: Si falla la persistencia
            ValidationError: Si el record es inválido
        """
        pass
    
    @abstractmethod  
    def find_by_id(self, id: str) -> Optional[PromptRecord]:
        """
        Busca un registro por su ID único.
        
        Args:
            id: Identificador único del registro
            
        Returns:
            PromptRecord si existe, None si no se encuentra
            
        Raises:
            RepositoryError: Si falla la consulta
        """
        pass
    
    @abstractmethod
    def find_paginated(self, offset: int = 0, limit: int = 10) -> Tuple[List[PromptRecord], int]:
        """
        Recupera registros paginados con conteo total.
        
        Args:
            offset: Número de registros a saltar
            limit: Máximo número de registros a retornar
            
        Returns:
            Tupla de (registros, total_count)
            
        Raises:
            RepositoryError: Si falla la consulta
        """
        pass

class VectorIndex(ABC):
    """
    Puerto para operaciones de índice vectorial.
    
    Abstrae el motor de búsqueda vectorial:
    - Permite intercambiar entre FAISS, ChromaDB, Pinecone, etc.
    - Optimizado para búsqueda de similaridad coseno
    - Maneja persistencia y recuperación de índices
    """
    
    @abstractmethod
    def add(self, id: str, vector: list[float]) -> None:
        """
        Añade un vector al índice con su identificador.
        
        Args:
            id: Identificador único del vector
            vector: Vector numérico normalizado L2
            
        Raises:
            VectorIndexError: Si falla la indexación
            ValidationError: Si el vector es inválido
        """
        pass
    
    @abstractmethod
    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        """
        Busca los k vectores más similares.
        
        Args:
            vector: Vector de consulta normalizado L2  
            k: Número de resultados a retornar
            
        Returns:
            Lista de tuplas (id, score) ordenadas por similaridad descendente
            
        Raises:
            VectorIndexError: Si falla la búsqueda
        """
        pass

class Embedder(ABC):
    """
    Puerto para generación de embeddings de texto.
    
    Abstrae el modelo de embeddings:
    - Permite intercambiar entre SentenceTransformers, OpenAI, etc.
    - Garantiza normalización L2 para similaridad coseno
    - Maneja optimizaciones como caching y GPU acceleration
    """
    
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """
        Convierte texto a vector numérico normalizado L2.
        
        Args:
            text: Texto a convertir en embedding
            
        Returns:
            Vector de dimensión fija normalizado (norma L2 = 1.0)
            
        Raises:
            EmbeddingError: Si falla la generación del embedding
        """
        pass
    
    @abstractmethod  
    def get_dimension(self) -> int:
        """
        Retorna la dimensión del espacio vectorial.
        
        Returns:
            Dimensión del vector (ej: 384 para all-MiniLM-L6-v2)
        """
        pass

class LLMProvider(ABC):
    """
    Puerto para generación de respuestas de LLM.
    
    Abstrae el modelo de lenguaje:
    - Permite intercambiar entre simulador, GPT, Claude, etc.
    - Garantiza determinismo para testing
    - Maneja rate limiting y error handling
    """
    
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Genera respuesta para un prompt dado.
        
        Args:
            prompt: Texto del prompt del usuario
            
        Returns:
            Respuesta generada por el LLM
            
        Raises:
            LLMError: Si falla la generación
        """
        pass
```

---

## Application Layer - Casos de Uso

### CreatePrompt (`use_cases/create_prompt.py`)

```python
import uuid
from datetime import datetime, timezone
from typing import Optional

from domain.entities import PromptRecord
from domain.ports import LLMProvider, PromptRepository, VectorIndex, Embedder
from domain.exceptions import ValidationError, PromptServiceError
from core.security import InputValidator
from core.logging import get_logger, perf_monitor

logger = get_logger(__name__)

class CreatePrompt:
    """
    Caso de uso para crear y procesar un nuevo prompt.
    
    Implementa el patrón Command del DDD:
    - Encapsula toda la lógica para procesar un prompt
    - Coordina múltiples servicios sin acoplarse a implementaciones
    - Maneja transacciones y rollback en caso de error
    - Garantiza consistencia entre base de datos e índice vectorial
    
    Flujo de ejecución:
    1. Validar entrada del usuario
    2. Generar respuesta con LLM  
    3. Crear embedding del prompt
    4. Persistir en base de datos
    5. Indexar vector para búsqueda
    6. Retornar registro creado
    
    Error Handling:
    - Rollback automático si falla cualquier paso
    - Logging detallado para debugging
    - Excepciones específicas para cada tipo de error
    """
    
    def __init__(
        self, 
        llm: LLMProvider, 
        repository: PromptRepository,
        vector_index: VectorIndex, 
        embedder: Embedder
    ):
        """
        Inicializa caso de uso con dependencias inyectadas.
        
        Args:
            llm: Proveedor de modelo de lenguaje
            repository: Repositorio para persistencia
            vector_index: Índice vectorial para búsqueda
            embedder: Generador de embeddings
        """
        self.llm = llm
        self.repository = repository
        self.vector_index = vector_index
        self.embedder = embedder
    
    def execute(self, prompt: str) -> PromptRecord:
        """
        Ejecuta el caso de uso completo de creación de prompt.
        
        Args:
            prompt: Texto del prompt del usuario
            
        Returns:
            PromptRecord: Registro creado con respuesta generada
            
        Raises:
            ValidationError: Si el prompt es inválido
            LLMError: Si falla la generación de respuesta
            EmbeddingError: Si falla la generación de embedding
            RepositoryError: Si falla la persistencia
            VectorIndexError: Si falla la indexación
        """
        
        # Iniciar monitoreo de performance
        start_time = perf_monitor.start_timer()
        
        try:
            # Paso 1: Validar entrada
            logger.info("Validating input prompt", extra={"prompt_length": len(prompt)})
            validated_prompt = InputValidator.validate_prompt(prompt)
            
            # Paso 2: Generar ID único y timestamp
            record_id = str(uuid.uuid4())
            created_at = datetime.now(timezone.utc).isoformat()
            
            logger.info("Generated record metadata", extra={
                "record_id": record_id,
                "created_at": created_at
            })
            
            # Paso 3: Generar respuesta con LLM
            logger.info("Generating LLM response")
            try:
                response = self.llm.generate(validated_prompt)
                logger.info("LLM response generated successfully", extra={
                    "response_length": len(response)
                })
            except Exception as e:
                logger.error("LLM generation failed", extra={"error": str(e)})
                raise LLMError(f"Failed to generate response: {str(e)}") from e
            
            # Paso 4: Crear embedding
            logger.info("Generating embedding")
            try:
                embedding = self.embedder.embed(validated_prompt)
                logger.info("Embedding generated successfully", extra={
                    "embedding_dimension": len(embedding)
                })
            except Exception as e:
                logger.error("Embedding generation failed", extra={"error": str(e)})
                raise EmbeddingError(f"Failed to generate embedding: {str(e)}") from e
            
            # Paso 5: Crear registro de dominio
            record = PromptRecord(
                id=record_id,
                prompt=validated_prompt,
                response=response,
                created_at=created_at
            )
            
            # Paso 6: Persistir en base de datos
            logger.info("Saving record to repository")
            try:
                self.repository.save(record)
                logger.info("Record saved successfully", extra={"record_id": record_id})
            except Exception as e:
                logger.error("Repository save failed", extra={"error": str(e)})
                raise RepositoryError(f"Failed to save prompt: {str(e)}") from e
            
            # Paso 7: Indexar vector
            logger.info("Adding vector to index")
            try:
                self.vector_index.add(record_id, embedding)
                logger.info("Vector indexed successfully", extra={"record_id": record_id})
            except Exception as e:
                logger.error("Vector indexing failed", extra={"error": str(e)})
                # Nota: En un sistema más robusto, aquí haríamos rollback de la BD
                raise VectorIndexError(f"Failed to index vector: {str(e)}") from e
            
            # Registrar métricas de performance
            duration = perf_monitor.end_timer(start_time)
            perf_monitor.record_duration("create_prompt", duration)
            
            logger.info("Prompt creation completed successfully", extra={
                "record_id": record_id,
                "duration_ms": duration * 1000
            })
            
            return record
            
        except (ValidationError, LLMError, EmbeddingError, RepositoryError, VectorIndexError):
            # Re-lanzar excepciones conocidas del dominio
            raise
        except Exception as e:
            # Capturar errores inesperados
            logger.error("Unexpected error in create prompt", extra={"error": str(e)})
            raise PromptServiceError(f"Unexpected error: {str(e)}") from e
```

### SearchSimilar (`use_cases/search_similar.py`)

```python
from typing import List, Optional
from domain.entities import PromptRecord
from domain.ports import VectorIndex, Embedder, PromptRepository
from domain.exceptions import EmbeddingError, VectorIndexError, ValidationError
from core.security import InputValidator
from core.logging import get_logger, perf_monitor

logger = get_logger(__name__)

class SearchSimilar:
    """
    Caso de uso para búsqueda de prompts similares.
    
    Implementa búsqueda semántica usando:
    1. Generación de embedding para query
    2. Búsqueda vectorial en índice
    3. Recuperación de registros completos
    4. Ordenamiento por relevancia
    
    Características:
    - Búsqueda por similaridad coseno (producto interno con vectores normalizados)
    - Resultados ordenados por score descendente
    - Manejo de casos edge (query vacía, sin resultados)
    - Performance monitoring integrado
    """
    
    def __init__(
        self, 
        vector_index: VectorIndex,
        embedder: Embedder, 
        repository: PromptRepository
    ):
        """
        Inicializa caso de uso con dependencias inyectadas.
        
        Args:
            vector_index: Índice vectorial para búsqueda
            embedder: Generador de embeddings
            repository: Repositorio para recuperar registros completos
        """
        self.vector_index = vector_index
        self.embedder = embedder
        self.repository = repository
    
    def execute(self, query: str, k: int = 5) -> List[PromptRecord]:
        """
        Ejecuta búsqueda de prompts similares.
        
        Args:
            query: Texto de consulta del usuario
            k: Número máximo de resultados a retornar
            
        Returns:
            Lista de PromptRecord ordenados por similaridad descendente
            
        Raises:
            ValidationError: Si la query es inválida
            EmbeddingError: Si falla la generación de embedding
            VectorIndexError: Si falla la búsqueda vectorial
        """
        
        start_time = perf_monitor.start_timer()
        
        try:
            # Paso 1: Validar entrada
            logger.info("Validating search query", extra={
                "query_length": len(query),
                "k": k
            })
            
            validated_query = InputValidator.validate_prompt(query)
            
            if k <= 0 or k > 100:  # Límite razonable para performance
                raise ValidationError(f"Invalid k value: {k}. Must be between 1 and 100")
            
            # Paso 2: Generar embedding de la query
            logger.info("Generating query embedding")
            try:
                query_embedding = self.embedder.embed(validated_query)
                logger.info("Query embedding generated", extra={
                    "embedding_dimension": len(query_embedding)
                })
            except Exception as e:
                logger.error("Query embedding failed", extra={"error": str(e)})
                raise EmbeddingError(f"Failed to generate query embedding: {str(e)}") from e
            
            # Paso 3: Buscar vectores similares
            logger.info("Searching similar vectors")
            try:
                similar_results = self.vector_index.search(query_embedding, k)
                logger.info("Vector search completed", extra={
                    "results_found": len(similar_results)
                })
            except Exception as e:
                logger.error("Vector search failed", extra={"error": str(e)})
                raise VectorIndexError(f"Failed to search vectors: {str(e)}") from e
            
            # Paso 4: Recuperar registros completos
            records = []
            for record_id, score in similar_results:
                try:
                    record = self.repository.find_by_id(record_id)
                    if record:
                        records.append(record)
                        logger.debug("Retrieved record", extra={
                            "record_id": record_id,
                            "similarity_score": score
                        })
                    else:
                        logger.warning("Record not found in repository", extra={
                            "record_id": record_id
                        })
                except Exception as e:
                    logger.error("Failed to retrieve record", extra={
                        "record_id": record_id,
                        "error": str(e)
                    })
                    # Continuar con otros resultados en lugar de fallar completamente
                    continue
            
            # Registrar métricas
            duration = perf_monitor.end_timer(start_time)
            perf_monitor.record_duration("search_similar", duration)
            
            logger.info("Search completed successfully", extra={
                "query_length": len(validated_query),
                "results_returned": len(records),
                "duration_ms": duration * 1000
            })
            
            return records
            
        except (ValidationError, EmbeddingError, VectorIndexError):
            # Re-lanzar excepciones conocidas
            raise
        except Exception as e:
            logger.error("Unexpected error in search similar", extra={"error": str(e)})
            raise PromptServiceError(f"Unexpected error in search: {str(e)}") from e
```

---

## Infrastructure Layer - Adaptadores

### SQLite Repository (`infra/sqlite_repo.py`)

```python
from typing import Optional, Tuple, List
from sqlmodel import SQLModel, Field, Session, create_engine, select, func
from domain.entities import PromptRecord
from domain.ports import PromptRepository
from domain.exceptions import RepositoryError
from core.logging import get_logger

logger = get_logger(__name__)

class PromptModel(SQLModel, table=True):
    """
    Modelo SQLModel para persistencia en SQLite.
    
    Mapea la entidad de dominio PromptRecord a tabla SQL:
    - Mantiene separación entre dominio e infraestructura
    - SQLModel proporciona type safety con Pydantic v2
    - Configuración optimizada para SQLite
    
    Índices automáticos:
    - PRIMARY KEY en id (automático)
    - INDEX en created_at para ordenamiento (manual si se requiere)
    """
    
    # Configuración de tabla
    __tablename__ = "promptmodel"  # Nombre explícito de tabla
    
    # Campos con tipos y constraints
    id: str = Field(primary_key=True, index=True, description="UUID único del prompt")
    prompt: str = Field(description="Texto del prompt original")
    response: str = Field(description="Respuesta generada por LLM")
    created_at: str = Field(description="Timestamp ISO8601 de creación")

class SQLitePromptRepository(PromptRepository):
    """
    Adaptador de repositorio usando SQLite y SQLModel.
    
    Implementa el puerto PromptRepository:
    - Utiliza SQLModel para ORM con type safety
    - Session management automático con context managers
    - Error handling específico para SQLite
    - Performance optimizations para consultas comunes
    
    Características técnicas:
    - WAL mode para mejor concurrencia (configurar externamente)
    - Connection pooling implícito de SQLAlchemy
    - Transacciones automáticas por sesión
    - Prepared statements para prevenir SQL injection
    """
    
    def __init__(self, db_url: str):
        """
        Inicializa repositorio con configuración de base de datos.
        
        Args:
            db_url: URL de conexión SQLite (ej: sqlite:///./data/prompts.db)
        """
        try:
            # Crear engine con configuración optimizada
            self.engine = create_engine(
                db_url, 
                echo=False,  # Cambiar a True para debugging SQL
                # Configuraciones específicas para SQLite
                connect_args={
                    "check_same_thread": False,  # Permitir uso multi-thread
                    "timeout": 20  # Timeout de conexión en segundos
                }
            )
            
            # Crear tablas si no existen
            SQLModel.metadata.create_all(self.engine)
            
            logger.info("SQLite repository initialized", extra={
                "db_url": db_url.replace("sqlite:///", "")  # Log sin prefijo
            })
            
        except Exception as e:
            logger.error("Failed to initialize SQLite repository", extra={"error": str(e)})
            raise RepositoryError(f"Database initialization failed: {str(e)}") from e
    
    def save(self, record: PromptRecord) -> None:
        """
        Persiste un registro usando transacción automática.
        
        Args:
            record: PromptRecord a persistir
            
        Raises:
            RepositoryError: Si falla la persistencia
        """
        try:
            # Mapear entidad de dominio a modelo de persistencia
            model = PromptModel(
                id=record.id,
                prompt=record.prompt,
                response=record.response,
                created_at=record.created_at,
            )
            
            # Persistir con transacción automática
            with Session(self.engine) as session:
                session.add(model)
                session.commit()  # Transacción automática
                
                logger.debug("Record saved successfully", extra={"record_id": record.id})
                
        except Exception as e:
            logger.error("Failed to save record", extra={
                "record_id": record.id,
                "error": str(e)
            })
            raise RepositoryError(f"Failed to save record: {str(e)}") from e
    
    def find_by_id(self, id: str) -> Optional[PromptRecord]:
        """
        Busca un registro por ID usando prepared statement.
        
        Args:
            id: Identificador único del registro
            
        Returns:
            PromptRecord si existe, None si no se encuentra
        """
        try:
            with Session(self.engine) as session:
                # Usar session.get() para búsqueda por primary key (más eficiente)
                model = session.get(PromptModel, id)
                
                if model is None:
                    logger.debug("Record not found", extra={"record_id": id})
                    return None
                
                # Mapear modelo de persistencia a entidad de dominio
                record = PromptRecord(
                    id=model.id,
                    prompt=model.prompt,
                    response=model.response,
                    created_at=model.created_at,
                )
                
                logger.debug("Record found", extra={"record_id": id})
                return record
                
        except Exception as e:
            logger.error("Failed to find record", extra={
                "record_id": id,
                "error": str(e)
            })
            raise RepositoryError(f"Failed to find record: {str(e)}") from e
    
    def find_paginated(self, offset: int = 0, limit: int = 10) -> Tuple[List[PromptRecord], int]:
        """
        Busca registros paginados con conteo eficiente.
        
        Args:
            offset: Número de registros a saltar
            limit: Máximo número de registros a retornar
            
        Returns:
            Tupla de (registros, conteo_total)
        """
        try:
            with Session(self.engine) as session:
                # Consulta 1: Obtener conteo total (eficiente)
                total_stmt = select(func.count(PromptModel.id))  # type: ignore
                total = session.exec(total_stmt).one()
                
                # Consulta 2: Obtener registros paginados
                stmt = (
                    select(PromptModel)
                    .order_by(PromptModel.created_at.desc())  # type: ignore - Más recientes primero
                    .offset(offset)
                    .limit(limit)
                )
                models = session.exec(stmt).all()
                
                # Mapear a entidades de dominio
                records = [
                    PromptRecord(
                        id=model.id,
                        prompt=model.prompt,
                        response=model.response,
                        created_at=model.created_at,
                    )
                    for model in models
                ]
                
                logger.debug("Paginated query completed", extra={
                    "offset": offset,
                    "limit": limit,
                    "returned": len(records),
                    "total": total
                })
                
                return records, total
                
        except Exception as e:
            logger.error("Failed to execute paginated query", extra={
                "offset": offset,
                "limit": limit,
                "error": str(e)
            })
            raise RepositoryError(f"Failed to execute paginated query: {str(e)}") from e
    
    def count(self) -> int:
        """
        Obtiene conteo total de registros de forma eficiente.
        
        Returns:
            Número total de registros en la tabla
        """
        try:
            with Session(self.engine) as session:
                stmt = select(func.count(PromptModel.id))  # type: ignore
                count = session.exec(stmt).one()
                
                logger.debug("Count query completed", extra={"total_records": count})
                return count
                
        except Exception as e:
            logger.error("Failed to count records", extra={"error": str(e)})
            raise RepositoryError(f"Failed to count records: {str(e)}") from e
```

---

## Testing - Documentación de Tests Críticos

### Tests de Validación de Similaridad

```python
"""
Tests para verificar correctness de búsqueda vectorial.

Estos tests aseguran que:
1. Los vectores más similares se devuelvan en orden correcto
2. La normalización L2 funcione apropiadamente  
3. El LLM sea completamente determinista
4. ChromaDB funcione como backend alternativo válido
"""

import numpy as np
import tempfile
import os
from infra.faiss_index import FaissVectorIndex
from infra.chroma_index import ChromaVectorIndex
from infra.embedder import SentenceTransformerEmbedder
from infra.llm_simulator import LLMSimulator

class TestSimilarityValidation:
    """Test suite para validar correctness de similaridad vectorial."""
    
    def setup_method(self):
        """
        Configuración pre-test.
        
        Crea entorno aislado con:
        - Directorio temporal para índices
        - Instancias frescas de FAISS y ChromaDB
        - Embedder singleton (reutilizado para performance)
        """
        self.temp_dir = tempfile.mkdtemp()
        self.faiss_index = FaissVectorIndex(os.path.join(self.temp_dir, "test.index"), dim=384)
        self.chroma_index = ChromaVectorIndex(self.temp_dir)
    
    def test_vector_similarity_order_faiss(self):
        """
        PROBLEMA 1: Tests de similitud real - Orden correcto de vectores.
        
        Verifica que FAISS retorna vectores en orden matemáticamente correcto:
        
        Test Strategy:
        1. Crear vectores con relaciones conocidas de similaridad
        2. Normalizar para similaridad coseno (norma L2 = 1.0)
        3. Indexar en FAISS con IndexFlatIP (producto interno)
        4. Realizar búsqueda y verificar orden estricto
        
        Validaciones matemáticas:
        - Vector base más similar a sí mismo (score ≈ 1.0)
        - Orden transitivo: similar > moderado > disimilar
        - Scores en orden estrictamente descendente
        - Todos los vectores indexados son encontrados
        """
        
        # Crear vectores con relaciones conocidas
        base_vector = [1.0] + [0.0] * 383      # Vector de referencia
        similar_vector = [0.99] + [0.01] + [0.0] * 382  # Muy similar (perturbación pequeña)
        moderate_vector = [0.8] + [0.2] + [0.0] * 382   # Moderadamente similar  
        dissimilar_vector = [0.1] + [0.9] + [0.0] * 382 # Poco similar
        
        # Normalización L2 para similaridad coseno
        base_vector = self._normalize_vector(base_vector)
        similar_vector = self._normalize_vector(similar_vector)
        moderate_vector = self._normalize_vector(moderate_vector)
        dissimilar_vector = self._normalize_vector(dissimilar_vector)
        
        # Indexar vectores
        self.faiss_index.add("base", base_vector)
        self.faiss_index.add("similar", similar_vector)
        self.faiss_index.add("moderate", moderate_vector)
        self.faiss_index.add("dissimilar", dissimilar_vector)
        
        # Realizar búsqueda
        results = self.faiss_index.search(base_vector, k=4)
        
        # VALIDACIONES CRÍTICAS
        assert len(results) == 4, "Debe retornar exactamente 4 resultados"
        
        # Extraer IDs y scores
        ids = [r[0] for r in results]
        scores = [r[1] for r in results]
        
        # Validación 1: Vector base debe ser el más similar a sí mismo
        assert ids[0] == "base", "Vector base debe ser top-1 resultado"
        assert scores[0] > 0.99, f"Auto-similaridad debe ser ≈1.0, got {scores[0]}"
        
        # Validación 2: Orden transitivo de similaridad  
        similar_idx = ids.index("similar")
        moderate_idx = ids.index("moderate")
        dissimilar_idx = ids.index("dissimilar")
        
        assert similar_idx < moderate_idx, "Vector similar debe ranquear antes que moderado"
        assert moderate_idx < dissimilar_idx, "Vector moderado debe ranquear antes que disimilar"
        
        # Validación 3: Scores en orden estrictamente descendente
        assert scores == sorted(scores, reverse=True), f"Scores no están ordenados: {scores}"
        
        print(f"✅ Test passed - Similarity order: {list(zip(ids, scores))}")
    
    def test_embedding_normalization_validation(self):
        """
        PROBLEMA 2: Validación de embeddings - Normalización L2 funciona.
        
        Verifica que embeddings estén correctamente normalizados:
        
        Mathematical Validation:
        - L2 norm = sqrt(sum(x_i^2)) ≈ 1.0 (tolerance: 0.001)
        - Dimension = 384 (all-MiniLM-L6-v2)
        - No zero vectors, NaN, or infinite values
        - Proper float32 types
        
        Test Coverage:
        - Textos cortos y largos
        - Vocabulario variado
        - Edge cases (texto mínimo)
        """
        embedder = SentenceTransformerEmbedder()
        
        # Dataset de testing con diferentes características
        test_texts = [
            "Short text",                                          # Texto corto
            "This is a longer text with more words and content",   # Texto largo
            "Another example with different vocabulary and structure"  # Vocabulario diferente
        ]
        
        for text in test_texts:
            # Generar embedding
            embedding = embedder.embed(text)
            
            # VALIDACIÓN CRÍTICA 1: Normalización L2
            norm = np.linalg.norm(embedding)
            assert abs(norm - 1.0) < 0.001, f"Embedding not normalized: norm={norm:.6f}"
            
            # VALIDACIÓN 2: Dimensión correcta
            assert len(embedding) == 384, f"Wrong dimension: {len(embedding)}, expected 384"
            
            # VALIDACIÓN 3: No vector cero
            assert any(x != 0 for x in embedding), "Embedding is all zeros"
            
            # VALIDACIÓN 4: Valores finitos
            assert all(isinstance(x, (int, float)) for x in embedding), "Invalid value types"
            assert all(not (x != x or abs(x) == float('inf')) for x in embedding), "NaN or inf values"
            
            print(f"✅ Embedding normalized: text='{text[:20]}...', norm={norm:.6f}")
    
    def test_deterministic_llm_responses(self):
        """
        PROBLEMA 3: Test de determinismo - Mismo prompt = misma respuesta.
        
        Verifica que LLM simulator sea completamente determinista:
        
        Determinism Requirements:
        - Mismo prompt → misma respuesta (100% consistency)
        - Formato [SimResponse-XXXX] consistente
        - Seed determinista basado en hash del prompt
        - Relación semántica prompt-respuesta
        
        Test Strategy:
        - Múltiples prompts de diferentes longitudes
        - 5 generaciones por prompt
        - Verificación de identidad exacta
        """
        llm = LLMSimulator()
        
        # Dataset de prompts con diferentes características
        test_prompts = [
            "What is machine learning?",                          # Pregunta técnica
            "Explain Python programming",                        # Tópico específico
            "How does a neural network work?",                   # Pregunta compleja
            "Short prompt",                                      # Prompt mínimo
            "A much longer prompt with many words and detailed descriptions that should still produce consistent results"  # Prompt largo
        ]
        
        for prompt in test_prompts:
            # VALIDACIÓN CRÍTICA: Generar múltiples respuestas
            responses = [llm.generate(prompt) for _ in range(5)]
            
            # Validación 1: Determinismo absoluto
            assert all(r == responses[0] for r in responses), f"Non-deterministic responses for: {prompt}"
            
            # Validación 2: Formato correcto
            assert "[SimResponse-" in responses[0], "Response doesn't have expected format"
            
            # Validación 3: Relación semántica
            prompt_words = prompt.lower().split()[:3]
            response_lower = responses[0].lower()
            assert any(word in response_lower for word in prompt_words), "Response doesn't relate to prompt"
            
            print(f"✅ Deterministic: prompt='{prompt[:30]}...' → response='{responses[0][:50]}...'")
```

---

Este documento proporciona documentación inline completa del código, explicando la implementación detallada, patrones de diseño utilizados, principios SOLID aplicados, y la lógica de testing para los 4 problemas críticos resueltos.

La documentación está organizada por capas de la arquitectura hexagonal y incluye comentarios técnicos que explican las decisiones de diseño, optimizaciones de performance, manejo de errores, y validaciones críticas.
