# 🧬 Astroflora Emergent Testing Suite

## 🎯 Visión General

Esta suite de testing emergente está diseñada específicamente para validar las capacidades agénticas avanzadas de Astroflora en su **Fase 1: Coexistencia y Estabilización**. Va más allá de los tests básicos para cubrir lógica agéntica compleja, coherencia científica, resiliencia ante fallos y comportamiento bajo estrés.

## 🏗️ Arquitectura de Testing

### 📋 Suites de Test Disponibles

1. **🔧 Lógica Agéntica y Orquestación** (`agentic_orchestration_resilience.yaml`)
   - Recomendación inteligente de herramientas basada en contexto científico
   - Coherencia en evaluación de aplicabilidad de herramientas  
   - Métricas del gateway bajo carga concurrente
   - Resiliencia ante fallos de herramientas individuales
   - Orquestación dinámica de protocolos científicos

2. **🧪 Protocolos Científicos y Coherencia** (`scientific_protocols_coherence.yaml`)
   - Validación de coherencia científica en resultados BLAST
   - Integridad de anotaciones UniProt
   - Precisión de características computacionales de secuencias
   - Consistencia en análisis LLM con diferentes profundidades
   - Coherencia cross-tool entre herramientas

3. **🛡️ Resiliencia y Simulación de Fallos** (`resilience_failure_simulation.yaml`)
   - Simulación de fallos de servicios bioinformáticos externos
   - Validación de circuit breakers y recovery mechanisms
   - Comportamiento con secuencias inválidas o malformadas
   - Testing de concurrencia y gestión de capacidad
   - Mecanismos de fallback y auto-recuperación

4. **🌐 Endpoints Bajo Estrés** (`endpoints_stress_testing.yaml`)
   - Testing exhaustivo de `/api/analysis/` bajo diferentes escenarios
   - Validación de `/api/health/` bajo estrés del sistema
   - Cobertura completa de los 15+ endpoints agénticos `/api/agentic/`
   - Parámetros extremos y edge cases
   - Rate limiting y autenticación bajo carga

5. **📋 Logging y Trazabilidad** (`logging_traceability_audit.yaml`)
   - Trazabilidad científica end-to-end de experimentos
   - Logs científicos detallados con metadatos completos
   - Auditoría de invocaciones de herramientas
   - Logging bajo condiciones extremas
   - Reproducibilidad y compliance científico

## 🚀 Ejecución

### Opción 1: Script Interactivo (Recomendado)

```bash
cd /app/emergent_tests
chmod +x run_emergent_tests.sh
./run_emergent_tests.sh
```

El script presenta un menú interactivo para:
- Ejecutar suites individuales
- Ejecutar todas las suites
- Generar reportes de configuración
- Verificar estado del sistema

### Opción 2: Ejecutor Python Directo

```bash
cd /app/emergent_tests

# Ejecutar todas las suites
python3 scripts/emergent_test_executor.py --verbose

# Ejecutar suite específica
python3 scripts/emergent_test_executor.py --suite agentic_orchestration_resilience.yaml

# Con configuración personalizada
python3 scripts/emergent_test_executor.py --config custom_config.yaml
```

### Opción 3: Suite Individual

```bash
# Solo la suite de lógica agéntica
python3 scripts/emergent_test_executor.py --suite agentic_orchestration_resilience.yaml
```

## 📊 Reportes y Resultados

### Ubicación de Reportes

Los reportes se generan automáticamente en:
```
/app/emergent_tests/reports/
├── emergent_test_report_YYYYMMDD_HHMMSS.json  # Reporte detallado
├── emergent_test_summary_YYYYMMDD_HHMMSS.md   # Resumen ejecutivo
└── system_configuration_YYYYMMDD_HHMMSS.md    # Configuración del sistema
```

### Formato de Reportes

- **JSON**: Datos completos, estructurados para análisis programático
- **Markdown**: Resúmenes ejecutivos legibles para humanos
- **Console**: Output en tiempo real durante ejecución

