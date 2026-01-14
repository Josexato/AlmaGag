#!/bin/bash
# Script para regenerar documentación SVG desde archivos .gag
#
# Uso:
#     ./scripts/generate_docs.sh [--verbose]

set -e

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Funciones
print_header() {
    echo -e "\n${BOLD}${BLUE}======================================================================${NC}"
    echo -e "${BOLD}${BLUE}                    $1${NC}"
    echo -e "${BOLD}${BLUE}======================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Variables
VERBOSE=false
if [[ "$*" == *"--verbose"* ]] || [[ "$*" == *"-v"* ]]; then
    VERBOSE=true
fi

GAGS_DIR="docs/diagrams/gags"
SVGS_DIR="docs/diagrams/svgs"
SUCCESS_COUNT=0
ERROR_COUNT=0

print_header "Generador de Documentación SVG - AlmaGag"

# Verificar que existe el directorio de gags
if [ ! -d "$GAGS_DIR" ]; then
    print_error "Directorio no encontrado: $GAGS_DIR"
    exit 1
fi

# Crear directorio de SVGs si no existe
if [ ! -d "$SVGS_DIR" ]; then
    print_info "Creando directorio: $SVGS_DIR"
    mkdir -p "$SVGS_DIR"
fi

# Contar archivos .gag
GAG_FILES=("$GAGS_DIR"/*.gag)
TOTAL=${#GAG_FILES[@]}

if [ "$TOTAL" -eq 0 ] || [ ! -f "${GAG_FILES[0]}" ]; then
    print_error "No se encontraron archivos .gag en $GAGS_DIR"
    exit 1
fi

print_info "Encontrados $TOTAL archivos .gag en $GAGS_DIR"
echo

# Procesar cada archivo
COUNTER=0
for GAG_FILE in "${GAG_FILES[@]}"; do
    ((COUNTER++))
    FILENAME=$(basename "$GAG_FILE")
    SVG_NAME="${FILENAME%.gag}.svg"

    echo -e "[$COUNTER/$TOTAL] Procesando: ${BOLD}$FILENAME${NC}"

    # Generar SVG
    if [ "$VERBOSE" = true ]; then
        python -m AlmaGag.main "$GAG_FILE"
    else
        python -m AlmaGag.main "$GAG_FILE" > /dev/null 2>&1
    fi

    if [ $? -eq 0 ]; then
        # Verificar que el SVG se generó
        if [ -f "$SVG_NAME" ]; then
            # Mover al directorio de docs
            mv "$SVG_NAME" "$SVGS_DIR/"
            if [ $? -eq 0 ]; then
                print_success "Generado: $SVG_NAME → $SVGS_DIR/"
                ((SUCCESS_COUNT++))
            else
                print_error "Error moviendo $SVG_NAME"
                ((ERROR_COUNT++))
            fi
        else
            print_error "SVG no generado: $SVG_NAME"
            ((ERROR_COUNT++))
        fi
    else
        print_error "Error generando $FILENAME"
        ((ERROR_COUNT++))
    fi

    echo
done

# Reporte final
print_header "Reporte Final"

echo -e "  Total procesados:  ${BOLD}$TOTAL${NC}"
echo -e "  ${GREEN}Exitosos:${NC}        $SUCCESS_COUNT"
echo -e "  ${RED}Errores:${NC}          $ERROR_COUNT"
echo

if [ "$ERROR_COUNT" -eq 0 ]; then
    print_success "Toda la documentación se generó correctamente"
    exit 0
else
    print_error "Algunos archivos fallaron ($ERROR_COUNT/$TOTAL)"
    exit 1
fi
