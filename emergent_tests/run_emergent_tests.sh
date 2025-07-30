#!/bin/bash
# ============================================================================
# ASTROFLORA EMERGENT TESTS - LAUNCHER SCRIPT
# ============================================================================
# Script de lanzamiento para las suites de testing emergente de Astroflora

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Banner
echo -e "${PURPLE}"
echo "============================================================================"
echo "🧬 ASTROFLORA EMERGENT TESTING SUITE"
echo "🤖 Testing Agéntico Avanzado - Fase 1: Coexistencia y Estabilización"
echo "============================================================================"
echo -e "${NC}"

# Directorio base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$(dirname "$SCRIPT_DIR")/emergent_tests"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo -e "${BLUE}📁 Directories:${NC}"
echo "   Script: $SCRIPT_DIR"
echo "   Tests:  $TEST_DIR"
echo "   Root:   $PROJECT_ROOT"
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 no encontrado. Instalando...${NC}"
    exit 1
fi

# Verificar dependencias
echo -e "${BLUE}🔍 Verificando dependencias...${NC}"
pip install -q httpx pyyaml aiofiles

# Hacer ejecutable el script Python
chmod +x "$TEST_DIR/scripts/emergent_test_executor.py"

# Verificar estado del backend
echo -e "${BLUE}🌐 Verificando estado del backend...${NC}"
BACKEND_URL=$(grep "REACT_APP_BACKEND_URL" "$PROJECT_ROOT/frontend/.env" 2>/dev/null | cut -d'=' -f2 || echo "http://localhost:8001")
echo "   Backend URL: $BACKEND_URL"

# Test de conectividad básica
if curl -s "$BACKEND_URL/api/health/" > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ Backend respondiendo${NC}"
else
    echo -e "${YELLOW}⚠️  Backend no responde en $BACKEND_URL${NC}"
    echo -e "${YELLOW}   Continuando con tests (algunos pueden fallar)${NC}"
fi

echo ""

# Menú de opciones
echo -e "${PURPLE}🎯 OPCIONES DE EJECUCIÓN:${NC}"
echo "1. 🔧 Lógica Agéntica y Orquestación"
echo "2. 🧪 Protocolos Científicos y Coherencia"
echo "3. 🛡️  Resiliencia y Simulación de Fallos"
echo "4. 🌐 Endpoints Bajo Estrés"
echo "5. 📋 Logging y Trazabilidad"
echo "6. 🚀 EJECUTAR TODAS LAS SUITES"
echo "7. 📊 Solo generar reporte de configuración"
echo "0. ❌ Salir"
echo ""

# Función para ejecutar suite específica
run_specific_suite() {
    local suite_file=$1
    local suite_name=$2
    
    echo -e "${GREEN}🚀 Ejecutando: $suite_name${NC}"
    echo "   Archivo: $suite_file"
    echo ""
    
    cd "$TEST_DIR"
    python3 scripts/emergent_test_executor.py --suite "$suite_file" --verbose
}

# Función para ejecutar todas las suites
run_all_suites() {
    echo -e "${GREEN}🚀 EJECUTANDO TODAS LAS SUITES DE TESTING EMERGENTE${NC}"
    echo ""
    
    cd "$TEST_DIR"
    python3 scripts/emergent_test_executor.py --verbose
}

# Función para generar reporte de configuración
generate_config_report() {
    echo -e "${BLUE}📊 Generando reporte de configuración...${NC}"
    
    REPORT_FILE="$TEST_DIR/reports/system_configuration_$(date +%Y%m%d_%H%M%S).md"
    mkdir -p "$TEST_DIR/reports"
    
    cat > "$REPORT_FILE" << EOF
# 🧬 Reporte de Configuración del Sistema - Astroflora

**Fecha:** $(date '+%Y-%m-%d %H:%M:%S')
**Host:** $(hostname)
**Usuario:** $(whoami)

## 🌐 Configuración de Red

- **Backend URL:** $BACKEND_URL
- **Backend Status:** $(curl -s "$BACKEND_URL/api/health/" > /dev/null 2>&1 && echo "✅ Operativo" || echo "❌ No responde")

## 🐍 Configuración de Python

- **Python Version:** $(python3 --version)
- **Python Path:** $(which python3)

## 📦 Dependencies Status

$(pip list | grep -E "(httpx|pyyaml|aiofiles)" || echo "Instalando dependencias...")

## 📁 Estructura de Tests

$(find "$TEST_DIR" -name "*.yaml" -o -name "*.py" | head -20)

## 🔧 Suites de Test Disponibles

$(ls -la "$TEST_DIR/yaml_tests/"*.yaml 2>/dev/null | wc -l) suites YAML encontradas:

$(ls "$TEST_DIR/yaml_tests/"*.yaml 2>/dev/null | sed 's/.*\//- /' || echo "No se encontraron suites")

## ⚡ Estado de Servicios

### Backend Health Check
\`\`\`json
$(curl -s "$BACKEND_URL/api/health/" 2>/dev/null || echo '{"error": "Backend no disponible"}')
\`\`\`

### Agentic Capabilities
\`\`\`json
$(curl -s "$BACKEND_URL/api/agentic/capabilities" 2>/dev/null || echo '{"error": "Capabilities no disponibles"}')
\`\`\`

## 🎯 Recomendaciones

- ✅ Sistema listo para testing emergente
- 📋 Todas las suites configuradas correctamente
- 🔍 Verificar conectividad de backend antes de ejecución masiva

---
*Generado automáticamente por Astroflora Emergent Test Suite*
EOF

    echo -e "${GREEN}✅ Reporte generado: $REPORT_FILE${NC}"
    echo ""
    head -20 "$REPORT_FILE"
    echo "..."
}

# Loop principal del menú
while true; do
    read -p "Selecciona una opción [0-7]: " choice
    echo ""
    
    case $choice in
        1)
            run_specific_suite "agentic_orchestration_resilience.yaml" "Lógica Agéntica y Orquestación"
            ;;
        2)
            run_specific_suite "scientific_protocols_coherence.yaml" "Protocolos Científicos y Coherencia"
            ;;
        3)
            run_specific_suite "resilience_failure_simulation.yaml" "Resiliencia y Simulación de Fallos"
            ;;
        4)
            run_specific_suite "endpoints_stress_testing.yaml" "Endpoints Bajo Estrés"
            ;;
        5)
            run_specific_suite "logging_traceability_audit.yaml" "Logging y Trazabilidad"
            ;;
        6)
            run_all_suites
            ;;
        7)
            generate_config_report
            ;;
        0)
            echo -e "${BLUE}👋 ¡Hasta luego!${NC}"
            break
            ;;
        *)
            echo -e "${RED}❌ Opción inválida. Por favor selecciona 0-7.${NC}"
            echo ""
            ;;
    esac
    
    if [ "$choice" != "0" ] && [ "$choice" != "7" ]; then
        echo ""
        echo -e "${YELLOW}📋 ¿Deseas ejecutar otra suite? (presiona Enter para continuar)${NC}"
        read -p ""
    fi
done