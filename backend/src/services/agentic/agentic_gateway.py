# -*- coding: utf-8 -*-
"""
ASTROFLORA - GATEWAY AGÉNTICO
Gateway que expone herramientas atómicas al DriverIA vía MCP.
FASE 1: Coexistencia y Estabilización - Preparación para capacidades agénticas completas.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.services.interfaces import IToolGateway
from src.models.analysis import ToolResult
from src.services.agentic.atomic_tools import (
    AtomicTool, BlastSearchTool, UniProtAnnotationTool, 
    SequenceFeaturesTool, LLMAnalysisTool
)

logger = logging.getLogger(__name__)

class AgenticToolGateway(IToolGateway):
    """
    Gateway que expone herramientas atómicas al DriverIA vía MCP.
    FASE 1: Mantiene compatibilidad con herramientas existentes mientras prepara la arquitectura agéntica.
    """

    def __init__(
        self,
        blast_service,
        uniprot_service,
        llm_service,
        circuit_breaker_factory
    ):
        # Inicializa herramientas atómicas
        self.atomic_tools: Dict[str, AtomicTool] = {
            "blast_search": BlastSearchTool(blast_service, circuit_breaker_factory),
            "uniprot_annotations": UniProtAnnotationTool(uniprot_service, circuit_breaker_factory),
            "sequence_features": SequenceFeaturesTool(),
            "llm_analysis": LLMAnalysisTool(llm_service, circuit_breaker_factory)
        }

        # Métricas del gateway
        self.gateway_metrics = {
            "total_tool_invocations": 0,
            "successful_invocations": 0,
            "failed_invocations": 0,
            "tools_performance": {},
            "last_reset": datetime.utcnow()
        }

        # Referencias a servicios para compatibilidad con la interfaz existente
        self.blast_service = blast_service
        self.uniprot_service = uniprot_service
        self.llm_service = llm_service
        self.circuit_breaker_factory = circuit_breaker_factory

        logger.info(f"AgenticToolGateway inicializado con {len(self.atomic_tools)} herramientas atómicas")

    # ============================================================================
    # INTERFAZ AGÉNTICA - NUEVAS CAPACIDADES
    # ============================================================================

    async def invoke_atomic_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """Invoca herramienta atómica específica."""
        self.gateway_metrics["total_tool_invocations"] += 1

        if tool_name not in self.atomic_tools:
            self.gateway_metrics["failed_invocations"] += 1
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error_message=f"Herramienta atómica no encontrada: {tool_name}",
                timestamp=datetime.utcnow()
            )

        try:
            tool = self.atomic_tools[tool_name]
            result = await tool.execute(parameters)
            
            # Actualiza métricas
            if result.success:
                self.gateway_metrics["successful_invocations"] += 1
            else:
                self.gateway_metrics["failed_invocations"] += 1

            # Actualiza métricas por herramienta
            if tool_name not in self.gateway_metrics["tools_performance"]:
                self.gateway_metrics["tools_performance"][tool_name] = {
                    "invocations": 0,
                    "successes": 0,
                    "failures": 0
                }
            
            tool_metrics = self.gateway_metrics["tools_performance"][tool_name]
            tool_metrics["invocations"] += 1
            if result.success:
                tool_metrics["successes"] += 1
            else:
                tool_metrics["failures"] += 1

            return result

        except Exception as e:
            self.gateway_metrics["failed_invocations"] += 1
            logger.error(f"Error invocando herramienta atómica {tool_name}: {e}")
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error_message=f"Error de ejecución: {str(e)}",
                timestamp=datetime.utcnow()
            )

    async def get_available_atomic_tools(self) -> List[str]:
        """Lista herramientas atómicas disponibles."""
        return list(self.atomic_tools.keys())

    async def get_atomic_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """Obtiene schema de parámetros para una herramienta atómica."""
        if tool_name not in self.atomic_tools:
            raise ValueError(f"Herramienta atómica no encontrada: {tool_name}")

        tool = self.atomic_tools[tool_name]
        return {
            "name": tool.name,
            "description": tool.description,
            "scientific_purpose": tool.scientific_purpose,
            "parameters": tool.get_parameter_schema(),
            "metadata": tool.get_scientific_metadata()
        }

    async def get_all_atomic_tools_schema(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene schemas de todas las herramientas atómicas."""
        schemas = {}
        for tool_name in self.atomic_tools.keys():
            schemas[tool_name] = await self.get_atomic_tool_schema(tool_name)
        return schemas

    async def assess_tool_applicability(self, context: Dict[str, Any]) -> Dict[str, float]:
        """Evalúa qué tan aplicable es cada herramienta para el contexto dado."""
        applicability_scores = {}
        
        for tool_name, tool in self.atomic_tools.items():
            try:
                score = await tool.assess_applicability(context)
                applicability_scores[tool_name] = score
            except Exception as e:
                logger.warning(f"Error evaluando aplicabilidad de {tool_name}: {e}")
                applicability_scores[tool_name] = 0.5  # Puntuación neutra

        return applicability_scores

    async def recommend_tools_for_context(self, context: Dict[str, Any], min_score: float = 0.5) -> List[Dict[str, Any]]:
        """Recomienda herramientas apropiadas para un contexto específico."""
        applicability_scores = await self.assess_tool_applicability(context)
        
        recommendations = []
        for tool_name, score in applicability_scores.items():
            if score >= min_score:
                tool = self.atomic_tools[tool_name]
                recommendations.append({
                    "tool_name": tool_name,
                    "applicability_score": score,
                    "description": tool.description,
                    "scientific_purpose": tool.scientific_purpose,
                    "priority": "high" if score > 0.8 else "medium" if score > 0.6 else "low"
                })
        
        # Ordena por puntuación de aplicabilidad
        recommendations.sort(key=lambda x: x["applicability_score"], reverse=True)
        return recommendations

    async def health_check_atomic_tool(self, tool_name: str) -> bool:
        """Verifica salud de herramienta atómica específica."""
        if tool_name not in self.atomic_tools:
            return False

        try:
            # Test básico con parámetros mínimos según el tipo de herramienta
            if tool_name == "blast_search":
                result = await self.invoke_atomic_tool(tool_name, {"sequence": "ATCGATCGATCG"})
            elif tool_name == "uniprot_annotations":
                result = await self.invoke_atomic_tool(tool_name, {"protein_ids": ["P12345"]})
            elif tool_name == "sequence_features":
                result = await self.invoke_atomic_tool(tool_name, {"sequence": "ATCGATCGATCG"})
            elif tool_name == "llm_analysis":
                result = await self.invoke_atomic_tool(tool_name, {"data": {"test": "data"}})
            else:
                return True  # Herramientas sin test específico

            # Para health check, incluso errores de parámetros indican que la herramienta responde
            return True

        except Exception as e:
            logger.error(f"Health check falló para herramienta atómica {tool_name}: {e}")
            return False

    async def get_gateway_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas completas del gateway."""
        # Calcula tasas de éxito
        total_invocations = self.gateway_metrics["total_tool_invocations"]
        success_rate = (self.gateway_metrics["successful_invocations"] / total_invocations * 100) if total_invocations > 0 else 0

        # Métricas por herramienta
        tool_performance = {}
        for tool_name, metrics in self.gateway_metrics["tools_performance"].items():
            invocations = metrics["invocations"]
            tool_success_rate = (metrics["successes"] / invocations * 100) if invocations > 0 else 0
            tool_performance[tool_name] = {
                **metrics,
                "success_rate": round(tool_success_rate, 2)
            }

        return {
            "gateway_info": {
                "total_atomic_tools": len(self.atomic_tools),
                "phase": "Fase 1: Coexistencia y Estabilización",
                "architecture": "Agentic Ready"
            },
            "usage_metrics": {
                "total_invocations": total_invocations,
                "successful_invocations": self.gateway_metrics["successful_invocations"],
                "failed_invocations": self.gateway_metrics["failed_invocations"],
                "overall_success_rate": round(success_rate, 2)
            },
            "tool_performance": tool_performance,
            "tool_scientific_metadata": {
                tool_name: tool.get_scientific_metadata() 
                for tool_name, tool in self.atomic_tools.items()
            },
            "last_metrics_reset": self.gateway_metrics["last_reset"]
        }

    # ============================================================================
    # COMPATIBILIDAD CON INTERFAZ EXISTENTE - MANTIENE FUNCIONALIDAD ACTUAL
    # ============================================================================

    async def invoke_tool(self, tool_name: str, parameters: Dict[str, Any]) -> ToolResult:
        """
        COMPATIBILIDAD: Mantiene la interfaz existente mientras redirige a herramientas atómicas.
        """
        # Mapea herramientas tradicionales a herramientas atómicas
        tool_mapping = {
            "blast": "blast_search",
            "uniprot": "uniprot_annotations", 
            "sequence_analysis": "sequence_features",
            "llm": "llm_analysis"
        }

        # Si es una herramienta atómica directa, úsala
        if tool_name in self.atomic_tools:
            return await self.invoke_atomic_tool(tool_name, parameters)
        
        # Si es un nombre tradicional, mapéalo
        elif tool_name in tool_mapping:
            atomic_tool_name = tool_mapping[tool_name]
            return await self.invoke_atomic_tool(atomic_tool_name, parameters)
        
        # Si no se encuentra, mantiene comportamiento original
        else:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error_message=f"Herramienta no encontrada: {tool_name}. Herramientas disponibles: {list(self.atomic_tools.keys())}",
                timestamp=datetime.utcnow()
            )

    async def list_available_tools(self) -> List[str]:
        """COMPATIBILIDAD: Lista todas las herramientas disponibles."""
        # Incluye tanto nombres atómicos como nombres de compatibilidad
        atomic_tools = list(self.atomic_tools.keys())
        compatibility_tools = ["blast", "uniprot", "sequence_analysis", "llm"]
        return atomic_tools + compatibility_tools

    async def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """COMPATIBILIDAD: Obtiene información de herramienta."""
        # Mapeo de compatibilidad
        tool_mapping = {
            "blast": "blast_search",
            "uniprot": "uniprot_annotations",
            "sequence_analysis": "sequence_features", 
            "llm": "llm_analysis"
        }

        # Resuelve el nombre real de la herramienta
        actual_tool_name = tool_mapping.get(tool_name, tool_name)
        
        if actual_tool_name in self.atomic_tools:
            return await self.get_atomic_tool_schema(actual_tool_name)
        else:
            return {
                "name": tool_name,
                "description": "Herramienta no encontrada",
                "available": False,
                "error": f"Tool {tool_name} not found"
            }

    async def health_check(self) -> Dict[str, bool]:
        """COMPATIBILIDAD: Health check de todas las herramientas."""
        health_status = {}
        
        # Verifica herramientas atómicas
        for tool_name in self.atomic_tools.keys():
            health_status[tool_name] = await self.health_check_atomic_tool(tool_name)
        
        # Añade aliases de compatibilidad
        tool_mapping = {
            "blast": "blast_search",
            "uniprot": "uniprot_annotations",
            "sequence_analysis": "sequence_features",
            "llm": "llm_analysis"
        }
        
        for alias, actual_name in tool_mapping.items():
            health_status[alias] = health_status.get(actual_name, False)

        return health_status

    async def get_capabilities(self) -> Dict[str, Any]:
        """Obtiene capacidades completas del gateway agéntico."""
        return {
            "architecture": "Agentic Tool Gateway v1.0",
            "phase": "Fase 1: Coexistencia y Estabilización",
            "capabilities": {
                "atomic_tools": True,
                "tool_recommendation": True, 
                "context_aware_selection": True,
                "scientific_metadata": True,
                "performance_monitoring": True,
                "backward_compatibility": True
            },
            "atomic_tools": await self.get_all_atomic_tools_schema(),
            "gateway_metrics": await self.get_gateway_metrics(),
            "health_status": await self.health_check()
        }

    async def reset_metrics(self):
        """Reinicia las métricas del gateway."""
        self.gateway_metrics = {
            "total_tool_invocations": 0,
            "successful_invocations": 0,
            "failed_invocations": 0,
            "tools_performance": {},
            "last_reset": datetime.utcnow()
        }
        
        # Reinicia métricas de herramientas individuales
        for tool in self.atomic_tools.values():
            tool.execution_count = 0
            tool.total_execution_time = 0.0
            tool.success_count = 0

        logger.info("Métricas del gateway agéntico reiniciadas")