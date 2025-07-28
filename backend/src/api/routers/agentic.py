# -*- coding: utf-8 -*-
"""
ASTROFLORA - ENDPOINTS AGÉNTICOS
Nuevos endpoints para capacidades agénticas - Fase 1: Coexistencia y Estabilización.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from src.models.analysis import (
    EnhancedAnalysisTemplate, ENHANCED_ANALYSIS_TEMPLATES,
    EnhancedPipelineConfig, APIResponse, AnalysisDepth, CostTier
)
from src.api.dependencies import get_container
from src.container import AppContainer

router = APIRouter(tags=["Agentic Capabilities"])

# ============================================================================
# MODELOS DE REQUEST/RESPONSE PARA ENDPOINTS AGÉNTICOS
# ============================================================================

class ToolRecommendationRequest(BaseModel):
    """Request para recomendación de herramientas."""
    context: Dict[str, Any] = Field(..., description="Contexto para evaluación")
    min_score: float = Field(0.5, ge=0.0, le=1.0, description="Puntuación mínima")

class AtomicToolRequest(BaseModel):
    """Request para invocar herramienta atómica."""
    tool_name: str = Field(..., description="Nombre de la herramienta atómica")
    parameters: Dict[str, Any] = Field(..., description="Parámetros de la herramienta")

class PipelineConfigRequest(BaseModel):
    """Request para crear configuración de pipeline personalizada."""
    blast_database: str = Field("nr", description="Base de datos BLAST")
    evalue_threshold: float = Field(1e-10, ge=0, description="E-value threshold")
    max_target_seqs: int = Field(100, ge=1, le=1000, description="Máximo secuencias objetivo")
    uniprot_fields: List[str] = Field(["function", "pathway", "domain"], description="Campos UniProt")
    llm_analysis_depth: AnalysisDepth = Field(AnalysisDepth.DETAILED, description="Profundidad análisis LLM")
    llm_max_tokens: int = Field(1500, ge=100, le=4000, description="Máximo tokens LLM")
    llm_temperature: float = Field(0.3, ge=0, le=1, description="Temperatura LLM")
    max_concurrent_sequences: int = Field(5, ge=1, le=20, description="Secuencias concurrentes")
    enable_caching: bool = Field(True, description="Habilitar caching")

# ============================================================================
# ENDPOINTS - HERRAMIENTAS ATÓMICAS
# ============================================================================

@router.get("/tools/available", response_model=APIResponse)
async def get_available_atomic_tools(container: AppContainer = Depends(get_container)):
    """Obtiene lista de herramientas atómicas disponibles."""
    try:
        tools = await container.tool_gateway.get_available_atomic_tools()
        
        return APIResponse(
            success=True,
            data={
                "atomic_tools": tools,
                "total_count": len(tools),
                "architecture": "Agentic Tool Gateway v1.0",
                "phase": "Fase 1: Coexistencia y Estabilización"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo herramientas atómicas: {str(e)}"
        )

@router.get("/tools/{tool_name}/schema", response_model=APIResponse)
async def get_atomic_tool_schema(tool_name: str, container: AppContainer = Depends(get_container)):
    """Obtiene schema y metadatos de una herramienta atómica específica."""
    try:
        schema = await container.tool_gateway.get_atomic_tool_schema(tool_name)
        
        return APIResponse(
            success=True,
            data=schema
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo schema de herramienta: {str(e)}"
        )

@router.get("/tools/schemas/all", response_model=APIResponse)
async def get_all_atomic_tools_schemas(container: AppContainer = Depends(get_container)):
    """Obtiene schemas de todas las herramientas atómicas."""
    try:
        schemas = await container.tool_gateway.get_all_atomic_tools_schema()
        
        return APIResponse(
            success=True,
            data={
                "tools_schemas": schemas,
                "total_tools": len(schemas)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo schemas: {str(e)}"
        )

@router.post("/tools/invoke", response_model=APIResponse)
async def invoke_atomic_tool(
    request: AtomicToolRequest,
    container: AppContainer = Depends(get_container)
):
    """Invoca una herramienta atómica específica."""
    try:
        result = await container.tool_gateway.invoke_atomic_tool(
            request.tool_name,
            request.parameters
        )
        
        return APIResponse(
            success=result.success,
            data=result.dict(),
            error=result.error_message if not result.success else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error invocando herramienta atómica: {str(e)}"
        )

@router.post("/tools/recommend", response_model=APIResponse)
async def recommend_tools_for_context(
    request: ToolRecommendationRequest,
    container: AppContainer = Depends(get_container)
):
    """Recomienda herramientas apropiadas para un contexto específico."""
    try:
        recommendations = await container.tool_gateway.recommend_tools_for_context(
            request.context,
            request.min_score
        )
        
        return APIResponse(
            success=True,
            data={
                "recommendations": recommendations,
                "total_recommendations": len(recommendations),
                "context_analyzed": request.context,
                "min_score_used": request.min_score
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando recomendaciones: {str(e)}"
        )

@router.get("/tools/health", response_model=APIResponse)
async def check_atomic_tools_health(container: AppContainer = Depends(get_container)):
    """Verifica salud de todas las herramientas atómicas."""
    try:
        health_status = {}
        tools = await container.tool_gateway.get_available_atomic_tools()
        
        for tool_name in tools:
            health_status[tool_name] = await container.tool_gateway.health_check_atomic_tool(tool_name)
        
        healthy_tools = sum(1 for status in health_status.values() if status)
        
        return APIResponse(
            success=True,
            data={
                "health_status": health_status,
                "healthy_tools": healthy_tools,
                "total_tools": len(tools),
                "overall_health": "healthy" if healthy_tools == len(tools) else "degraded"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verificando salud de herramientas: {str(e)}"
        )

# ============================================================================
# ENDPOINTS - PLANTILLAS Y CONFIGURACIÓN
# ============================================================================

@router.get("/templates/available", response_model=APIResponse)
async def get_available_templates():
    """Obtiene plantillas de análisis disponibles."""
    try:
        templates = {
            template_id: template.dict()
            for template_id, template in ENHANCED_ANALYSIS_TEMPLATES.items()
        }
        
        return APIResponse(
            success=True,
            data={
                "templates": templates,
                "total_count": len(templates),
                "available_depths": [depth.value for depth in AnalysisDepth],
                "available_cost_tiers": [tier.value for tier in CostTier]
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo plantillas: {str(e)}"
        )

@router.get("/templates/{template_id}", response_model=APIResponse)
async def get_template_by_id(template_id: str):
    """Obtiene una plantilla específica por ID."""
    try:
        if template_id not in ENHANCED_ANALYSIS_TEMPLATES:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plantilla no encontrada: {template_id}"
            )
        
        template = ENHANCED_ANALYSIS_TEMPLATES[template_id]
        
        return APIResponse(
            success=True,
            data=template.dict()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo plantilla: {str(e)}"
        )

@router.post("/config/validate", response_model=APIResponse)
async def validate_pipeline_config(request: PipelineConfigRequest):
    """Valida una configuración de pipeline personalizada."""
    try:
        # Crea la configuración para validar
        config = EnhancedPipelineConfig(
            blast_database=request.blast_database,
            evalue_threshold=request.evalue_threshold,
            max_target_seqs=request.max_target_seqs,
            uniprot_fields=request.uniprot_fields,
            llm_analysis_depth=request.llm_analysis_depth,
            llm_max_tokens=request.llm_max_tokens,
            llm_temperature=request.llm_temperature,
            max_concurrent_sequences=request.max_concurrent_sequences,
            enable_caching=request.enable_caching
        )
        
        return APIResponse(
            success=True,
            data={
                "config": config.dict(),
                "validation_status": "valid",
                "estimated_cost_tier": _estimate_cost_tier(config),
                "estimated_duration_minutes": _estimate_duration(config)
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuración inválida: {str(e)}"
        )

# ============================================================================
# ENDPOINTS - MÉTRICAS Y CAPACIDADES
# ============================================================================

@router.get("/metrics/gateway", response_model=APIResponse)
async def get_gateway_metrics(container: AppContainer = Depends(get_container)):
    """Obtiene métricas del gateway agéntico."""
    try:
        metrics = await container.tool_gateway.get_gateway_metrics()
        
        return APIResponse(
            success=True,
            data=metrics
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo métricas: {str(e)}"
        )

@router.get("/capabilities", response_model=APIResponse)
async def get_agentic_capabilities(container: AppContainer = Depends(get_container)):
    """Obtiene capacidades completas del sistema agéntico."""
    try:
        capabilities = await container.tool_gateway.get_capabilities()
        
        # Añade información del pipeline
        pipeline_status = await container.pipeline_service.get_pipeline_status()
        
        return APIResponse(
            success=True,
            data={
                "system_info": {
                    "name": "Astroflora Agentic System",
                    "version": "1.0.0",
                    "phase": "Fase 1: Coexistencia y Estabilización",
                    "architecture": "Enhanced Scientific Pipeline + Atomic Tools"
                },
                "tool_gateway": capabilities,
                "pipeline_status": pipeline_status,
                "available_templates": len(ENHANCED_ANALYSIS_TEMPLATES),
                "supported_analysis_depths": [depth.value for depth in AnalysisDepth],
                "supported_cost_tiers": [tier.value for tier in CostTier]
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo capacidades: {str(e)}"
        )

@router.post("/metrics/reset", response_model=APIResponse)
async def reset_gateway_metrics(container: AppContainer = Depends(get_container)):
    """Reinicia las métricas del gateway agéntico."""
    try:
        await container.tool_gateway.reset_metrics()
        
        return APIResponse(
            success=True,
            data={
                "message": "Métricas del gateway agéntico reiniciadas exitosamente",
                "reset_timestamp": container.tool_gateway.gateway_metrics["last_reset"]
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reiniciando métricas: {str(e)}"
        )

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def _estimate_cost_tier(config: EnhancedPipelineConfig) -> str:
    """Estima el nivel de costo basado en la configuración."""
    cost_factors = 0
    
    # Factores que aumentan el costo
    if config.max_target_seqs > 100:
        cost_factors += 1
    if config.llm_max_tokens > 2000:
        cost_factors += 1
    if config.llm_analysis_depth == AnalysisDepth.COMPREHENSIVE:
        cost_factors += 2
    elif config.llm_analysis_depth == AnalysisDepth.DETAILED:
        cost_factors += 1
    if config.max_concurrent_sequences > 10:
        cost_factors += 1
    if not config.enable_caching:
        cost_factors += 1
    
    if cost_factors >= 4:
        return CostTier.HIGH.value
    elif cost_factors >= 2:
        return CostTier.MEDIUM.value
    else:
        return CostTier.LOW.value

def _estimate_duration(config: EnhancedPipelineConfig) -> int:
    """Estima la duración en minutos basada en la configuración."""
    base_duration = 30
    
    # Ajustes basados en configuración
    if config.llm_analysis_depth == AnalysisDepth.COMPREHENSIVE:
        base_duration *= 2
    elif config.llm_analysis_depth == AnalysisDepth.DETAILED:
        base_duration *= 1.5
    
    if config.max_target_seqs > 200:
        base_duration *= 1.3
    
    if not config.enable_caching:
        base_duration *= 1.2
    
    return int(base_duration)