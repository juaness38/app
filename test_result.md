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


user_problem_statement: "Migración exitosa del backend mejorado de app2-main a app. El backend de Antares ha sido actualizado con todas las mejoras y optimizaciones de la versión 5.0.0, incluyendo configuración avanzada, mejor manejo de excepciones, y arquitectura más robusta."

backend:
  - task: "Migración del backend mejorado"
    implemented: true
    working: true
    file: "backend/ (completo reemplazado desde app2-main/app-main/backend/)"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Backend completamente migrado desde app2-main/app-main/backend/. Incluye versión 5.0.0 con configuración avanzada, servicios de IA mejorados, y arquitectura más robusta"

  - task: "Configuración de Astroflora Antares 5.0.0"
    implemented: true
    working: true
    file: "backend/.env, backend/src/config/settings.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Configuración completa con variables de entorno para OpenAI, Gemini, Anthropic, Redis, SQS, servicios bioinformáticos y parámetros de resiliencia"

  - task: "Arquitectura base de Antares actualizada"
    implemented: true
    working: true
    file: "backend/src/config/settings.py, backend/src/container.py, backend/src/main.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Arquitectura migrada exitosamente con contenedor de dependencias mejorado, ciclo de vida robusto y manejo avanzado de excepciones"

  - task: "Modelos de datos y excepciones actualizados"
    implemented: true
    working: true
    file: "backend/src/models/analysis.py, backend/src/core/exceptions.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Modelos Pydantic migrados con excepción PipelineException agregada para compatibilidad completa"

  - task: "Servicios mejorados de ejecución y IA"
    implemented: true
    working: true
    file: "backend/src/services/"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Todos los servicios migrados: IA, bioinformáticos, resiliencia, ejecución, observabilidad con mejoras de la versión 5.0.0"

  - task: "API endpoints actualizados"
    implemented: true
    working: true
    file: "backend/src/api/routers/"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "API completa migrada con autenticación por API key mejorada y endpoints de análisis, salud y herramientas funcionando"

frontend:
  - task: "Interfaz de usuario Antares"
    implemented: true
    working: true
    file: "src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Interfaz React completa con formularios para análisis, visualización de herramientas y análisis recientes"

  - task: "Integración con backend"
    implemented: true
    working: true
    file: "src/App.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: "Integración completa con API backend, manejo de autenticación y estados de análisis"

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus:
    - "Arquitectura completa de Antares implementada"
    - "Driver IA funcionando con simulación"
    - "Herramientas bioinformáticas integradas"
    - "Frontend funcional con análisis en tiempo real"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Arquitectura completa de Antares implementada exitosamente. Sistema incluye: Driver IA con OpenAI, Orchestrator inteligente, Analysis Worker, Tool Gateway con 13 herramientas bioinformáticas (BLAST, AlphaFold, MAFFT, etc.), servicios de resiliencia con Circuit Breakers, métricas Prometheus, Context Manager, Event Store, y API completa. Frontend React funcional permite iniciar análisis de diferentes tipos de protocolos científicos. Sistema está funcionando en modo simulado listo para integración con claves API reales."