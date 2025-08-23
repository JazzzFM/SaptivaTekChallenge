# === VARIABLES ===
IMAGE_NAME = prompt-service
CONTAINER_NAME = prompt-service
PORT = 8080
VERSION = 1.0.0

# === DOCKER COMMANDS ===
.PHONY: build run stop clean test logs health stats

# Construir la imagen Docker
build:
	@echo "🔨 Construyendo imagen Docker..."
	docker build -t $(IMAGE_NAME):functional .
	docker tag $(IMAGE_NAME):functional $(IMAGE_NAME):latest
	@echo "✅ Imagen construida: $(IMAGE_NAME):functional"

# Ejecutar contenedor
run:
	@echo "🚀 Iniciando contenedor..."
	docker run -d \
		--name $(CONTAINER_NAME) \
		-p $(PORT):$(PORT) \
		-e PORT=$(PORT) \
		-e ENVIRONMENT=production \
		-e DATABASE_URL=sqlite:///./data/prompts.db \
		-e VECTOR_BACKEND=faiss \
		-e ENABLE_RATE_LIMITING=true \
		-e RATE_LIMIT_PER_MINUTE=60 \
		-e LOG_LEVEL=INFO \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/logs:/app/logs \
		$(IMAGE_NAME):latest
	@echo "✅ Contenedor iniciado en puerto $(PORT)"
	@echo "🌐 Servicio disponible en: http://localhost:$(PORT)"

# Usar docker-compose
up:
	@echo "🚀 Iniciando con docker-compose..."
	docker-compose up -d
	@echo "✅ Servicios iniciados"
	@echo "🌐 Servicio disponible en: http://localhost:$(PORT)"

# Parar servicios docker-compose
down:
	@echo "🛑 Deteniendo servicios..."
	docker-compose down
	@echo "✅ Servicios detenidos"

# Parar contenedor individual
stop:
	@echo "🛑 Deteniendo contenedor..."
	-docker stop $(CONTAINER_NAME)
	-docker rm $(CONTAINER_NAME)
	@echo "✅ Contenedor detenido"

# Ver logs
logs:
	@echo "📋 Mostrando logs..."
	docker logs -f $(CONTAINER_NAME)

# Ver logs con docker-compose
logs-compose:
	@echo "📋 Mostrando logs (docker-compose)..."
	docker-compose logs -f

# Limpiar imágenes y contenedores
clean:
	@echo "🧹 Limpiando contenedores e imágenes..."
	-docker stop $(CONTAINER_NAME)
	-docker rm $(CONTAINER_NAME)
	-docker rmi $(IMAGE_NAME):$(VERSION)
	-docker rmi $(IMAGE_NAME):latest
	docker system prune -f
	@echo "✅ Limpieza completada"

# === TESTING ===
# Ejecutar tests en contenedor
test:
	@echo "🧪 Ejecutando tests en contenedor..."
	docker run --rm \
		-v $(PWD):/app \
		$(IMAGE_NAME):latest \
		python -m pytest tests/ -v --cov

# === HEALTH CHECKS ===
# Verificar salud del servicio
health:
	@echo "🏥 Verificando salud del servicio..."
	@curl -s http://localhost:$(PORT)/health | jq '.' || echo "❌ Servicio no disponible"

# Verificar salud detallada
health-detailed:
	@echo "🏥 Verificando salud detallada..."
	@curl -s http://localhost:$(PORT)/health/detailed | jq '.' || echo "❌ Servicio no disponible"

# Ver estadísticas del servicio
stats:
	@echo "📊 Estadísticas del servicio..."
	@curl -s http://localhost:$(PORT)/stats | jq '.' || echo "❌ Servicio no disponible"

# === DEVELOPMENT ===
# Rebuild y restart rápido
restart: stop build run
	@echo "🔄 Servicio reiniciado"

# Monitor en tiempo real
monitor:
	@echo "👀 Monitoreando servicio..."
	@while true; do \
		echo "=== $$(date) ===" ; \
		curl -s http://localhost:$(PORT)/health | jq '.timestamp = now | .uptime = now - .timestamp' ; \
		sleep 10 ; \
	done

# === LINT & QUALITY ===
lint:
	@echo "🔍 Ejecutando linters..."
	ruff check .
	mypy . --python-version=3.11
	@echo "✅ Linting completado"

# === HELP ===
help:
	@echo "🚀 Prompt Service - Docker Commands"
	@echo ""
	@echo "📦 Build & Run:"
	@echo "  make build          - Construir imagen Docker"
	@echo "  make run            - Ejecutar contenedor individual"
	@echo "  make up             - Iniciar con docker-compose"
	@echo "  make down           - Parar servicios docker-compose"
	@echo "  make stop           - Parar contenedor individual"
	@echo "  make restart        - Rebuild y restart rápido"
	@echo ""
	@echo "📋 Logs & Monitoring:"
	@echo "  make logs           - Ver logs del contenedor"
	@echo "  make logs-compose   - Ver logs docker-compose"
	@echo "  make monitor        - Monitor en tiempo real"
	@echo ""
	@echo "🏥 Health Checks:"
	@echo "  make health         - Health check básico"
	@echo "  make health-detailed - Health check detallado"
	@echo "  make stats          - Estadísticas del servicio"
	@echo ""
	@echo "🔍 Quality:"
	@echo "  make lint           - Ejecutar linters"
	@echo "  make test           - Ejecutar tests"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean          - Limpiar contenedores e imágenes"
	@echo ""
	@echo "🌐 URL: http://localhost:$(PORT)"
