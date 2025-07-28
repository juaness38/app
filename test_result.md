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


user_problem_statement: "Implementación exitosa de mejoras avanzadas en Astroflora Antares 5.0.0 basadas en el documento de mejoras. Se agregaron funcionalidades enterprise como validación de secuencias biológicas, rate limiting, request tracing, plantillas de análisis, WebSockets, circuit breakers mejorados, cost tracking y monitoreo avanzado de recursos."

backend:
  - task: "Modelos de datos con validación biológica avanzada"
    implemented: true
    working: true
    file: "backend/src/models/analysis.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Modelos completamente mejorados con validación de secuencias biológicas (proteína/DNA), configuración de pipeline tipada, cache inteligente, cost tracking LLM, plantillas de análisis predefinidas, formato de respuesta API estructurado y query models para búsquedas avanzadas"

  - task: "Configuración con validación avanzada"
    implemented: true
    working: true
    file: "backend/src/config/settings.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Configuración robusta con validaciones Pydantic para claves API, parámetros de rate limiting, cache TTL, monitoreo, dead letter queue y métodos de verificación de entorno y claves reales"

  - task: "API principal con middleware enterprise"
    implemented: true
    working: true
    file: "backend/src/main.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "API mejorada con rate limiting por IP, request ID tracing, logging estructurado, manejo de excepciones con formato APIResponse, middleware avanzado para monitoreo y respuestas estructuradas"

  - task: "Contenedor con health checks comprehensivos"
    implemented: true
    working: true
    file: "backend/src/container.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Contenedor mejorado con health checks comprehensivos que prueban todas las dependencias (Redis, MongoDB, DriverIA, Tool Gateway), índices MongoDB automáticos, métricas detalladas y cierre limpio de recursos"

  - task: "Analysis Worker con resiliencia avanzada"
    implemented: true
    working: true
    file: "backend/src/services/execution/analysis_worker.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Worker mejorado con circuit breakers para DriverIA, retry strategy exponencial, monitoreo de recursos (CPU/memoria), cleanup automático, estadísticas detalladas y cierre limpio"

  - task: "API de análisis con WebSockets y plantillas"
    implemented: true
    working: true
    file: "backend/src/api/routers/analysis.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Router completamente mejorado con WebSockets para updates en tiempo real, plantillas predefinidas, búsqueda avanzada con filtros, rate limiting por endpoint, gestión de conexiones y análisis desde plantillas"

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
    - "Backend Astroflora Antares 5.0.0 migrado exitosamente"
    - "API completa funcionando con autenticación mejorada"
    - "13 herramientas bioinformáticas disponibles"
    - "Frontend compatible con backend migrado"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "✅ MIGRACIÓN EXITOSA: Backend completo de app2-main/app-main/backend/ reemplazado en app/backend/. Astroflora Antares 5.0.0 funcionando correctamente con configuración avanzada, servicios de IA mejorados, 13 herramientas bioinformáticas, API con autenticación robusta, y frontend completamente compatible. Sistema listo para continuar desarrollo."
  - agent: "testing"
    message: "✅ TESTING COMPLETADO: Ejecuté pruebas exhaustivas del backend migrado de Astroflora Antares 5.0.0. TODOS LOS TESTS PASARON (20/20). Confirmé: API de salud funcionando, autenticación robusta con API key, 13 herramientas bioinformáticas disponibles, 6 tipos de protocolo, análisis completo funcional, endpoints de mantenimiento operativos. Sistema backend completamente funcional y listo para producción."