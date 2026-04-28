.PHONY: help up down logs status build clean test env restart bash-backend bash-frontend push pull

DOCKER_COMPOSE := docker-compose -f infra/docker-compose.yml
PROJECT_NAME := visor360

# Variables de colores
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Mostrar esta ayuda
	@echo "$(BLUE)Visor 360 - Makefile$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Ejemplo:$(NC)"
	@echo "  make up              # Iniciar contenedores"
	@echo "  make logs service=backend"
	@echo ""

# ========== DOCKER COMPOSE ==========

up: .env ## Iniciar contenedores
	@echo "$(BLUE)Iniciando contenedores...$(NC)"
	$(DOCKER_COMPOSE) up -d --build
	@echo "$(GREEN)✓ Contenedores iniciados$(NC)"
	@echo ""
	@echo "$(BLUE)Accesos:$(NC)"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  Backend:   http://localhost:8000"

down: ## Detener contenedores
	@echo "$(BLUE)Deteniendo contenedores...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Contenedores detenidos$(NC)"

restart: ## Reiniciar contenedores
	@echo "$(BLUE)Reiniciando contenedores...$(NC)"
	$(DOCKER_COMPOSE) restart
	@echo "$(GREEN)✓ Contenedores reiniciados$(NC)"

build: ## Construir imágenes
	@echo "$(BLUE)Construyendo imágenes...$(NC)"
	$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✓ Imágenes construidas$(NC)"

status: ## Ver estado de contenedores
	@$(DOCKER_COMPOSE) ps

# ========== LOGS ==========

logs: ## Ver logs (ej: make logs service=backend)
	@$(DOCKER_COMPOSE) logs -f $(if $(service),$(service),'')

logs-backend: ## Ver logs del backend
	@$(DOCKER_COMPOSE) logs -f --tail 100 backend

logs-frontend: ## Ver logs del frontend
	@$(DOCKER_COMPOSE) logs -f --tail 100 frontend

# ========== BASH/SHELL ==========

bash-backend: ## Acceder a shell del backend
	@$(DOCKER_COMPOSE) exec backend bash

bash-frontend: ## Acceder a shell del frontend
	@$(DOCKER_COMPOSE) exec frontend sh

# ========== TESTING ==========

test: test-backend test-frontend ## Ejecutar todos los tests

test-backend: ## Probar endpoint backend
	@echo "$(BLUE)Probando backend...$(NC)"
	@curl -s http://localhost:8000/ | jq . 2>/dev/null || echo "Backend no responde"

test-frontend: ## Probar frontend
	@echo "$(BLUE)Probando frontend...$(NC)"
	@curl -s http://localhost:3000/ | grep -q "DOCTYPE" && echo "$(GREEN)✓ Frontend responde$(NC)" || echo "$(RED)✗ Frontend no responde$(NC)"

# ========== CLEANUP ==========

clean: ## Limpiar Docker (⚠️ elimina todo)
	@echo "$(YELLOW)Advertencia: Esto eliminará contenedores y volúmenes$(NC)"
	@read -p "¿Continuar? (s/n): " confirm && [ "$$confirm" = "s" ] && docker system prune -a --volumes || echo "Cancelado"

prune: ## Limpiar solo imágenes no usadas
	@docker image prune -a
	@echo "$(GREEN)✓ Limpieza completada$(NC)"

# ========== ENVIRONMENT ==========

.env: .env.prod
	@echo "$(YELLOW)Creando .env desde .env.prod...$(NC)"
	@cp infra/.env.prod infra/.env
	@echo "$(GREEN)✓ .env creado$(NC)"
	@echo "$(YELLOW)⚠️  Edita infra/.env y agrega tus credenciales$(NC)"

env: ## Mostrar variables de entorno configuradas
	@if [ -f "infra/.env" ]; then \
		echo "$(GREEN).env existe$(NC)"; \
		grep -v '^\#' infra/.env | grep '='; \
	else \
		echo "$(RED)Archivo .env no encontrado$(NC)"; \
		$(MAKE) .env; \
	fi

# ========== GIT HELPERS ==========

push: ## Hacer push a git (sin .env)
	@echo "$(BLUE)Verificando archivos sensibles...$(NC)"
	@if git ls-files infra/.env >/dev/null 2>&1; then \
		echo "$(RED)✗ .env está en git! Debes removerl$(NC)"; \
		git rm --cached infra/.env; \
		exit 1; \
	fi
	@echo "$(GREEN)✓ Seguro para push$(NC)"
	@git push

# ========== UTILITIES ==========

info: ## Mostrar información del proyecto
	@echo "$(BLUE)========== Visor 360 ===========$(NC)"
	@echo "$(BLUE)Estado de contenedores:$(NC)"
	@$(DOCKER_COMPOSE) ps || echo "No hay contenedores ejecutándose"
	@echo ""
	@echo "$(BLUE)Imágenes Docker:$(NC)"
	@docker images | grep $(PROJECT_NAME) || echo "No hay imágenes del proyecto"
	@echo ""
	@echo "$(BLUE)Redes:$(NC)"
	@docker network ls | grep $(PROJECT_NAME) || echo "Red no creada"

version: ## Mostrar versiones
	@echo "Docker: $$(docker --version)"
	@echo "Docker Compose: $$(docker-compose --version)"

# ========== PROD COMMANDS ==========

deploy: ## Deploy a producción (requires Rocky Linux)
	@echo "$(YELLOW)Deploy a Rocky Linux$(NC)"
	@echo "1. Conecta al servidor: ssh root@tu_ip"
	@echo "2. Clona el repositorio"
	@echo "3. Ejecuta: cd /opt/visor360 && make up"

logs-prod: ## Ver logs en servidor
	@ssh -C root@${SERVER_IP} "cd /opt/visor360 && docker-compose -f infra/docker-compose.yml logs -f"

.PHONY: .env
