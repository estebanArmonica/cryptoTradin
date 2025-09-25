#!/bin/bash

# ============================================================
# Script para levantar proyecto de FastiAPI con Docker
# Autor: Esteban Lobos y Ricardo Alcantar
# Correo: esteban.hernan.lobos@gmail.com, 
# Fecha: 2025-09-25
# Versión: 2.0
# Descripción: Este script automatiza la construcción y el despliegue
#              de un proyecto FastAPI utilizando Docker y Docker Compose.
# ============================================================

set -euo pipefail # Detiene en errores, variables no definidas y pipes failures

# ============================================================
# Confirguración de variables editables
# ============================================================
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly SRC_DIR="${SCRIPT_DIR}/src"
readonly REQUIREMENTS_FILE="requirements.txt"
readonly APP_MODULE="app.main:app"
readonly HOST="0.0.0.0"
readonly PORT="8000"

# =============================================================================
# Colores para output en terminal
# =============================================================================
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# =============================================================================
# Funciones de utilidad
# =============================================================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

check_directory_exists() {
    if [ ! -d "$1" ]; then
        log_error "Directorio no encontrado: $1"
        return 1
    fi
}

check_file_exists() {
    if [ ! -f "$1" ]; then
        log_error "Archivo no encontrado: $1"
        return 1
    fi
}

# =============================================================================
# Función principal
# =============================================================================
main() {
    log_info "Iniciando despliegue del proyecto..."
    log_info "Directorio del script: $SCRIPT_DIR"
    log_info "Directorio raíz del proyecto: $PROJECT_ROOT"

    # Validaciones previas
    log_info "Validando estructura del proyecto..."

    check_file_exists "$REQUIREMENTS_FILE" || exit 1
    check_directory_exists "$SRC_DIR" || exit 1

    # Instalar dependencias
    log_info "Instalando dependencias desde: $REQUIREMENTS_FILE"
    
    if pip install -r "$REQUIREMENTS_FILE"; then
        log_success "Dependencias instaladas correctamente"
    else
        log_error "Error al instalar dependencias"
        exit 1
    fi

    # Cambiar al directorio src y ejecutar la aplicación
    log_info "Cambiando al directorio: $SRC_DIR"
    
    if cd "$SRC_DIR"; then
        log_success "Directorio cambiado correctamente"
        log_info "Directorio actual: $(pwd)"
    else
        log_error "No se pudo cambiar al directorio: $SRC_DIR"
        exit 1
    fi

    # Ejecutar la aplicación
    log_info "Iniciando servidor FastAPI..."
    log_info "Módulo: $APP_MODULE"
    log_info "Host: $HOST, Puerto: $PORT"
    log_info "La aplicación estará disponible en: http://${HOST}:${PORT}"
    log_warning "Presiona Ctrl+C para detener el servidor"
    echo ""

    # Ejecutar el servidor
    exec python -m uvicorn "$APP_MODULE" --reload --host "$HOST" --port "$PORT"
}

# =============================================================================
# Punto de entrada del script
# =============================================================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
