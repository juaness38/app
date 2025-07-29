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
from core.exceptions import ToolGatewayException, CircuitBreakerOpenException

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

class MCPToolsServer:
    """MCP Tools Server implementation with atomic tool execution"""
    
    def __init__(self, tool_gateway: IToolGateway, event_store: IEventStore):
        self.tool_gateway = tool_gateway
        self.event_store = event_store
        self.available_tools: Dict[str, ToolMetadata] = {}
        self.hardware_devices: Dict[str, HardwareDevice] = {}
        self._initialize_tools()
        self._initialize_hardware_devices()
        
    def _initialize_tools(self):
        """Initialize available tools metadata"""
        # Bioinformatics tools
        bioinformatics_tools = [
            {
                "tool_name": "blast",
                "display_name": "BLAST Sequence Search",
                "description": "Basic Local Alignment Search Tool for sequence homology",
                "version": "2.14.0",
                "capabilities": [ToolCapability.BIOINFORMATICS],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sequence": {"type": "string", "description": "Input sequence"},
                        "database": {"type": "string", "description": "Target database"},
                        "e_value": {"type": "number", "default": 0.001}
                    },
                    "required": ["sequence"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "hits": {"type": "array", "items": {"type": "object"}},
                        "statistics": {"type": "object"}
                    }
                },
                "estimated_duration_ms": 5000
            },
            {
                "tool_name": "mafft",
                "display_name": "MAFFT Multiple Alignment",
                "description": "Multiple sequence alignment using MAFFT",
                "version": "7.505",
                "capabilities": [ToolCapability.BIOINFORMATICS],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sequences": {"type": "array", "items": {"type": "string"}},
                        "algorithm": {"type": "string", "default": "auto"}
                    },
                    "required": ["sequences"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "aligned_sequences": {"type": "array"},
                        "alignment_score": {"type": "number"}
                    }
                },
                "estimated_duration_ms": 8000
            },
            {
                "tool_name": "alphafold",
                "display_name": "AlphaFold Structure Prediction",
                "description": "3D protein structure prediction using AlphaFold",
                "version": "2.3.0",
                "capabilities": [ToolCapability.BIOINFORMATICS, ToolCapability.AI_ANALYSIS],
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sequence": {"type": "string", "description": "Protein sequence"},
                        "confidence_threshold": {"type": "number", "default": 70}
                    },
                    "required": ["sequence"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "structure": {"type": "object"},
                        "confidence_scores": {"type": "array"},
                        "pdb_data": {"type": "string"}
                    }
                },
                "estimated_duration_ms": 15000
            }
        ]
        
        # AI Analysis tools
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
        
        # Register all tools
        for tool_data in bioinformatics_tools + ai_tools:
            tool_metadata = ToolMetadata(**tool_data)
            self.available_tools[tool_metadata.tool_name] = tool_metadata
            
    def _initialize_hardware_devices(self):
        """Initialize mock hardware devices"""
        devices = [
            {
                "device_id": "microscope_01",
                "device_type": HardwareDeviceType.MICROSCOPE,
                "name": "Fluorescence Microscope Alpha",
                "status": "available",
                "capabilities": ["fluorescence", "brightfield", "phase_contrast"],
                "parameters": {
                    "magnification_range": [10, 1000],
                    "resolution": "0.2μm",
                    "wavelengths": [405, 488, 561, 640]
                },
                "mock_responses": {
                    "capture_image": {"image_id": "img_{timestamp}", "format": "tiff", "size": "2048x2048"},
                    "set_magnification": {"current_magnification": "{requested_value}"},
                    "acquire_stack": {"stack_id": "stack_{timestamp}", "num_slices": "{z_slices}"}
                }
            },
            {
                "device_id": "thermal_cycler_01",
                "device_type": HardwareDeviceType.THERMAL_CYCLER,
                "name": "PCR Thermal Cycler Beta",
                "status": "available",
                "capabilities": ["pcr", "gradient_pcr", "real_time_monitoring"],
                "parameters": {
                    "temperature_range": [-10, 105],
                    "accuracy": "±0.1°C",
                    "ramp_rate": "5°C/s",
                    "block_volume": "0.2ml"
                },
                "mock_responses": {
                    "run_pcr": {"run_id": "pcr_{timestamp}", "status": "running", "estimated_time": "{cycle_time}"},
                    "get_temperature": {"current_temp": "{target_temp}", "block_temp": "{target_temp}"},
                    "set_program": {"program_id": "prog_{timestamp}", "cycles": "{num_cycles}"}
                }
            }
        ]
        
        for device_data in devices:
            device = HardwareDevice(**device_data)
            self.hardware_devices[device.device_id] = device

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
            
            # Add hardware tools
            hardware_tools = []
            for device in server.hardware_devices.values():
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
            
            # Check if tool exists
            if request.tool_name.startswith("hardware_"):
                # Hardware tool execution
                device_id = request.tool_name.replace("hardware_", "")
                if device_id not in server.hardware_devices:
                    raise HTTPException(status_code=404, detail=f"Hardware device not found: {device_id}")
                
                result = await _execute_hardware_tool(server.hardware_devices[device_id], request)
                tool_version = "1.0.0"
                
            elif request.tool_name in server.available_tools:
                # Standard tool execution
                tool_metadata = server.available_tools[request.tool_name]
                result = await server.tool_gateway.invoke_tool(request.tool_name, request.parameters)
                tool_version = tool_metadata.version
                
                if not result.success:
                    raise ToolGatewayException(f"Tool execution failed: {result.error_message}")
                    
                result = result.result
                
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
                output_data_hash=str(hash(str(result))),
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
                result=result,
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

async def _execute_hardware_tool(device: HardwareDevice, request: ToolCallRequest) -> Dict[str, Any]:
    """Execute hardware device tool with mock responses"""
    action = request.parameters.get("action")
    if action not in device.mock_responses:
        raise HTTPException(status_code=400, detail=f"Invalid action for device: {action}")
    
    # Simulate hardware execution time
    await asyncio.sleep(0.5)
    
    # Generate mock response
    mock_response = device.mock_responses[action].copy()
    timestamp = str(int(time.time()))
    
    # Replace placeholders in mock response
    for key, value in mock_response.items():
        if isinstance(value, str):
            mock_response[key] = value.replace("{timestamp}", timestamp)
            for param_key, param_value in request.parameters.get("parameters", {}).items():
                mock_response[key] = mock_response[key].replace(f"{{{param_key}}}", str(param_value))
    
    return {
        "result": mock_response,
        "device_status": device.status,
        "device_id": device.device_id,
        "action_executed": action
    }

# Health check for MCP Tools Server
@router.get("/health", summary="Tools Server Health Check")
async def health_check(server: MCPToolsServer = Depends(get_mcp_tools_server)):
    """Health check for the MCP Tools Server"""
    return {
        "status": "healthy",
        "available_tools": len(server.available_tools),
        "hardware_devices": len(server.hardware_devices),
        "timestamp": datetime.utcnow().isoformat()
    }