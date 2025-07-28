# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - ROUTER DE ANÁLISIS MEJORADO
LUIS: API mejorada con WebSockets, búsqueda avanzada y plantillas.
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.dependencies import get_container, verify_api_key
from src.container import AppContainer
from src.models.analysis import (
    AnalysisRequest, AnalysisContext, AnalysisQuery, 
    PromptProtocolType, AnalysisTemplate, APIResponse,
    ANALYSIS_TEMPLATES
)
from src.core.exceptions import AstrofloraException

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

class ConnectionManager:
    """LUIS: Gestor de conexiones WebSocket para updates en tiempo real."""
    
    def __init__(self):
        self.active_connections: dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, context_id: str):
        await websocket.accept()
        if context_id not in self.active_connections:
            self.active_connections[context_id] = []
        self.active_connections[context_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, context_id: str):
        if context_id in self.active_connections:
            self.active_connections[context_id].remove(websocket)
            if not self.active_connections[context_id]:
                del self.active_connections[context_id]
    
    async def send_update(self, context_id: str, data: dict):
        if context_id in self.active_connections:
            for websocket in self.active_connections[context_id]:
                try:
                    await websocket.send_json(data)
                except:
                    # Conexión cerrada, se limpiará automáticamente
                    pass

# Gestor global de conexiones
connection_manager = ConnectionManager()

# === ENDPOINTS BÁSICOS ===

@router.get("/", response_model=List[AnalysisContext])
async def get_analyses(
    container: AppContainer = Depends(get_container),
    _: str = Depends(verify_api_key),
    limit: int = 20,
    offset: int = 0
):
    """LUIS: Obtiene lista de análisis con paginación."""
    try:
        analyses = await container.context_manager.get_recent_analyses(limit, offset)
        return analyses
    except Exception as e:
        logger.error(f"Error getting analyses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving analyses: {str(e)}"
        )

@router.post("/start", response_model=AnalysisContext)
@limiter.limit("10/minute")  # 10 análisis por minuto por IP
async def start_analysis(
    request: Request,
    analysis_request: AnalysisRequest,
    container: AppContainer = Depends(get_container),
    _: str = Depends(verify_api_key)
):
    """LUIS: Inicia un nuevo análisis con rate limiting."""
    try:
        # Verifica capacidad disponible
        if not await container.capacity_manager.can_process_request():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="System at maximum capacity. Please try again later."
            )
        
        # Reserva capacidad
        await container.capacity_manager.reserve_capacity(analysis_request.context_id)
        
        # Crea contexto inicial
        context = AnalysisContext(
            context_id=analysis_request.context_id,
            user_id=analysis_request.user_id,
            workspace_id=analysis_request.workspace_id,
            protocol_type=analysis_request.protocol_type,
            sequence_data=analysis_request.sequence_data,
            parameters=analysis_request.parameters
        )
        
        # Guarda contexto
        await container.context_manager.create_context(context)
        
        # Despacha para procesamiento
        await container.sqs_dispatcher.dispatch_job({
            "context_id": analysis_request.context_id,
            "action": "start_analysis"
        })
        
        return context
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting analysis: {str(e)}"
        )

@router.get("/{context_id}", response_model=AnalysisContext)
async def get_analysis_status(
    context_id: str,
    container: AppContainer = Depends(get_container),
    _: str = Depends(verify_api_key)
):
    """LUIS: Obtiene el estado actual de un análisis."""
    try:
        context = await container.context_manager.get_context(context_id)
        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis {context_id} not found"
            )
        return context
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving analysis: {str(e)}"
        )

# === ENDPOINTS AVANZADOS ===

@router.get("/search", response_model=List[AnalysisContext])
async def search_analyses(
    query: AnalysisQuery = Depends(),
    container: AppContainer = Depends(get_container),
    _: str = Depends(verify_api_key)
):
    """LUIS: Búsqueda avanzada de análisis con filtros."""
    try:
        analyses = await container.context_manager.search_analyses(query)
        return analyses
    except Exception as e:
        logger.error(f"Error searching analyses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching analyses: {str(e)}"
        )

