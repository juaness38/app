# -*- coding: utf-8 -*-
"""
MCP Data Server - Standardized resource and context management service
Implements resources/get_context and resources/save_event endpoints
"""
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from mcp.protocol import (
    GetContextRequest, GetContextResponse, SaveEventRequest, SaveEventResponse,
    ResourceMetadata, ResourceType, MCPError, CorrelationContext
)
from services.interfaces import IContextManager, IEventStore
from models.analysis import AnalysisContext, EventStoreEntry

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

class MCPDataServer:
    """MCP Data Server implementation for resource and context management"""
    
    def __init__(self, context_manager: IContextManager, event_store: IEventStore):
        self.context_manager = context_manager
        self.event_store = event_store
        
    async def get_analysis_context(self, context_id: str, include_history: bool = False) -> Dict[str, Any]:
        """Get analysis context with optional history"""
        context = await self.context_manager.get_context(context_id)
        if not context:
            return None
            
        context_data = {
            "context_id": context.context_id,
            "request_data": context.request_data,
            "status": context.status,
            "progress": context.progress,
            "status_message": context.status_message,
            "results": context.results,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat()
        }
        
        if include_history:
            # Get execution events for this context
            history = await self.event_store.get_events_by_context(context_id)
            context_data["execution_history"] = [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "timestamp": event.timestamp.isoformat(),
                    "agent": event.agent,
                    "data": event.data
                }
                for event in history
            ]
        
        return context_data

# Create router
router = APIRouter()

# Dependency injection
mcp_data_server: Optional[MCPDataServer] = None

def get_mcp_data_server() -> MCPDataServer:
    """Get MCP Data Server instance"""
    if mcp_data_server is None:
        raise HTTPException(status_code=500, detail="MCP Data Server not initialized")
    return mcp_data_server

def initialize_mcp_data_server(context_manager: IContextManager, event_store: IEventStore):
    """Initialize the MCP Data Server"""
    global mcp_data_server
    mcp_data_server = MCPDataServer(context_manager, event_store)

@router.post("/get_context", response_model=GetContextResponse, summary="Get Analysis Context")
async def get_context(
    request: GetContextRequest,
    server: MCPDataServer = Depends(get_mcp_data_server)
) -> GetContextResponse:
    """
    Retrieve analysis context with optional execution history.
    Implements standardized MCP resources/get_context endpoint.
    """
    with tracer.start_as_current_span("mcp_data_get_context") as span:
        span.set_attribute("correlation_id", request.correlation_context.correlation_id)
        span.set_attribute("context_id", request.context_id)
        span.set_attribute("include_history", request.include_history)
        
        try:
            logger.info(f"[{request.correlation_context.correlation_id}] Getting context: {request.context_id}")
            
            context_data = await server.get_analysis_context(request.context_id, request.include_history)
            
            if context_data is None:
                span.set_status(Status(StatusCode.ERROR, "Context not found"))
                return GetContextResponse(
                    success=False,
                    correlation_context=request.correlation_context
                )
            
            # Create resource metadata
            metadata = ResourceMetadata(
                resource_id=request.context_id,
                resource_type=ResourceType.ANALYSIS_CONTEXT,
                created_at=datetime.fromisoformat(context_data["created_at"]),
                updated_at=datetime.fromisoformat(context_data["updated_at"]),
                version=1,  # Could be enhanced with actual versioning
                tags=["analysis", "context"],
                size_bytes=len(str(context_data).encode('utf-8'))
            )
            
            # Get execution history if requested
            history = None
            if request.include_history and "execution_history" in context_data:
                history = context_data.pop("execution_history")
            
            # Log access event
            await server.event_store.store_event(EventStoreEntry(
                context_id=request.correlation_context.correlation_id,
                event_type="context_accessed",
                data={
                    "accessed_context_id": request.context_id,
                    "include_history": request.include_history,
                    "data_size_bytes": metadata.size_bytes
                },
                agent="mcp_data_server"
            ))
            
            span.set_status(Status(StatusCode.OK))
            
            return GetContextResponse(
                success=True,
                context_data=context_data,
                metadata=metadata,
                history=history,
                correlation_context=request.correlation_context
            )
            
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(f"[{request.correlation_context.correlation_id}] Error getting context: {e}")
            
            return GetContextResponse(
                success=False,
                correlation_context=request.correlation_context
            )

@router.post("/save_event", response_model=SaveEventResponse, summary="Save Event")
async def save_event(
    request: SaveEventRequest,
    server: MCPDataServer = Depends(get_mcp_data_server)
) -> SaveEventResponse:
    """
    Save an event to the event store with correlation tracing.
    Implements standardized MCP resources/save_event endpoint.
    """
    with tracer.start_as_current_span("mcp_data_save_event") as span:
        span.set_attribute("correlation_id", request.correlation_context.correlation_id)
        span.set_attribute("event_type", request.event_type)
        span.set_attribute("agent", request.agent)
        
        try:
            logger.info(f"[{request.correlation_context.correlation_id}] Saving event: {request.event_type}")
            
            # Create event store entry
            event_entry = EventStoreEntry(
                context_id=request.correlation_context.correlation_id,
                event_type=request.event_type,
                data=request.event_data,
                timestamp=request.timestamp,
                agent=request.agent
            )
            
            # Store the event
            await server.event_store.store_event(event_entry)
            
            event_id = str(uuid.uuid4())  # Generate unique event ID
            
            span.set_status(Status(StatusCode.OK))
            
            return SaveEventResponse(
                success=True,
                event_id=event_id,
                correlation_context=request.correlation_context
            )
            
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(f"[{request.correlation_context.correlation_id}] Error saving event: {e}")
            
            return SaveEventResponse(
                success=False,
                event_id="",
                correlation_context=request.correlation_context
            )

@router.get("/resources/types", summary="List Resource Types")
async def list_resource_types():
    """List all available resource types"""
    return {
        "resource_types": [
            {
                "type": ResourceType.ANALYSIS_CONTEXT,
                "description": "Analysis execution context and state"
            },
            {
                "type": ResourceType.PROMPT_PROTOCOL,
                "description": "Prompt protocol definitions and schemas"
            },
            {
                "type": ResourceType.EXECUTION_STATE,
                "description": "Runtime execution state and progress"
            },
            {
                "type": ResourceType.EVENT_LOG,
                "description": "System events and audit trail"
            },
            {
                "type": ResourceType.AUDIT_TRAIL,
                "description": "Security and compliance audit logs"
            }
        ]
    }

@router.get("/resources/stats", summary="Resource Statistics")
async def get_resource_stats(server: MCPDataServer = Depends(get_mcp_data_server)):
    """Get statistics about stored resources"""
    try:
        # This would typically query the actual storage backend
        return {
            "total_contexts": 0,  # Would be actual count
            "total_events": 0,    # Would be actual count
            "storage_usage_bytes": 0,  # Would be actual usage
            "last_updated": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting resource stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving statistics")

# Health check for MCP Data Server
@router.get("/health", summary="Data Server Health Check")
async def health_check():
    """Health check for the MCP Data Server"""
    return {
        "status": "healthy",
        "service": "mcp_data_server",
        "timestamp": datetime.utcnow().isoformat(),
        "capabilities": [
            "context_management",
            "event_storage",
            "resource_metadata",
            "correlation_tracing"
        ]
    }