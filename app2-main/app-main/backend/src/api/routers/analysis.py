# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - ROUTER DE ANÁLISIS
LUIS: Endpoints para gestión de análisis científicos.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from src.api.dependencies import get_container, get_current_user
from src.models.analysis import AnalysisRequest, AnalysisContext, PromptProtocolType
from src.services.interfaces import IOrchestrator
from src.container import AppContainer

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    "/", 
    status_code=status.HTTP_202_ACCEPTED, 
    response_model=AnalysisContext,
    summary="Iniciar Análisis",
    description="Inicia un nuevo análisis científico usando el Driver IA"
)
async def start_analysis(
    request: AnalysisRequest,
    current_user: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container)
) -> AnalysisContext:
    """LUIS: Endpoint para iniciar un nuevo análisis."""
    try:
        logger.info(f"Iniciando análisis {request.protocol_type} para usuario {current_user}")
        
        # Obtiene el orquestador del contenedor
        orchestrator = container.orchestrator
        
        # Inicia el análisis
        context = await orchestrator.start_new_analysis(request, current_user)
        
        logger.info(f"Análisis iniciado exitosamente: {context.context_id}")
        return context
        
    except Exception as e:
        logger.error(f"Error iniciando análisis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando análisis: {str(e)}"
        )

@router.get(
    "/{context_id}",
    response_model=AnalysisContext,
    summary="Obtener Estado del Análisis",
    description="Obtiene el estado actual de un análisis por su ID"
)
async def get_analysis_status(
    context_id: str,
    current_user: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container)
) -> AnalysisContext:
    """LUIS: Endpoint para obtener el estado de un análisis."""
    try:
        orchestrator = container.orchestrator
        
        context = await orchestrator.get_analysis_status(context_id)
        
        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Análisis no encontrado: {context_id}"
            )
        
        return context
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estado del análisis {context_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estado del análisis: {str(e)}"
        )

@router.delete(
    "/{context_id}",
    summary="Cancelar Análisis",
    description="Cancela un análisis en curso"
)
async def cancel_analysis(
    context_id: str,
    current_user: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container)
) -> dict:
    """LUIS: Endpoint para cancelar un análisis."""
    try:
        orchestrator = container.orchestrator
        
        success = await orchestrator.cancel_analysis(context_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No se pudo cancelar el análisis: {context_id}"
            )
        
        return {"message": f"Análisis cancelado exitosamente: {context_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelando análisis {context_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelando análisis: {str(e)}"
        )

@router.get(
    "/user/{user_id}",
    response_model=List[AnalysisContext],
    summary="Obtener Análisis del Usuario",
    description="Obtiene todos los análisis de un usuario específico"
)
async def get_user_analyses(
    user_id: str,
    limit: int = 50,
    current_user: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container)
) -> List[AnalysisContext]:
    """LUIS: Endpoint para obtener análisis de un usuario."""
    try:
        orchestrator = container.orchestrator
        
        analyses = await orchestrator.get_user_analyses(user_id, limit)
        
        return analyses
        
    except Exception as e:
        logger.error(f"Error obteniendo análisis del usuario {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo análisis del usuario: {str(e)}"
        )

@router.get(
    "/",
    response_model=List[AnalysisContext],
    summary="Obtener Mis Análisis",
    description="Obtiene todos los análisis del usuario actual"
)
async def get_my_analyses(
    limit: int = 50,
    current_user: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container)
) -> List[AnalysisContext]:
    """LUIS: Endpoint para obtener análisis del usuario actual."""
    try:
        orchestrator = container.orchestrator
        
        analyses = await orchestrator.get_user_analyses(current_user, limit)
        
        return analyses
        
    except Exception as e:
        logger.error(f"Error obteniendo análisis del usuario actual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo análisis: {str(e)}"
        )

@router.get(
    "/protocols/types",
    response_model=List[str],
    summary="Obtener Tipos de Protocolo",
    description="Obtiene todos los tipos de protocolo disponibles"
)
async def get_protocol_types(
    current_user: str = Depends(get_current_user)
) -> List[str]:
    """LUIS: Endpoint para obtener tipos de protocolo disponibles."""
    try:
        return [protocol.value for protocol in PromptProtocolType]
        
    except Exception as e:
        logger.error(f"Error obteniendo tipos de protocolo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo tipos de protocolo: {str(e)}"
        )

@router.get(
    "/tools/available",
    response_model=List[str],
    summary="Obtener Herramientas Disponibles",
    description="Obtiene todas las herramientas bioinformáticas disponibles"
)
async def get_available_tools(
    current_user: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container)
) -> List[str]:
    """LUIS: Endpoint para obtener herramientas disponibles."""
    try:
        tool_gateway = container.tool_gateway
        
        tools = await tool_gateway.get_available_tools()
        
        return tools
        
    except Exception as e:
        logger.error(f"Error obteniendo herramientas disponibles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo herramientas: {str(e)}"
        )

@router.get(
    "/tools/{tool_name}/health",
    summary="Verificar Salud de Herramienta",
    description="Verifica si una herramienta específica está disponible"
)
async def check_tool_health(
    tool_name: str,
    current_user: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container)
) -> dict:
    """LUIS: Endpoint para verificar salud de herramienta."""
    try:
        tool_gateway = container.tool_gateway
        
        is_healthy = await tool_gateway.health_check_tool(tool_name)
        
        return {
            "tool_name": tool_name,
            "healthy": is_healthy,
            "status": "available" if is_healthy else "unavailable"
        }
        
    except Exception as e:
        logger.error(f"Error verificando salud de herramienta {tool_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verificando herramienta: {str(e)}"
        )

@router.post(
    "/batch",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=List[AnalysisContext],
    summary="Iniciar Análisis por Lotes",
    description="Inicia múltiples análisis simultáneamente"
)
async def start_batch_analysis(
    requests: List[AnalysisRequest],
    current_user: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container)
) -> List[AnalysisContext]:
    """LUIS: Endpoint para iniciar análisis por lotes."""
    try:
        if len(requests) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Máximo 10 análisis por lote"
            )
        
        orchestrator = container.orchestrator
        contexts = []
        
        for request in requests:
            context = await orchestrator.start_new_analysis(request, current_user)
            contexts.append(context)
        
        logger.info(f"Análisis por lotes iniciado: {len(contexts)} análisis")
        return contexts
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error iniciando análisis por lotes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando análisis por lotes: {str(e)}"
        )