# -*- coding: utf-8 -*-
"""
MCP Tools Server - Standardized tool execution service
Implements tools/list and tools/call endpoints with correlation tracing
"""
import logging
import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from mcp.protocol import (
    ToolListRequest, ToolListResponse, ToolCallRequest, ToolCallResponse,
    ToolMetadata, ToolCapability, MCPError, CorrelationContext, MCPVersion,
    AuditLogEntry, HardwareDevice, HardwareDeviceType
)
from services.interfaces import IToolGateway, IEventStore
from services.agentic.atomic_tools import atomic_tool_registry, AtomicToolResult
from services.hardware.devices import hardware_manager
from core.exceptions import ToolGatewayException, CircuitBreakerOpenException

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

class MCPToolsServer:
    """MCP Tools Server implementation with atomic tool execution"""
    
    def __init__(self, tool_gateway: IToolGateway, event_store: IEventStore):
        self.tool_gateway = tool_gateway
        self.event_store = event_store
        self.available_tools: Dict[str, ToolMetadata] = {}
        self._initialize_tools()
        
    def _initialize_tools(self):
        """Initialize available tools metadata from atomic tool registry"""
        # Get tools from enhanced atomic tool registry
        atomic_tools = atomic_tool_registry.list_tools()
        
        for tool_name in atomic_tools:
            metadata = atomic_tool_registry.get_tool_metadata(tool_name)
            if metadata:
                tool_metadata = ToolMetadata(
                    tool_name=metadata["tool_name"],
                    display_name=metadata["tool_name"].replace("_", " ").title(),
                    description=f"Enhanced atomic {metadata['tool_name']} tool",
                    version="2.0.0",  # Enhanced version
                    capabilities=metadata["capabilities"],
                    input_schema=metadata["input_schema"],
                    output_schema=metadata["output_schema"],
                    estimated_duration_ms=5000  # Default estimate
                )
                self.available_tools[tool_name] = tool_metadata
        
        # Add AI Analysis tools
        ai_tools = [
            {
                "tool_name": "sequence_analyzer",
                "display_name": "AI Sequence Analyzer",
                "description": "LLM-powered sequence analysis and interpretation",
                "version": "1.0.0",
                "capabilities": [ToolCapability.AI_ANALYSIS],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sequence": {"type": "string"},
                        "analysis_type": {"type": "string", "enum": ["function", "structure", "evolution"]},
                        "context": {"type": "string"}
                    },
                    "required": ["sequence", "analysis_type"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "analysis": {"type": "string"},
                        "confidence": {"type": "number"},
                        "findings": {"type": "array"}
                    }
                },
                "estimated_duration_ms": 3000
            }
        ]
        
        # Register AI tools
        for tool_data in ai_tools:
            tool_metadata = ToolMetadata(**tool_data)
            self.available_tools[tool_metadata.tool_name] = tool_metadata

# Create router
router = APIRouter()

# Dependency injection
mcp_tools_server: Optional[MCPToolsServer] = None

def get_mcp_tools_server() -> MCPToolsServer:
    """Get MCP Tools Server instance"""
    if mcp_tools_server is None:
        raise HTTPException(status_code=500, detail="MCP Tools Server not initialized")
    return mcp_tools_server

def initialize_mcp_tools_server(tool_gateway: IToolGateway, event_store: IEventStore):
    """Initialize the MCP Tools Server"""
    global mcp_tools_server
    mcp_tools_server = MCPToolsServer(tool_gateway, event_store)

