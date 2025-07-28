#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================


user_problem_statement: "TRANSFORMACIÓN AGÉNTICA ASTROFLORA - FASE 1: COEXISTENCIA Y ESTABILIZACIÓN. Implementación exitosa de capacidades agénticas avanzadas basadas en el diseño del primer científico artificial. Se integraron pipeline científico mejorado, herramientas atómicas, gateway agéntico, configuraciones avanzadas, plantillas predefinidas y endpoints especializados. El sistema mantiene compatibilidad total mientras se prepara para la descomposición atómica completa."

backend:
  - task: "Pipeline Científico Agéntico Mejorado"
    implemented: true
    working: true
    file: "backend/src/core/pipeline.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "EnhancedScientificPipeline implementado con configuración agéntica mejorada, validación biológica avanzada, caching configurable, templates de profundidad variable, métricas científicas y compatibilidad total con interfaz existente. Preparado para descomposición atómica."

  - task: "Modelos Agénticos Avanzados"
    implemented: true
    working: true
    file: "backend/src/models/analysis.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Modelos agénticos implementados: EnhancedSequenceData con validación biológica avanzada, EnhancedPipelineConfig con configuración científica completa, ToolResult para herramientas atómicas, EnhancedAnalysisTemplate con plantillas predefinidas y metadatos científicos completos"

  - task: "Herramientas Atómicas Científicas"
    implemented: true
    working: true
    file: "backend/src/services/agentic/atomic_tools.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "4 herramientas atómicas implementadas: BlastSearchTool (búsqueda homología), UniProtAnnotationTool (anotaciones funcionales), SequenceFeaturesTool (características computacionales), LLMAnalysisTool (análisis con IA). Cada herramienta con metadatos científicos, evaluación de aplicabilidad y métricas de rendimiento"

  - task: "Gateway Agéntico con MCP"
    implemented: true
    working: true
    file: "backend/src/services/agentic/agentic_gateway.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "AgenticToolGateway implementado con capacidades MCP, recomendación de herramientas basada en contexto, evaluación de aplicabilidad, métricas comprehensivas, health checks individuales y compatibilidad completa con interfaz IToolGateway existente"

  - task: "Contenedor con Inyección Agéntica"
    implemented: true
    working: true
    file: "backend/src/container.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "AppContainer actualizado con inicialización de servicios agénticos: AgenticToolGateway reemplaza BioinformaticsToolGateway, EnhancedScientificPipeline con configuración agéntica, referencias circulares resueltas correctamente y health checks comprehensivos"

  - task: "API Agéntica RESTful"
    implemented: true
    working: true
    file: "backend/src/api/routers/agentic.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Router agéntico completo con 15+ endpoints especializados: gestión de herramientas atómicas, recomendación de herramientas, validación de configuraciones, plantillas predefinidas, métricas del gateway, capacidades del sistema y health checks. Totalmente integrado en /api/agentic"

  - task: "Aplicación Principal Integrada"
    implemented: true
    working: true
    file: "backend/src/main.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Aplicación principal actualizada con router agéntico registrado en /api/agentic con tags especializados. Mantiene compatibilidad total con endpoints existentes mientras expone nuevas capacidades agénticas"

frontend:
  - task: "Compatibilidad con backend migrado"
    implemented: true
    working: true
    file: "frontend/src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Frontend mantiene compatibilidad completa con el backend migrado. Funciona correctamente con la nueva API de Astroflora Antares 5.0.0"

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus:
    - "FASE 1 COMPLETADA: Coexistencia y Estabilización"
    - "Pipeline Científico Agéntico Mejorado funcionando"
    - "4 Herramientas Atómicas Científicas operativas"
    - "Gateway Agéntico con capacidades MCP"
    - "15+ Endpoints agénticos en /api/agentic"
    - "Compatibilidad total con sistema existente"
    - "Preparado para Fase 2: Descomposición Atómica"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "🚀 FASE 1 TRANSFORMACIÓN AGÉNTICA COMPLETADA: Implementación exitosa de arquitectura agéntica completa manteniendo compatibilidad total. EnhancedScientificPipeline con configuración avanzada, 4 herramientas atómicas científicas (BLAST, UniProt, SequenceFeatures, LLM), AgenticToolGateway con capacidades MCP, 15+ endpoints especializados en /api/agentic, modelos de datos mejorados y contenedor integrado. Sistema listo para Fase 2: Descomposición Atómica donde las herramientas funcionarán independientemente."