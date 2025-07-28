# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - MODELOS DE DATOS MEJORADOS
LUIS: Modelos Pydantic completos con validaciones avanzadas.
"""
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Literal
from enum import Enum
from pydantic import BaseModel, Field, validator

# === ENUMS Y TIPOS ===
class AnalysisStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class PromptProtocolType(str, Enum):
    PROTEIN_FUNCTION_ANALYSIS = "PROTEIN_FUNCTION_ANALYSIS"
    SEQUENCE_ALIGNMENT = "SEQUENCE_ALIGNMENT"
    STRUCTURE_PREDICTION = "STRUCTURE_PREDICTION"
    DRUG_DESIGN = "DRUG_DESIGN"
    BIOREACTOR_OPTIMIZATION = "BIOREACTOR_OPTIMIZATION"
    PIPELINE_BATCH = "PIPELINE_BATCH"

class EventType(str, Enum):
    ANALYSIS_STARTED = "analysis_started"
    TOOL_CALLED = "tool_called"
    STEP_COMPLETED = "step_completed"
    ANALYSIS_COMPLETED = "analysis_completed"
    ERROR_OCCURRED = "error_occurred"

# === MODELOS BASE MEJORADOS ===
class SequenceData(BaseModel):
    """Datos de secuencia biológica con validación."""
    sequence: str = Field(..., min_length=10, description="Secuencia biológica")
    sequence_type: str = Field("protein", description="Tipo de secuencia")
    organism: Optional[str] = Field(None, description="Organismo origen")
    
    @validator('sequence')
    def validate_biological_sequence(cls, v, values):
        """Valida secuencias biológicas según el tipo."""
        sequence_type = values.get('sequence_type', 'protein')
        if sequence_type == 'protein':
            valid_chars = set('ACDEFGHIKLMNPQRSTVWY')
            if not set(v.upper()).issubset(valid_chars):
                raise ValueError('Invalid protein sequence characters')
        elif sequence_type == 'dna':
            valid_chars = set('ATCG')
            if not set(v.upper()).issubset(valid_chars):
                raise ValueError('Invalid DNA sequence characters')
        return v.upper()

class PipelineConfig(BaseModel):
    """Configuración tipada para el pipeline científico."""
    blast_database: str = Field("nr", description="Base de datos BLAST")
    evalue_threshold: float = Field(1e-10, ge=0, description="E-value threshold")
    max_target_seqs: int = Field(500, ge=1, le=1000, description="Máximo secuencias objetivo")
    uniprot_fields: List[str] = Field(default_factory=lambda: ["function", "pathway"], description="Campos UniProt")
    llm_analysis_depth: str = Field("detailed", regex="^(basic|detailed|comprehensive)$", description="Profundidad de análisis LLM")
    max_blast_hits: int = Field(50, ge=1, le=200, description="Máximo hits BLAST")
    llm_max_tokens: int = Field(1000, ge=100, le=4000, description="Máximo tokens LLM")
    uniprot_batch_size: int = Field(10, ge=1, le=50, description="Tamaño de lote UniProt")

class CacheableResult(BaseModel):
    """Base para resultados cacheables."""
    cache_key: str = Field(..., description="Clave de cache")
    cache_ttl: int = Field(3600, description="TTL en segundos")
    cached_at: Optional[datetime] = None
    
    def is_cache_valid(self) -> bool:
        """Verifica si el cache sigue siendo válido."""
        if not self.cached_at:
            return False
        return (datetime.utcnow() - self.cached_at).seconds < self.cache_ttl

class LLMUsage(BaseModel):
    """Tracking de uso y costos de LLM."""
    context_id: str
    model_used: str = Field(..., description="Modelo usado (gpt-4, gpt-3.5-turbo, etc)")
    prompt_tokens: int = Field(0, description="Tokens en el prompt")
    completion_tokens: int = Field(0, description="Tokens en la respuesta")
    total_tokens: int = Field(0, description="Total de tokens")
    estimated_cost_usd: float = Field(0.0, description="Costo estimado en USD")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AnalysisTemplate(BaseModel):
    """Plantilla predefinida para análisis."""
    template_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Nombre de la plantilla")
    description: str = Field(..., description="Descripción detallada")
    protocol_type: PromptProtocolType
    default_parameters: Dict[str, Any] = Field(default_factory=dict)
    estimated_duration_minutes: int = Field(30, description="Duración estimada")
    cost_tier: str = Field("medium", regex="^(low|medium|high)$")
    tags: List[str] = Field(default_factory=list)

class APIResponse(BaseModel):
    """Formato de respuesta estructurado para la API."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

# === MODELOS DE ANÁLISIS ===
class AnalysisRequest(BaseModel):
    """Solicitud de análisis científico."""
    context_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="ID del usuario")
    workspace_id: str = Field(..., description="ID del workspace")
    protocol_type: PromptProtocolType = Field(..., description="Tipo de protocolo")
    sequence_data: Optional[SequenceData] = Field(None, description="Datos de secuencia")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parámetros adicionales")
    config: PipelineConfig = Field(default_factory=PipelineConfig, description="Configuración del pipeline")
    priority: int = Field(1, ge=1, le=5, description="Prioridad del análisis")

