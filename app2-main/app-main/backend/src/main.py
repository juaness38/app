# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - PUNTO DE ENTRADA PRINCIPAL
LUIS: Aplicación principal con ciclo de vida completo.
"""
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings
from src.container import AppContainer
from src.api.dependencies import set_container
from src.api.routers import analysis, health
from src.core.exceptions import (
    AstrofloraException, ServiceUnavailableException, 
    AnalysisNotFoundException, DriverIAException,
    ToolGatewayException, CircuitBreakerOpenException,
    CapacityExceededException
)

def setup_logging() -> None:
    """LUIS: Configura el sistema de logging."""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Silencia logs ruidosos
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """LUIS: Ciclo de vida de la aplicación."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info(f"🚀 Iniciando {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    logger.info(f"Entorno: {settings.ENVIRONMENT}")
    
    try:
        # Inicializa el contenedor
        container = AppContainer(settings)
        set_container(container)
        
        # Inicializa recursos
        await container.initialize_resources()
        
        logger.info("✅ Astroflora Antares iniciado exitosamente")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Error iniciando aplicación: {e}")
        raise
    finally:
        logger.info("🔄 Apagando Astroflora Antares...")
        
        try:
            # Limpia recursos
            await container.shutdown()
            logger.info("✅ Astroflora Antares apagado exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error apagando aplicación: {e}")

# Crea la aplicación FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="""
    🧬 **Astroflora Antares Core** - Sistema Cognitivo para Investigación Científica Autónoma
    
    Antares es el cerebro cognitivo de Astroflora que orquesta investigación científica de forma autónoma.
    
    ## Características Principales
    
    - **Driver IA**: Científico cognitivo que ejecuta Prompt Protocols
    - **Orquestador Inteligente**: Gestiona flujos de análisis complejos
    - **Herramientas Bioinformáticas**: BLAST, AlphaFold, MAFFT, MUSCLE y más
    - **Resiliencia**: Circuit Breakers y gestión de capacidad
    - **Observabilidad**: Métricas en tiempo real y auditoría completa
    
    ## Tipos de Análisis Disponibles
    
    - **Análisis de Función de Proteína**: Determina la función de proteínas desconocidas
    - **Alineamiento de Secuencias**: Alineamiento múltiple y análisis de conservación
    - **Predicción de Estructura**: Predicción 3D con AlphaFold
    - **Diseño de Fármacos**: Docking molecular y análisis de candidatos
    - **Optimización de Bioreactores**: Optimización de condiciones de cultivo
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Manejadores de excepciones
@app.exception_handler(AstrofloraException)
async def handle_astroflora_exceptions(request: Request, exc: AstrofloraException):
    """LUIS: Maneja excepciones específicas de Astroflora."""
    logger = logging.getLogger(__name__)
    logger.error(f"Excepción Astroflora: {exc}")
    
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    if isinstance(exc, ServiceUnavailableException):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, AnalysisNotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, DriverIAException):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, ToolGatewayException):
        status_code = status.HTTP_502_BAD_GATEWAY
    elif isinstance(exc, CircuitBreakerOpenException):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, CapacityExceededException):
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": exc.__class__.__name__,
            "detail": str(exc),
            "type": "astroflora_error"
        }
    )

@app.exception_handler(HTTPException)
async def handle_http_exceptions(request: Request, exc: HTTPException):
    """LUIS: Maneja excepciones HTTP estándar."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "detail": exc.detail,
            "type": "http_error"
        }
    )

@app.exception_handler(Exception)
async def handle_general_exceptions(request: Request, exc: Exception):
    """LUIS: Maneja excepciones generales."""
    logger = logging.getLogger(__name__)
    logger.error(f"Excepción no manejada: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "detail": "Error interno del servidor",
            "type": "internal_error"
        }
    )

# Registra rutas
app.include_router(
    analysis.router,
    prefix="/api/analysis",
    tags=["🧬 Análisis Científico"]
)

app.include_router(
    health.router,
    prefix="/api/health",
    tags=["🏥 Salud del Sistema"]
)

# Ruta raíz
@app.get("/", tags=["🚀 General"])
async def root():
    """LUIS: Endpoint raíz con información del sistema."""
    return {
        "message": "🧬 Astroflora Antares Core - Sistema Cognitivo Activo",
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/api/health",
        "metrics": "/api/health/metrics"
    }

# Ruta de información
@app.get("/info", tags=["🚀 General"])
async def info():
    """LUIS: Información detallada del sistema."""
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
        "description": "Sistema Cognitivo para Investigación Científica Autónoma",
        "features": [
            "Driver IA con LLM",
            "Herramientas Bioinformáticas",
            "Orquestación Inteligente",
            "Resiliencia y Circuit Breakers",
            "Métricas y Observabilidad",
            "Gestión de Capacidad"
        ],
        "endpoints": {
            "analysis": "/api/analysis",
            "health": "/api/health",
            "metrics": "/api/health/metrics"
        }
    }

# Middleware de logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """LUIS: Middleware para logging de requests."""
    logger = logging.getLogger(__name__)
    
    start_time = asyncio.get_event_loop().time()
    
    # Procesa request
    response = await call_next(request)
    
    # Calcula tiempo de procesamiento
    process_time = asyncio.get_event_loop().time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    return response

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True if settings.ENVIRONMENT == "dev" else False,
        log_level=settings.LOG_LEVEL.lower()
    )