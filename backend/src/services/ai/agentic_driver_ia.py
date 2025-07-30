# -*- coding: utf-8 -*-
"""
Enhanced DriverIA - Agentic driver that consumes MCP Servers via HTTP
Pure MCP alignment with dynamic node suggestion and orchestration
"""
import logging
import asyncio
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
import json
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from mcp.protocol import (
    ToolListRequest, ToolCallRequest, GetContextRequest, SaveEventRequest,
    CorrelationContext, MCPVersion, ToolCapability
)
from services.interfaces import IDriverIA, IContextManager, IEventStore
from models.analysis import (
    AnalysisRequest, AnalysisContext, PromptProtocol, PromptNode, 
    PromptProtocolType, EventStoreEntry
)
from config.settings import settings
from core.exceptions import DriverIAException

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

class AgenticDriverIA(IDriverIA):
    """
    Enhanced agentic DriverIA that consumes MCP Servers via HTTP.
    Capable of dynamic protocol generation and node orchestration.
    """
    
    def __init__(
        self, 
        context_manager: IContextManager,
        event_store: IEventStore,
        mcp_tools_url: str = "http://localhost:8001/mcp/tools",
        mcp_data_url: str = "http://localhost:8001/mcp/data"
    ):
        self.context_manager = context_manager
        self.event_store = event_store
        self.mcp_tools_url = mcp_tools_url
        self.mcp_data_url = mcp_data_url
        self.logger = logging.getLogger(__name__)
        
        # HTTP client for MCP server communication
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={"Content-Type": "application/json"}
        )
        
        # Available tools cache
        self.available_tools: Dict[str, Any] = {}
        self.tools_last_updated = None
        
        self.logger.info("Agentic DriverIA initialized with MCP server integration")

    async def execute_protocol(self, protocol: PromptProtocol, context: AnalysisContext) -> None:
        """Execute a PromptProtocol using MCP servers with enhanced orchestration"""
        correlation_context = CorrelationContext(
            correlation_id=context.context_id,
            user_id=context.request_data.get("user_id"),
            session_id=context.request_data.get("session_id"),
            trace_id=str(uuid.uuid4())
        )
        
        with tracer.start_as_current_span("agentic_driver_execute_protocol") as span:
            span.set_attribute("correlation_id", correlation_context.correlation_id)
            span.set_attribute("protocol_name", protocol.name)
            span.set_attribute("protocol_type", protocol.protocol_type)
            
            try:
                self.logger.info(f"[{correlation_context.correlation_id}] Executing agentic protocol: {protocol.name}")
                
                # Save protocol start event via MCP Data Server
                await self._save_event_via_mcp(
                    correlation_context,
                    "agentic_protocol_started",
                    {
                        "protocol_name": protocol.name,
                        "protocol_type": protocol.protocol_type,
                        "nodes_count": len(protocol.nodes),
                        "agentic_mode": True
                    }
                )
                
                await self.context_manager.update_progress(context.context_id, 0, "Initializing agentic execution")
                
                # Refresh available tools
                await self._refresh_available_tools(correlation_context)
                
                # Execute nodes with dynamic adaptation
                results = {}
                for i, node in enumerate(protocol.nodes):
                    progress = int((i / len(protocol.nodes)) * 100)
                    await self.context_manager.update_progress(
                        context.context_id, 
                        progress, 
                        f"Executing agentic node: {node.name}"
                    )
                    
                    # Execute node with MCP integration
                    node_result = await self._execute_agentic_node(node, correlation_context, results)
                    results[node.node_id] = node_result
                    
                    # Dynamic node suggestion based on results
                    if node_result.get("success") and node_result.get("suggest_additional_nodes"):
                        suggested_nodes = await self._suggest_dynamic_nodes(node_result, correlation_context)
                        if suggested_nodes:
                            self.logger.info(f"[{correlation_context.correlation_id}] Adding {len(suggested_nodes)} dynamic nodes")
                            protocol.nodes.extend(suggested_nodes)
                    
                    await asyncio.sleep(0.3)  # Prevent overwhelming MCP servers
                
                # Generate comprehensive analysis using all results
                final_analysis = await self._generate_agentic_analysis(correlation_context, results)
                results["agentic_analysis"] = final_analysis
                
                await self.context_manager.set_results(context.context_id, results)
                await self.context_manager.update_progress(context.context_id, 100, "Agentic protocol completed")
                await self.context_manager.mark_completed(context.context_id)
                
                # Save completion event
                await self._save_event_via_mcp(
                    correlation_context,
                    "agentic_protocol_completed",
                    {
                        "protocol_name": protocol.name,
                        "results_count": len(results),
                        "final_nodes_count": len(protocol.nodes)
                    }
                )
                
                span.set_status(Status(StatusCode.OK))
                
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                self.logger.error(f"[{correlation_context.correlation_id}] Agentic protocol execution failed: {e}")
                
                await self.context_manager.mark_failed(context.context_id, str(e))
                await self._save_event_via_mcp(
                    correlation_context,
                    "agentic_protocol_failed",
                    {
                        "protocol_name": protocol.name,
                        "error": str(e)
                    }
                )
                
                raise DriverIAException(f"Agentic protocol execution failed: {e}")

    async def _execute_agentic_node(
        self, 
        node: PromptNode, 
        correlation_context: CorrelationContext, 
        previous_results: Dict
    ) -> Dict[str, Any]:
        """Execute a single node using MCP Tools Server with enhanced intelligence"""
        
        with tracer.start_as_current_span("agentic_node_execution") as span:
            span.set_attribute("node_name", node.name)
            span.set_attribute("tool_name", node.tool_name or "none")
            
            start_time = time.time()
            
            try:
                # Enhance parameters with previous results context
                enhanced_parameters = await self._enhance_node_parameters(node, previous_results, correlation_context)
                
                if node.tool_name:
                    # Execute via MCP Tools Server
                    tool_result = await self._call_tool_via_mcp(
                        node.tool_name, 
                        enhanced_parameters, 
                        correlation_context
                    )
                    
                    # Enhanced result processing
                    result_data = {
                        "node_name": node.name,
                        "tool_name": node.tool_name,
                        "success": tool_result.get("success", False),
                        "execution_time_ms": tool_result.get("execution_time_ms", 0),
                        "result": tool_result.get("result"),
                        "parameters_used": enhanced_parameters,
                        "mcp_metadata": tool_result.get("metadata"),
                        "agentic_enhancements": {
                            "parameter_enrichment": True,
                            "context_awareness": len(previous_results),
                            "execution_strategy": "mcp_optimized"
                        }
                    }
                    
                    # Analyze result for dynamic node suggestions
                    if result_data["success"] and result_data["result"]:
                        suggestions = await self._analyze_for_suggestions(result_data["result"], correlation_context)
                        if suggestions:
                            result_data["suggest_additional_nodes"] = True
                            result_data["suggested_tools"] = suggestions
                
                else:
                    # Processing node without tool
                    result_data = {
                        "node_name": node.name,
                        "success": True,
                        "execution_time_ms": int((time.time() - start_time) * 1000),
                        "result": {
                            "message": f"Agentic processing node {node.name} completed",
                            "context_size": len(previous_results)
                        },
                        "parameters_used": enhanced_parameters,
                        "agentic_enhancements": {
                            "context_processing": True,
                            "parameter_enrichment": True
                        }
                    }
                
                # Save node execution event
                await self._save_event_via_mcp(
                    correlation_context,
                    "agentic_node_completed" if result_data["success"] else "agentic_node_failed",
                    result_data
                )
                
                span.set_status(Status(StatusCode.OK))
                return result_data
                
            except Exception as e:
                execution_time = int((time.time() - start_time) * 1000)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                
                error_result = {
                    "node_name": node.name,
                    "success": False,
                    "error": str(e),
                    "execution_time_ms": execution_time,
                    "agentic_context": "error_handling"
                }
                
                await self._save_event_via_mcp(
                    correlation_context,
                    "agentic_node_error",
                    error_result
                )
                
                return error_result

    async def _refresh_available_tools(self, correlation_context: CorrelationContext):
        """Refresh available tools from MCP Tools Server"""
        try:
            request_data = ToolListRequest(
                correlation_context=correlation_context,
                mcp_version=MCPVersion()
            )
            
            response = await self.http_client.post(
                f"{self.mcp_tools_url}/list",
                json=request_data.dict()
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    self.available_tools = {
                        tool["tool_name"]: tool 
                        for tool in result.get("tools", [])
                    }
                    self.tools_last_updated = datetime.utcnow()
                    self.logger.info(f"[{correlation_context.correlation_id}] Refreshed {len(self.available_tools)} tools")
                    
        except Exception as e:
            self.logger.error(f"[{correlation_context.correlation_id}] Failed to refresh tools: {e}")

    async def _call_tool_via_mcp(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any], 
        correlation_context: CorrelationContext
    ) -> Dict[str, Any]:
        """Call a tool via MCP Tools Server"""
        request_data = ToolCallRequest(
            correlation_context=correlation_context,
            mcp_version=MCPVersion(),
            tool_name=tool_name,
            parameters=parameters
        )
        
        response = await self.http_client.post(
            f"{self.mcp_tools_url}/call",
            json=request_data.dict()
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"MCP Tools Server error: {response.status_code} - {response.text}")

    async def _save_event_via_mcp(
        self,
        correlation_context: CorrelationContext,
        event_type: str,
        event_data: Dict[str, Any]
    ):
        """Save event via MCP Data Server"""
        request_data = SaveEventRequest(
            correlation_context=correlation_context,
            mcp_version=MCPVersion(),
            event_type=event_type,
            event_data=event_data,
            agent="agentic_driver_ia"
        )
        
        try:
            response = await self.http_client.post(
                f"{self.mcp_data_url}/save_event",
                json=request_data.dict()
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Failed to save event via MCP: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error saving event via MCP: {e}")

    async def _enhance_node_parameters(
        self, 
        node: PromptNode, 
        previous_results: Dict, 
        correlation_context: CorrelationContext
    ) -> Dict[str, Any]:
        """Enhance node parameters with context and intelligence"""
        enhanced = node.parameters.copy()
        
        # Substitute references to previous results
        for key, value in enhanced.items():
            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                ref_key = value[1:-1]
                if ref_key in previous_results:
                    # Extract meaningful data from previous result
                    prev_result = previous_results[ref_key]
                    if isinstance(prev_result, dict) and prev_result.get("result"):
                        enhanced[key] = prev_result["result"]
                    else:
                        enhanced[key] = prev_result
        
        # Add agentic context
        enhanced["_agentic_context"] = {
            "correlation_id": correlation_context.correlation_id,
            "previous_nodes_count": len(previous_results),
            "execution_strategy": "mcp_enhanced"
        }
        
        return enhanced

    async def _suggest_dynamic_nodes(
        self, 
        node_result: Dict[str, Any], 
        correlation_context: CorrelationContext
    ) -> List[PromptNode]:
        """Suggest additional nodes based on current results"""
        suggestions = []
        
        if not node_result.get("suggested_tools"):
            return suggestions
        
        for suggested_tool in node_result["suggested_tools"]:
            if suggested_tool in self.available_tools:
                # Create dynamic node
                dynamic_node = PromptNode(
                    node_id=f"dynamic_{suggested_tool}_{int(time.time())}",
                    name=f"Dynamic {suggested_tool} Analysis",
                    tool_name=suggested_tool,
                    parameters={
                        "input_from_previous": "{previous_result}",
                        "_dynamic_generation": True
                    },
                    dependencies=[]
                )
                suggestions.append(dynamic_node)
        
        return suggestions

    async def _analyze_for_suggestions(
        self, 
        result: Dict[str, Any], 
        correlation_context: CorrelationContext
    ) -> List[str]:
        """Analyze result to suggest additional tools"""
        suggestions = []
        
        # Simple heuristics for tool suggestions
        if isinstance(result, dict):
            # If we have sequence data, suggest structure prediction
            if any(key in result for key in ["sequence", "sequences", "protein_sequence"]):
                if "alphafold" in self.available_tools:
                    suggestions.append("alphafold")
            
            # If we have BLAST results, suggest domain analysis
            if "hits" in result or "blast_results" in result:
                if "interpro" in self.available_tools:
                    suggestions.append("interpro")
            
            # If we have structure, suggest docking
            if "structure" in result or "pdb_data" in result:
                if "swissdock" in self.available_tools:
                    suggestions.append("swissdock")
        
        return suggestions

    async def _generate_agentic_analysis(
        self, 
        correlation_context: CorrelationContext, 
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive agentic analysis of all results"""
        
        analysis = {
            "agentic_summary": "Comprehensive analysis completed using MCP-based orchestration",
            "execution_strategy": "mcp_enhanced_agentic",
            "total_nodes_executed": len([k for k in results.keys() if k != "agentic_analysis"]),
            "successful_nodes": len([r for r in results.values() if isinstance(r, dict) and r.get("success", False)]),
            "mcp_integration": {
                "tools_server_calls": len([r for r in results.values() if isinstance(r, dict) and r.get("tool_name")]),
                "dynamic_nodes_generated": len([r for r in results.values() if isinstance(r, dict) and r.get("_dynamic_generation")]),
                "correlation_id": correlation_context.correlation_id
            },
            "key_findings": [],
            "recommendations": [],
            "confidence_score": 0.0
        }
        
        # Extract key findings from results
        successful_results = [
            r for r in results.values() 
            if isinstance(r, dict) and r.get("success") and r.get("result")
        ]
        
        for result in successful_results:
            result_data = result.get("result", {})
            if isinstance(result_data, dict):
                # Extract findings based on tool type
                if "function" in result_data:
                    analysis["key_findings"].append(f"Function prediction: {result_data['function']}")
                if "confidence" in result_data:
                    analysis["confidence_score"] = max(analysis["confidence_score"], result_data.get("confidence", 0))
                if "hits" in result_data:
                    analysis["key_findings"].append(f"Homology found: {len(result_data['hits'])} hits")
        
        # Generate recommendations
        if analysis["confidence_score"] > 0.7:
            analysis["recommendations"].append("High confidence results - suitable for publication")
        elif analysis["confidence_score"] > 0.4:
            analysis["recommendations"].append("Moderate confidence - consider additional validation")
        else:
            analysis["recommendations"].append("Low confidence - requires further investigation")
        
        return analysis

    async def analyze_results(self, context_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - delegates to agentic analysis"""
        correlation_context = CorrelationContext(
            correlation_id=context_id,
            trace_id=str(uuid.uuid4())
        )
        return await self._generate_agentic_analysis(correlation_context, results)

    async def close(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()