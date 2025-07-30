# -*- coding: utf-8 -*-
"""
MCP Protocol Models - Pure MCP alignment implementation
Standardized contracts for tools and data MCP servers
"""
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# ===============================================================================
# MCP PROTOCOL VERSIONING
# ===============================================================================

class MCPVersion(BaseModel):
    """MCP Protocol version metadata"""
    major: int = 1
    minor: int = 0
    patch: int = 0
    
    @property
    def version_string(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def is_compatible(self, other: "MCPVersion") -> bool:
        """Check if versions are compatible (same major version)"""
        return self.major == other.major and self.minor <= other.minor

# ===============================================================================
# CORRELATION ID AND TRACING
# ===============================================================================

class CorrelationContext(BaseModel):
    """Distributed tracing context"""
    correlation_id: str = Field(..., description="Unique correlation ID for request tracing")
    user_id: Optional[str] = Field(None, description="User ID for audit logging")
    session_id: Optional[str] = Field(None, description="Session ID")
    node_id: Optional[str] = Field(None, description="Current processing node ID")
    parent_span_id: Optional[str] = Field(None, description="Parent span for OpenTelemetry")
    trace_id: Optional[str] = Field(None, description="Trace ID for OpenTelemetry")

# ===============================================================================
# MCP TOOLS SERVER CONTRACTS
# ===============================================================================

class ToolCapability(str, Enum):
    """Tool capability types"""
    BIOINFORMATICS = "bioinformatics"
    HARDWARE = "hardware"
    AI_ANALYSIS = "ai_analysis"
    DATA_PROCESSING = "data_processing"
    VISUALIZATION = "visualization"

class ToolMetadata(BaseModel):
    """Tool metadata and capabilities"""
    tool_name: str = Field(..., description="Unique tool identifier")
    display_name: str = Field(..., description="Human-readable tool name")
    description: str = Field(..., description="Tool description")
    version: str = Field(..., description="Tool version")
    capabilities: List[ToolCapability] = Field(..., description="Tool capabilities")
    input_schema: Dict[str, Any] = Field(..., description="JSON schema for tool inputs")
    output_schema: Dict[str, Any] = Field(..., description="JSON schema for tool outputs")
    requires_auth: bool = Field(False, description="Whether tool requires authentication")
    estimated_duration_ms: Optional[int] = Field(None, description="Estimated execution time")

class ToolListRequest(BaseModel):
    """Request to list available tools"""
    correlation_context: CorrelationContext
    mcp_version: MCPVersion = Field(default_factory=MCPVersion)
    filter_capabilities: Optional[List[ToolCapability]] = Field(None, description="Filter by capabilities")

class ToolListResponse(BaseModel):
    """Response with available tools"""
    success: bool = True
    tools: List[ToolMetadata] = Field(..., description="Available tools")
    total_count: int = Field(..., description="Total number of tools")
    mcp_version: MCPVersion = Field(default_factory=MCPVersion)
    correlation_context: CorrelationContext

class ToolCallRequest(BaseModel):
    """Request to execute a tool"""
    correlation_context: CorrelationContext
    mcp_version: MCPVersion = Field(default_factory=MCPVersion)
    tool_name: str = Field(..., description="Tool to execute")
    parameters: Dict[str, Any] = Field(..., description="Tool execution parameters")
    timeout_ms: Optional[int] = Field(30000, description="Execution timeout in milliseconds")
    retry_count: int = Field(0, description="Number of retries attempted")

class ToolCallResponse(BaseModel):
    """Response from tool execution"""
    success: bool = Field(..., description="Whether execution succeeded")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool execution result")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: int = Field(..., description="Actual execution time")
    tool_version: str = Field(..., description="Version of tool that executed")
    correlation_context: CorrelationContext
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

# ===============================================================================
# MCP DATA SERVER CONTRACTS
# ===============================================================================

class ResourceType(str, Enum):
    """Resource types for data server"""
    ANALYSIS_CONTEXT = "analysis_context"
    PROMPT_PROTOCOL = "prompt_protocol"
    EXECUTION_STATE = "execution_state"
    EVENT_LOG = "event_log"
    AUDIT_TRAIL = "audit_trail"

class ResourceMetadata(BaseModel):
    """Resource metadata"""
    resource_id: str = Field(..., description="Unique resource identifier")
    resource_type: ResourceType = Field(..., description="Type of resource")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    version: int = Field(1, description="Resource version")
    tags: Optional[List[str]] = Field(None, description="Resource tags")
    size_bytes: Optional[int] = Field(None, description="Resource size in bytes")

class GetContextRequest(BaseModel):
    """Request to get analysis context"""
    correlation_context: CorrelationContext
    mcp_version: MCPVersion = Field(default_factory=MCPVersion)
    context_id: str = Field(..., description="Context ID to retrieve")
    include_history: bool = Field(False, description="Include execution history")

class GetContextResponse(BaseModel):
    """Response with analysis context"""
    success: bool = True
    context_data: Optional[Dict[str, Any]] = Field(None, description="Context data")
    metadata: Optional[ResourceMetadata] = Field(None, description="Resource metadata")
    history: Optional[List[Dict[str, Any]]] = Field(None, description="Execution history")
    correlation_context: CorrelationContext

class SaveEventRequest(BaseModel):
    """Request to save an event"""
    correlation_context: CorrelationContext
    mcp_version: MCPVersion = Field(default_factory=MCPVersion)
    event_type: str = Field(..., description="Type of event")
    event_data: Dict[str, Any] = Field(..., description="Event payload")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    agent: str = Field(..., description="Agent that generated the event")

class SaveEventResponse(BaseModel):
    """Response from saving event"""
    success: bool = True
    event_id: str = Field(..., description="Generated event ID")
    correlation_context: CorrelationContext

# ===============================================================================
# AUDIT LOGGING MODELS
# ===============================================================================

class AuditLogEntry(BaseModel):
    """Audit log entry for tool calls and operations"""
    audit_id: str = Field(..., description="Unique audit entry ID")
    correlation_context: CorrelationContext
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    operation: str = Field(..., description="Operation performed")
    tool_name: Optional[str] = Field(None, description="Tool name if applicable")
    input_data_hash: Optional[str] = Field(None, description="Hash of input data")
    output_data_hash: Optional[str] = Field(None, description="Hash of output data")
    success: bool = Field(..., description="Whether operation succeeded")
    execution_time_ms: int = Field(..., description="Execution time")
    error_details: Optional[str] = Field(None, description="Error details if failed")
    sensitive_data_encrypted: bool = Field(False, description="Whether sensitive data was encrypted")

# ===============================================================================
# ERROR MODELS
# ===============================================================================

class MCPError(BaseModel):
    """Standardized MCP error response"""
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    correlation_context: CorrelationContext
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

# ===============================================================================
# PROTOCOL VALIDATION
# ===============================================================================

class PromptProtocolValidation(BaseModel):
    """Validation for PromptProtocols"""
    protocol_id: str = Field(..., description="Protocol identifier")
    version: MCPVersion = Field(default_factory=MCPVersion)
    is_valid: bool = Field(..., description="Whether protocol is valid")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors")
    dag_cycles: List[str] = Field(default_factory=list, description="DAG cycle violations")
    dependency_issues: List[str] = Field(default_factory=list, description="Dependency issues")

# ===============================================================================
# HARDWARE NAMESPACE MODELS
# ===============================================================================

class HardwareDeviceType(str, Enum):
    """Hardware device types"""
    MICROSCOPE = "microscope"
    SPECTROMETER = "spectrometer"
    CENTRIFUGE = "centrifuge"
    THERMAL_CYCLER = "thermal_cycler"
    PIPETTE = "pipette"
    INCUBATOR = "incubator"

class HardwareDevice(BaseModel):
    """Hardware device mock definition"""
    device_id: str = Field(..., description="Unique device identifier")
    device_type: HardwareDeviceType = Field(..., description="Type of device")
    name: str = Field(..., description="Device name")
    status: str = Field("available", description="Device status")
    capabilities: List[str] = Field(..., description="Device capabilities")
    parameters: Dict[str, Any] = Field(..., description="Device parameters")
    mock_responses: Dict[str, Any] = Field(..., description="Mock response patterns")