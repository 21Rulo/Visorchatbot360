#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

DOCKER_COMPOSE="docker-compose -f infra/docker-compose.yml"

# Funciones
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

# Verificar que estamos en el directorio correcto
if [ ! -f "infra/docker-compose.yml" ]; then
    print_error "No se encontró infra/docker-compose.yml"
    print_warning "Ejecuta este script desde la raíz del proyecto"
    exit 1
fi

# Verificar Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker no está instalado"
    exit 1
fi

# Menú principal
case "${1}" in
    up)
        print_header "Iniciando contenedores..."
        $DOCKER_COMPOSE up -d --build
        if [ $? -eq 0 ]; then
            print_success "Contenedores iniciados"
            echo -e "\n${BLUE}Accesos:${NC}"
            echo "  Frontend:  http://localhost:3000"
            echo "  Backend:   http://localhost:8000"
        else
            print_error "Error al iniciar contenedores"
            exit 1
        fi
        ;;

    down)
        print_header "Deteniendo contenedores..."
        $DOCKER_COMPOSE down
        print_success "Contenedores detenidos"
        ;;

    restart)
        print_header "Reiniciando contenedores..."
        $DOCKER_COMPOSE restart
        print_success "Contenedores reiniciados"
        ;;

    logs)
        print_header "Mostrando logs..."
        service="${2:-all}"
        if [ "$service" = "all" ]; then
            $DOCKER_COMPOSE logs -f
        else
            $DOCKER_COMPOSE logs -f "$service"
        fi
        ;;

    status)
        print_header "Estado de contenedores"
        $DOCKER_COMPOSE ps
        ;;

    bash-backend)
        print_header "Accediendo a backend"
        $DOCKER_COMPOSE exec backend bash
        ;;

    bash-frontend)
        print_header "Accediendo a frontend"
        $DOCKER_COMPOSE exec frontend sh
        ;;

    build)
        print_header "Construyendo imágenes..."
        $DOCKER_COMPOSE build
        print_success "Imágenes construidas"
        ;;

    clean)
        print_header "Limpiando Docker..."
        print_warning "Esto eliminará contenedores, volúmenes y redes no utilizados"
        read -p "¿Continuar? (s/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Ss]$ ]]; then
            docker system prune -a --volumes
            print_success "Sistema limpiado"
        fi
        ;;

    test-backend)
        print_header "Probando backend..."
        curl -s http://localhost:8000/ | jq . || echo "Backend no responde"
        ;;

    test-frontend)
        print_header "Probando frontend..."
        curl -s http://localhost:3000/ | head -20
        ;;

    logs-backend)
        $DOCKER_COMPOSE logs -f --tail 50 backend
        ;;

    logs-frontend)
        $DOCKER_COMPOSE logs -f --tail 50 frontend
        ;;

    env)
        print_header "Verificando variables de entorno"
        if [ -f "infra/.env" ]; then
            echo -e "${GREEN}.env existe${NC}"
            grep -v '^#' infra/.env | grep '='
        else
            print_warning "Archivo .env no encontrado"
            print_header "Creando desde .env.prod..."
            cp infra/.env.prod infra/.env
            print_success ".env creado desde .env.prod"
            print_warning "Edita infra/.env y agrega tus credenciales"
        fi
        ;;

    *)
        echo -e "${BLUE}Visor 360 - Script de Docker${NC}"
        echo ""
        echo "Uso: $0 [comando]"
        echo ""
        echo "Comandos disponibles:"
        echo "  ${GREEN}up${NC}              - Iniciar contenedores"
        echo "  ${GREEN}down${NC}            - Detener contenedores"
        echo "  ${GREEN}restart${NC}         - Reiniciar contenedores"
        echo "  ${GREEN}status${NC}          - Ver estado de contenedores"
        echo "  ${GREEN}logs${NC}            - Ver logs (ej: logs backend)"
        echo "  ${GREEN}logs-backend${NC}    - Ver logs del backend"
        echo "  ${GREEN}logs-frontend${NC}   - Ver logs del frontend"
        echo "  ${GREEN}bash-backend${NC}    - Acceder a shell del backend"
        echo "  ${GREEN}bash-frontend${NC}   - Acceder a shell del frontend"
        echo "  ${GREEN}build${NC}           - Construir imágenes"
        echo "  ${GREEN}clean${NC}           - Limpiar sistema Docker"
        echo "  ${GREEN}test-backend${NC}    - Probar backend"
        echo "  ${GREEN}test-frontend${NC}   - Probar frontend"
        echo "  ${GREEN}env${NC}             - Configurar variables de entorno"
        echo ""
        echo "Ejemplo:"
        echo "  $0 up"
        echo "  $0 logs backend"
        echo "  $0 bash-backend"
        echo ""
        ;;
esac
