# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - PUNTO DE ENTRADA PRINCIPAL MEJORADO
LUIS: Aplicación con ciclo de vida completo, middleware avanzado y monitoreo.
"""
import logging
import asyncio
import uuid
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.config.settings import settings
from src.container import AppContainer
from src.api.dependencies import set_container
from src.api.routers import analysis, health
from src.models.analysis import APIResponse
from src.core.exceptions import (
    AstrofloraException, ServiceUnavailableException, 
    AnalysisNotFoundException, DriverIAException,
    ToolGatewayException, CircuitBreakerOpenException,
    CapacityExceededException
)

def setup_logging() -> None:
    """LUIS: Configura el sistema de logging mejorado."""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Silencia logs ruidosos
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """LUIS: Ciclo de vida mejorado de la aplicación."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info(f"🚀 Iniciando {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    logger.info(f"Entorno: {settings.ENVIRONMENT}")
    
    try:
        # Inicializa el contenedor
        container = AppContainer(settings)
        set_container(container)
        app.state.container = container
        
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
            if hasattr(app.state, 'container'):
                await app.state.container.shutdown()
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
    - **Rate Limiting**: Control de tasa por IP y endpoint
    - **Cost Tracking**: Seguimiento de costos de IA
    
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

# Configura rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === MIDDLEWARE AVANZADO ===

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """LUIS: Middleware para tracing de requests."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """LUIS: Middleware mejorado para logging de requests."""
    logger = logging.getLogger(__name__)
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    start_time = time.time()
    
    # Log request
    logger.info(
        f"[{request_id}] {request.method} {request.url.path} - "
        f"IP: {request.client.host if request.client else 'unknown'}"
    )
    
    # Procesa request
    try:
        response = await call_next(request)
        
        # Calcula tiempo de procesamiento
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"ERROR: {str(e)} - Time: {process_time:.3f}s"
        )
        raise

# === MANEJADORES DE EXCEPCIONES MEJORADOS ===

@app.exception_handler(AstrofloraException)
async def handle_astroflora_exceptions(request: Request, exc: AstrofloraException):
    """LUIS: Maneja excepciones específicas de Astroflora con respuesta estructurada."""
    logger = logging.getLogger(__name__)
    request_id = getattr(request.state, 'request_id', None)
    logger.error(f"[{request_id}] Excepción Astroflora: {exc}")
    
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
        content=APIResponse(
            success=False,
            error=f"{exc.__class__.__name__}: {str(exc)}",
            request_id=request_id
        ).dict()
    )

@app.exception_handler(HTTPException)
async def handle_http_exceptions(request: Request, exc: HTTPException):
    """LUIS: Maneja excepciones HTTP estándar."""
    request_id = getattr(request.state, 'request_id', None)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            success=False,
            error=exc.detail,
            request_id=request_id
        ).dict()
    )

@app.exception_handler(Exception)
async def handle_general_exceptions(request: Request, exc: Exception):
    """LUIS: Maneja excepciones generales con logging."""
    logger = logging.getLogger(__name__)
    request_id = getattr(request.state, 'request_id', None)
    logger.error(f"[{request_id}] Excepción no manejada: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIResponse(
            success=False,
            error="Error interno del servidor" if settings.is_production() else str(exc),
            request_id=request_id
        ).dict()
    )

# === REGISTRA RUTAS ===
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

# === ENDPOINTS PRINCIPALES ===

@app.get("/", tags=["🚀 General"])
@limiter.limit(f"{settings.RATE_LIMIT_REQUESTS_PER_MINUTE}/minute")
async def root(request: Request):
    """LUIS: Endpoint raíz con información del sistema."""
    request_id = getattr(request.state, 'request_id', None)
    
    return APIResponse(
        success=True,
        data={
            "message": "🧬 Astroflora Antares Core - Sistema Cognitivo Activo",
            "version": settings.PROJECT_VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": "/docs",
            "health": "/api/health",
            "metrics": "/api/health/metrics",
            "features": [
                "Rate Limited API",
                "Request Tracing",
                "Cost Tracking",
                "Advanced Monitoring"
            ]
        },
        request_id=request_id
    )

@app.get("/info", tags=["🚀 General"])
async def info(request: Request):
    """LUIS: Información detallada del sistema."""
    request_id = getattr(request.state, 'request_id', None)
    
    return APIResponse(
        success=True,
        data={
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
                "Gestión de Capacidad",
                "Rate Limiting Inteligente",
                "Cost Tracking Avanzado",
                "Request Tracing"
            ],
            "endpoints": {
                "analysis": "/api/analysis",
                "health": "/api/health",
                "metrics": "/api/health/metrics"
            },
            "limits": {
                "requests_per_minute": settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
                "analysis_per_minute": settings.RATE_LIMIT_ANALYSIS_PER_MINUTE,
                "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS
            }
        },
        request_id=request_id
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True if settings.ENVIRONMENT == "dev" else False,
        log_level=settings.LOG_LEVEL.lower()
    )