@router.get("/templates", response_model=List[AnalysisTemplate])
async def get_analysis_templates(
    _: str = Depends(verify_api_key)
):
    """LUIS: Obtiene plantillas predefinidas para análisis comunes."""
    return list(ANALYSIS_TEMPLATES.values())

@router.get("/templates/{template_id}", response_model=AnalysisTemplate)
async def get_analysis_template(
    template_id: str,
    _: str = Depends(verify_api_key)
):
    """LUIS: Obtiene una plantilla específica."""
    if template_id not in ANALYSIS_TEMPLATES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )
    return ANALYSIS_TEMPLATES[template_id]

@router.post("/from-template/{template_id}", response_model=AnalysisContext)
async def start_analysis_from_template(
    template_id: str,
    user_id: str,
    workspace_id: str,
    parameters: Optional[dict] = None,
    container: AppContainer = Depends(get_container),
    _: str = Depends(verify_api_key)
):
    """LUIS: Inicia análisis desde una plantilla."""
    try:
        if template_id not in ANALYSIS_TEMPLATES:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {template_id} not found"
            )
        
        template = ANALYSIS_TEMPLATES[template_id]
        
        # Combina parámetros de plantilla con los proporcionados
        final_parameters = template.default_parameters.copy()
        if parameters:
            final_parameters.update(parameters)
        
        # Crea request desde plantilla
        analysis_request = AnalysisRequest(
            user_id=user_id,
            workspace_id=workspace_id,
            protocol_type=template.protocol_type,
            parameters=final_parameters
        )
        
        # Usa la lógica de inicio estándar
        return await start_analysis(None, analysis_request, container, _)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting analysis from template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting analysis from template: {str(e)}"
        )

# === WEBSOCKET PARA REAL-TIME UPDATES ===

@router.websocket("/ws/{context_id}")
async def websocket_endpoint(websocket: WebSocket, context_id: str):
    """LUIS: WebSocket para updates en tiempo real del progreso de análisis."""
    await connection_manager.connect(websocket, context_id)
    try:
        # Obtiene container (simplificado para WebSocket)
        from src.api.dependencies import get_container_sync
        container = get_container_sync()
        
        while True:
            try:
                # Envía update del progreso cada 2 segundos
                context = await container.context_manager.get_context(context_id)
                if context:
                    await websocket.send_json({
                        "context_id": context_id,
                        "status": context.status,
                        "progress": context.progress,
                        "current_step": context.current_step,
                        "timestamp": context.updated_at.isoformat() if context.updated_at else None
                    })
                
                await asyncio.sleep(2)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error for context {context_id}: {e}")
                await websocket.send_json({
                    "error": f"Error getting status: {str(e)}"
                })
                
    except WebSocketDisconnect:
        pass
    finally:
        connection_manager.disconnect(websocket, context_id)

# === ENDPOINTS DE HERRAMIENTAS Y PROTOCOLOS ===

@router.get("/tools/available")
async def get_available_tools(
    container: AppContainer = Depends(get_container),
    _: str = Depends(verify_api_key)
):
    """LUIS: Lista herramientas bioinformáticas disponibles."""
    try:
        tools = await container.tool_gateway.list_available_tools()
        return tools
    except Exception as e:
        logger.error(f"Error getting available tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tools: {str(e)}"
        )

@router.get("/protocols/types")
async def get_protocol_types(
    _: str = Depends(verify_api_key)
):
    """LUIS: Lista tipos de protocolos disponibles."""
    return [protocol_type.value for protocol_type in PromptProtocolType]

@router.delete("/{context_id}")
async def cancel_analysis(
    context_id: str,
    container: AppContainer = Depends(get_container),
    _: str = Depends(verify_api_key)
):
    """LUIS: Cancela un análisis en curso."""
    try:
        context = await container.context_manager.get_context(context_id)
        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis {context_id} not found"
            )
        
        # Actualiza estado a cancelado
        await container.context_manager.update_context(
            context_id,
            {
                "status": "cancelled",
                "completed_at": datetime.utcnow()
            }
        )
        
        # Libera capacidad
        await container.capacity_manager.release_capacity(context_id)
        
        return {"message": f"Analysis {context_id} cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling analysis: {str(e)}"
        )