## 🔧 Configuración

### Variables de Entorno

El sistema utiliza automáticamente:
- `REACT_APP_BACKEND_URL` desde `/app/frontend/.env`
- API Key predefinida para testing

### Configuración Personalizada

Crear archivo `custom_config.yaml`:

```yaml
backend_url: "https://mi-backend-custom.com"
api_key: "mi-api-key-personalizada"
timeout: 300
parallel_execution: false
verbose: true
```

## 🎯 Criterios de Éxito

### Por Suite

- **Lógica Agéntica**: ≥90% success rate en recomendaciones inteligentes
- **Protocolos Científicos**: ≥95% coherencia científica
- **Resiliencia**: ≥90% recovery success rate
- **Endpoints**: ≥99% disponibilidad bajo estrés
- **Logging**: 100% trazabilidad y audit readiness

### Global

- **Overall Success Rate**: ≥90%
- **No Data Corruption**: 100%
- **Scientific Accuracy**: ≥95%
- **Graceful Degradation**: 100%

## 🧪 Casos de Test Destacados

### Recomendación Inteligente de Herramientas

```yaml
- context:
    sequence_info: {type: "protein", length: 350}
    analysis_goal: "function_prediction"
  expected:
    - "blast_search en top 3 recomendaciones"
    - "uniprot_annotations incluido si score > 0.7"
    - "llm_analysis útil con múltiples fuentes"
```

### Coherencia Científica BLAST

```yaml
- validation:
    - "E-values ≤ threshold configurado"
    - "Identity scores entre 0-100"
    - "Interpretación evolutionary coherente con identidad"
    - "Taxonomic distribution análisis válido"
```

### Simulación de Fallos

```yaml
- failure_scenarios:
    - "BLAST timeout → circuit breaker activation"
    - "UniProt rate limit → graceful fallback"
    - "Sequence inválida → error estructurado"
```

## 🔍 Validaciones Científicas

### Nivel 1: Estructura de Datos
- Formato correcto de respuestas
- Campos requeridos presentes
- Tipos de datos apropiados

### Nivel 2: Coherencia Lógica
- Valores dentro de rangos científicos válidos
- Consistencia entre campos relacionados
- Lógica de interpretación apropiada

### Nivel 3: Interpretación Científica
- Correlación correcta identidad → confianza
- Análisis taxonómico coherente
- Recomendaciones contextualmente apropiadas

## 📈 Métricas y KPIs

### Performance
- Response time P95 ≤ 2000ms
- Concurrent request handling
- Resource utilization patterns

### Científicas
- Coherencia en interpretaciones
- Precisión de recomendaciones
- Calidad de metadatos generados

### Operacionales
- Uptime durante testing
- Error rate bajo estrés
- Recovery time after failures

## 🤝 Integración con CI/CD

Los tests están diseñados para integrarse con pipelines:

```bash
# En pipeline CI/CD
cd /app/emergent_tests
python3 scripts/emergent_test_executor.py --config ci_config.yaml
```

## 🐛 Troubleshooting

### Backend No Responde
```bash
# Verificar status
curl http://localhost:8001/api/health/

# Verificar logs
tail -f /var/log/supervisor/backend.*.log
```

### Tests Fallan por Timeout
- Aumentar `timeout` en configuración
- Verificar carga del sistema
- Revisar conectividad de red

### Resultados Inconsistentes
- Ejecutar suite individual para aislar problema
- Verificar estado de servicios externos
- Revisar logs detallados en reportes

## 🔮 Próximas Fases

Esta suite está preparada para **Fase 2: Descomposición Atómica**:
- Tests de herramientas completamente independientes
- Validación de DriverIA autónomo
- Protocolos dinámicos generados por IA
- Auto-fine-tuning validation

---

**🧬 Astroflora Emergent Testing Suite - Validando el Futuro de la Investigación Científica Autónoma**