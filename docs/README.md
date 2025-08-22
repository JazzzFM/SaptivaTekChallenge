# Índice de Documentación - SaptivaTekChallenge

**Generado**: 2025-08-21 22:00:51

## Documentos Principales

### 📋 Resumen Ejecutivo
- **HTML**: [docs/reports/EXECUTIVE_SUMMARY.html](reports/EXECUTIVE_SUMMARY.html)
- **PDF**: [docs/pdf/EXECUTIVE_SUMMARY.pdf](pdf/EXECUTIVE_SUMMARY.pdf) (si disponible)
- **Markdown**: [docs/EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)

### 🔧 Documentación Técnica  
- **HTML**: [docs/reports/TECHNICAL_DOCUMENTATION.html](reports/TECHNICAL_DOCUMENTATION.html)
- **PDF**: [docs/pdf/TECHNICAL_DOCUMENTATION.pdf](pdf/TECHNICAL_DOCUMENTATION.pdf) (si disponible)
- **Markdown**: [docs/TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)

### 🧪 Reporte de Testing
- **HTML**: [docs/reports/TEST_REPORT.html](reports/TEST_REPORT.html)  
- **PDF**: [docs/pdf/TEST_REPORT.pdf](pdf/TEST_REPORT.pdf) (si disponible)
- **Markdown**: [docs/TEST_REPORT.md](TEST_REPORT.md)

## Archivos de Código Documentados

### Arquitectura
- `domain/` - Entidades y puertos (interfaces)
- `use_cases/` - Lógica de aplicación
- `infra/` - Adaptadores e implementaciones
- `api/` - Controllers y DTOs FastAPI
- `core/` - Servicios centrales (DI, logging, seguridad)

### Testing
- `tests/test_similarity_validation.py` - Tests de similaridad vectorial
- `tests/test_chroma_integration.py` - Tests de ChromaDB
- `tests/test_seed_integration.py` - Tests de datos reproducibles

## Scripts de Utilidad
- `scripts/seed_data.py` - Generación de datos reproducibles
- `scripts/generate_docs.py` - Generación de documentación

## Configuración
- `.env.example` - Variables de entorno documentadas
- `pyproject.toml` - Configuración de proyecto y herramientas
- `requirements.txt` - Dependencias Python

---

**Estado del Proyecto**: ✅ PRODUCTION READY

**Tests Críticos**: ✅ 4/4 IMPLEMENTADOS Y FUNCIONANDO
1. Tests de similitud real
2. Validación de embeddings L2  
3. Test de determinismo LLM
4. Tests de ChromaDB completos

**Calidad**: ✅ Linting clean, Type checking clean, 130+ tests