class AnalysisContext(BaseModel):
    """Contexto completo de un análisis en curso."""
    context_id: str = Field(..., description="ID único del contexto")
    user_id: str = Field(..., description="ID del usuario")
    workspace_id: str = Field(..., description="ID del workspace")
    protocol_type: PromptProtocolType = Field(..., description="Tipo de protocolo")
    status: AnalysisStatus = Field(AnalysisStatus.QUEUED, description="Estado actual")
    sequence_data: Optional[SequenceData] = Field(None, description="Datos de secuencia")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parámetros")
    results: Optional[Dict[str, Any]] = Field(None, description="Resultados")
    progress: int = Field(0, ge=0, le=100, description="Progreso porcentual")
    current_step: Optional[str] = Field(None, description="Paso actual")
    error_message: Optional[str] = Field(None, description="Mensaje de error")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    duration_seconds: Optional[int] = Field(None, description="Duración en segundos")

class PromptNode(BaseModel):
    """Nodo individual en un protocolo de prompts."""
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = Field(..., description="Nombre de la herramienta")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list, description="IDs de nodos dependientes")
    retry_count: int = Field(0, description="Número de reintentos")
    max_retries: int = Field(3, description="Máximo número de reintentos")
    timeout_seconds: int = Field(300, description="Timeout en segundos")

class PromptProtocol(BaseModel):
    """Protocolo completo de análisis científico."""
    protocol_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    protocol_type: PromptProtocolType = Field(..., description="Tipo de protocolo")
    nodes: List[PromptNode] = Field(..., description="Lista de nodos del protocolo")
    config: PipelineConfig = Field(default_factory=PipelineConfig)
    created_by: str = Field("driver_ia", description="Creado por")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AnalysisEvent(BaseModel):
    """Evento en el historial de un análisis."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    context_id: str = Field(..., description="ID del contexto")
    event_type: EventType = Field(..., description="Tipo de evento")
    data: Dict[str, Any] = Field(default_factory=dict, description="Datos del evento")
    agent: str = Field(..., description="Agente que generó el evento")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    execution_time_ms: Optional[float] = Field(None, description="Tiempo de ejecución")

# === MODELOS DE RESULTADOS ===
class BlastResult(CacheableResult):
    """Resultado de análisis BLAST."""
    query_sequence: str = Field(..., description="Secuencia consultada")
    hits: List[Dict[str, Any]] = Field(default_factory=list, description="Hits encontrados")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Estadísticas")
    database_used: str = Field(..., description="Base de datos usada")

class UniProtResult(CacheableResult):
    """Resultado de consulta UniProt."""
    protein_ids: List[str] = Field(default_factory=list, description="IDs de proteínas")
    entries: List[Dict[str, Any]] = Field(default_factory=list, description="Entradas UniProt")
    fields_retrieved: List[str] = Field(default_factory=list, description="Campos obtenidos")

class LLMResult(BaseModel):
    """Resultado de análisis con LLM."""
    analysis: str = Field(..., description="Análisis generado")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="Puntuación de confianza")
    model_used: str = Field(..., description="Modelo LLM usado")
    usage: LLMUsage = Field(..., description="Información de uso")
    sources: List[str] = Field(default_factory=list, description="Fuentes usadas")

class PipelineResult(BaseModel):
    """Resultado completo del pipeline científico."""
    context_id: str = Field(..., description="ID del contexto")
    blast_result: Optional[BlastResult] = Field(None, description="Resultado BLAST")
    uniprot_result: Optional[UniProtResult] = Field(None, description="Resultado UniProt")
    llm_result: Optional[LLMResult] = Field(None, description="Resultado LLM")
    final_analysis: Optional[str] = Field(None, description="Análisis final")
    execution_summary: Dict[str, Any] = Field(default_factory=dict, description="Resumen de ejecución")

# === COST TRACKER ===
class CostTracker:
    """Calculador de costos de LLM."""
    PRICING = {
        "gpt-4": {"prompt": 0.03/1000, "completion": 0.06/1000},
        "gpt-3.5-turbo": {"prompt": 0.0015/1000, "completion": 0.002/1000},
        "gpt-4o": {"prompt": 0.005/1000, "completion": 0.015/1000}
    }
    
    @classmethod
    def calculate_cost(cls, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calcula el costo de uso del LLM."""
        if model not in cls.PRICING:
            return 0.0
        
        pricing = cls.PRICING[model]
        return (prompt_tokens * pricing["prompt"]) + (completion_tokens * pricing["completion"])

# === PLANTILLAS PREDEFINIDAS ===
ANALYSIS_TEMPLATES = {
    "protein_function": AnalysisTemplate(
        name="Protein Function Discovery",
        description="Análisis completo de función de proteína usando BLAST + UniProt + LLM",
        protocol_type=PromptProtocolType.PROTEIN_FUNCTION_ANALYSIS,
        default_parameters={
            "blast_database": "nr",
            "evalue_threshold": 1e-10,
            "max_blast_hits": 50,
            "uniprot_fields": ["function", "pathway", "domain"],
            "llm_analysis_depth": "detailed"
        },
        estimated_duration_minutes=45,
        cost_tier="medium",
        tags=["protein", "function", "annotation"]
    ),
    "sequence_alignment": AnalysisTemplate(
        name="Multiple Sequence Alignment",
        description="Alineamiento múltiple de secuencias con análisis de conservación",
        protocol_type=PromptProtocolType.SEQUENCE_ALIGNMENT,
        default_parameters={
            "alignment_method": "mafft",
            "gap_penalty": -10,
            "conservation_threshold": 0.8
        },
        estimated_duration_minutes=30,
        cost_tier="low",
        tags=["alignment", "conservation", "phylogeny"]
    )
}

# === QUERY MODELS ===
class AnalysisQuery(BaseModel):
    """Parámetros de búsqueda avanzada de análisis."""
    status: Optional[AnalysisStatus] = None
    protocol_type: Optional[PromptProtocolType] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)