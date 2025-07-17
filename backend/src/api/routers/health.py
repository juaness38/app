# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - ROUTER DE SALUD
LUIS: Endpoints para verificación de salud del sistema.
"""
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from prometheus_client import generate_latest, REGISTRY
from src.api.dependencies import get_container
from src.container import AppContainer

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get(
    "/",
    summary="Health Check",
    description="Verificación básica de salud del sistema"
)
async def health_check(
    container: AppContainer = Depends(get_container)
) -> dict:
    """LUIS: Health check básico del sistema."""
    try:
        # Verifica salud del contenedor
        health_status = await container.health_check()
        
        # Determina estado general
        overall_healthy = True
        if health_status.get("container") != "healthy":
            overall_healthy = False
        
        services = health_status.get("services", {})
        for service_name, service_status in services.items():
            if isinstance(service_status, str) and "unhealthy" in service_status:
                overall_healthy = False
            elif isinstance(service_status, dict) and service_status.get("orchestrator") != "healthy":
                overall_healthy = False
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "version": container.settings.PROJECT_VERSION,
            "environment": container.settings.ENVIRONMENT,
            "components": health_status
        }
        
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@router.get(
    "/detailed",
    summary="Detailed Health Check",
    description="Verificación detallada de salud con información del sistema"
)
async def detailed_health_check(
    container: AppContainer = Depends(get_container)
) -> dict:
    """LUIS: Health check detallado del sistema."""
    try:
        # Salud básica
        health_status = await container.health_check()
        
        # Información del sistema
        system_info = await container.get_system_info()
        
        return {
            "health": health_status,
            "system_info": system_info,
            "timestamp": "2024-01-01T00:00:00Z"  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error en detailed health check: {e}")
        return {
            "health": {"status": "unhealthy", "error": str(e)},
            "system_info": {"error": str(e)}
        }

@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Expone métricas en formato Prometheus"
)
async def get_metrics() -> Response:
    """LUIS: Expone las métricas de Prometheus."""
    try:
        metrics_data = generate_latest(REGISTRY)
        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Error generando métricas: {e}")
        return Response(
            content=f"# Error generating metrics: {e}",
            media_type="text/plain"
        )

@router.get(
    "/capacity",
    summary="System Capacity",
    description="Información sobre la capacidad actual del sistema"
)
async def get_system_capacity(
    container: AppContainer = Depends(get_container)
) -> dict:
    """LUIS: Información de capacidad del sistema."""
    try:
        capacity_info = await container.capacity_manager.get_current_capacity()
        
        return {
            "capacity": capacity_info,
            "timestamp": "2024-01-01T00:00:00Z"  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo capacidad: {e}")
        return {
            "error": str(e)
        }

@router.get(
    "/queue",
    summary="Queue Status",
    description="Estado actual de la cola de procesamiento"
)
async def get_queue_status(
    container: AppContainer = Depends(get_container)
) -> dict:
    """LUIS: Estado de la cola de procesamiento."""
    try:
        queue_status = await container.sqs_dispatcher.get_queue_status()
        
        return {
            "queue": queue_status,
            "timestamp": "2024-01-01T00:00:00Z"  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de cola: {e}")
        return {
            "error": str(e)
        }

@router.post(
    "/maintenance/cleanup",
    summary="Cleanup Resources",
    description="Limpia recursos antiguos del sistema"
)
async def cleanup_resources(
    container: AppContainer = Depends(get_container)
) -> dict:
    """LUIS: Limpia recursos antiguos."""
    try:
        await container.cleanup_resources()
        
        return {
            "message": "Recursos limpiados exitosamente",
            "timestamp": "2024-01-01T00:00:00Z"  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error limpiando recursos: {e}")
        return {
            "error": str(e)
        }

@router.post(
    "/maintenance/reset-capacity",
    summary="Reset Capacity",
    description="Reinicia los contadores de capacidad"
)
async def reset_capacity(
    container: AppContainer = Depends(get_container)
) -> dict:
    """LUIS: Reinicia la capacidad del sistema."""
    try:
        await container.capacity_manager.reset_capacity()
        
        return {
            "message": "Capacidad reiniciada exitosamente",
            "timestamp": "2024-01-01T00:00:00Z"  # Placeholder
        }
        
    except Exception as e:
        logger.error(f"Error reiniciando capacidad: {e}")
        return {
            "error": str(e)
        }