@router.post("/list", response_model=ToolListResponse, summary="List Available Tools")
async def list_tools(
    request: ToolListRequest,
    server: MCPToolsServer = Depends(get_mcp_tools_server)
) -> ToolListResponse:
    """
    List all available tools with filtering capabilities.
    Implements standardized MCP tools/list endpoint.
    """
    with tracer.start_as_current_span("mcp_tools_list") as span:
        span.set_attribute("correlation_id", request.correlation_context.correlation_id)
        span.set_attribute("user_id", request.correlation_context.user_id or "anonymous")
        
        try:
            logger.info(f"[{request.correlation_context.correlation_id}] Listing tools")
            
            # Filter tools by capabilities if requested
            filtered_tools = list(server.available_tools.values())
            if request.filter_capabilities:
                filtered_tools = [
                    tool for tool in filtered_tools
                    if any(cap in tool.capabilities for cap in request.filter_capabilities)
                ]
            
            # Add hardware tools from hardware manager
            devices = hardware_manager.list_devices()
            hardware_tools = []
            for device in devices:
                hardware_tool = ToolMetadata(
                    tool_name=f"hardware_{device.device_id}",
                    display_name=f"Hardware: {device.name}",
                    description=f"Control {device.device_type.value} device",
                    version="1.0.0",
                    capabilities=[ToolCapability.HARDWARE],
                    input_schema={
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": list(device.mock_responses.keys())},
                            "parameters": {"type": "object"}
                        },
                        "required": ["action"]
                    },
                    output_schema={
                        "type": "object",
                        "properties": {
                            "result": {"type": "object"},
                            "device_status": {"type": "string"}
                        }
                    },
                    estimated_duration_ms=2000
                )
                hardware_tools.append(hardware_tool)
            
            all_tools = filtered_tools + hardware_tools
            
            # Log event
            await server.event_store.store_event({
                "context_id": request.correlation_context.correlation_id,
                "event_type": "tools_listed",
                "data": {
                    "total_tools": len(all_tools),
                    "filter_capabilities": request.filter_capabilities
                },
                "agent": "mcp_tools_server"
            })
            
            span.set_status(Status(StatusCode.OK))
            
            return ToolListResponse(
                tools=all_tools,
                total_count=len(all_tools),
                correlation_context=request.correlation_context,
                mcp_version=request.mcp_version
            )
            
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(f"[{request.correlation_context.correlation_id}] Error listing tools: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@router.post("/call", response_model=ToolCallResponse, summary="Execute Tool")
async def call_tool(
    request: ToolCallRequest,
    server: MCPToolsServer = Depends(get_mcp_tools_server)
) -> ToolCallResponse:
    """
    Execute a specific tool with the provided parameters.
    Implements standardized MCP tools/call endpoint with full audit logging.
    """
    with tracer.start_as_current_span("mcp_tools_call") as span:
        span.set_attribute("correlation_id", request.correlation_context.correlation_id)
        span.set_attribute("tool_name", request.tool_name)
        span.set_attribute("user_id", request.correlation_context.user_id or "anonymous")
        
        start_time = time.time()
        audit_entry = None
        
        try:
            logger.info(f"[{request.correlation_context.correlation_id}] Executing tool: {request.tool_name}")
            
            # Check if tool exists in atomic tool registry
            if request.tool_name in atomic_tool_registry.list_tools():
                # Execute via atomic tool registry
                result = await atomic_tool_registry.execute_tool(
                    request.tool_name,
                    request.parameters,
                    request.correlation_context
                )
                
                if result.success:
                    execution_time_ms = result.execution_time_ms
                    tool_result = result.result
                    tool_version = "2.0.0"  # Enhanced atomic tools version
                else:
                    raise ToolGatewayException(f"Atomic tool execution failed: {result.error_message}")
                
            elif request.tool_name.startswith("hardware_"):
                # Hardware tool execution
                device_id = request.tool_name.replace("hardware_", "")
                device = hardware_manager.get_device(device_id)
                if not device:
                    raise HTTPException(status_code=404, detail=f"Hardware device not found: {device_id}")
                
                result = await hardware_manager.execute_device_action(
                    device_id,
                    request.parameters.get("action"),
                    request.parameters.get("parameters", {})
                )
                tool_result = result
                tool_version = "1.0.0"
                
            elif request.tool_name in server.available_tools:
                # Legacy tool execution via tool gateway
                tool_metadata = server.available_tools[request.tool_name]
                result = await server.tool_gateway.invoke_tool(request.tool_name, request.parameters)
                tool_version = tool_metadata.version
                
                if not result.success:
                    raise ToolGatewayException(f"Tool execution failed: {result.error_message}")
                    
                tool_result = result.result
                
            else:
                raise HTTPException(status_code=404, detail=f"Tool not found: {request.tool_name}")
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Create audit log entry
            audit_entry = AuditLogEntry(
                audit_id=str(uuid.uuid4()),
                correlation_context=request.correlation_context,
                operation="tool_call",
                tool_name=request.tool_name,
                input_data_hash=str(hash(str(request.parameters))),
                output_data_hash=str(hash(str(tool_result))),
                success=True,
                execution_time_ms=execution_time_ms
            )
            
            # Store audit log
            await server.event_store.store_event({
                "context_id": request.correlation_context.correlation_id,
                "event_type": "tool_executed",
                "data": audit_entry.dict(),
                "agent": "mcp_tools_server"
            })
            
            span.set_status(Status(StatusCode.OK))
            
            return ToolCallResponse(
                success=True,
                result=tool_result,
                execution_time_ms=execution_time_ms,
                tool_version=tool_version,
                correlation_context=request.correlation_context,
                metadata={"audit_id": audit_entry.audit_id}
            )
            
        except CircuitBreakerOpenException as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            
            # Create failure audit log
            audit_entry = AuditLogEntry(
                audit_id=str(uuid.uuid4()),
                correlation_context=request.correlation_context,
                operation="tool_call",
                tool_name=request.tool_name,
                input_data_hash=str(hash(str(request.parameters))),
                success=False,
                execution_time_ms=execution_time_ms,
                error_details=f"Circuit breaker open: {str(e)}"
            )
            
            await server.event_store.store_event({
                "context_id": request.correlation_context.correlation_id,
                "event_type": "tool_failed",
                "data": audit_entry.dict(),
                "agent": "mcp_tools_server"
            })
            
            return ToolCallResponse(
                success=False,
                error_message=f"Service temporarily unavailable: {str(e)}",
                execution_time_ms=execution_time_ms,
                tool_version="unknown",
                correlation_context=request.correlation_context,
                metadata={"audit_id": audit_entry.audit_id}
            )
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(f"[{request.correlation_context.correlation_id}] Tool execution error: {e}")
            
            # Create failure audit log
            audit_entry = AuditLogEntry(
                audit_id=str(uuid.uuid4()),
                correlation_context=request.correlation_context,
                operation="tool_call",
                tool_name=request.tool_name,
                input_data_hash=str(hash(str(request.parameters))),
                success=False,
                execution_time_ms=execution_time_ms,
                error_details=str(e)
            )
            
            await server.event_store.store_event({
                "context_id": request.correlation_context.correlation_id,
                "event_type": "tool_failed",
                "data": audit_entry.dict(),
                "agent": "mcp_tools_server"
            })
            
            return ToolCallResponse(
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time_ms,
                tool_version="unknown",
                correlation_context=request.correlation_context,
                metadata={"audit_id": audit_entry.audit_id if audit_entry else None}
            )

# Health check for MCP Tools Server
@router.get("/health", summary="Tools Server Health Check")
async def health_check(server: MCPToolsServer = Depends(get_mcp_tools_server)):
    """Health check for the MCP Tools Server"""
    return {
        "status": "healthy",
        "available_tools": len(server.available_tools),
        "atomic_tools": len(atomic_tool_registry.list_tools()),
        "hardware_devices": len(hardware_manager.list_devices()),
        "execution_stats": atomic_tool_registry.get_execution_statistics(),
        "timestamp": datetime.utcnow().isoformat()
    }