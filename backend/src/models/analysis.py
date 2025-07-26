# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - MODELOS DE DATOS
LUIS: Contratos de datos (DTOs) que fluyen por el sistema.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime
import uuid

class AnalysisStatus(str, Enum):
    """Estados posibles de un análisis."""
    PENDING = "PENDING"
    QUEUED = "QUEUED"  
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class PromptProtocolType(str, Enum):
    """Tipos de protocolos científicos disponibles."""
    PROTEIN_FUNCTION_ANALYSIS = "PROTEIN_FUNCTION_ANALYSIS"
    SEQUENCE_ALIGNMENT = "SEQUENCE_ALIGNMENT"
    STRUCTURE_PREDICTION = "STRUCTURE_PREDICTION"
    DRUG_DESIGN = "DRUG_DESIGN"
    BIOREACTOR_OPTIMIZATION = "BIOREACTOR_OPTIMIZATION"
    PIPELINE_BATCH = "PIPELINE_BATCH"  # Nuevo tipo para pipeline batch

# ============================================================================
# MODELOS ESPECÍFICOS PARA PIPELINE CIENTÍFICO
# ============================================================================

class SequenceData(BaseModel):
    """Modelo para datos de secuencia biológica."""
    id: str = Field(..., description="Identificador único de la secuencia")
    sequence: str = Field(..., min_length=10, description="Secuencia biológica")
    sequence_type: Optional[str] = Field(None, description="Tipo: DNA, RNA, protein")
    description: Optional[str] = Field(None, description="Descripción de la secuencia")
    organism: Optional[str] = Field(None, description="Organismo de origen")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")

class BlastResult(BaseModel):
    """Resultado de búsqueda BLAST."""
    query_sequence: str = Field(..., description="Secuencia consultada")
    query_length: int = Field(..., description="Longitud de la secuencia")
    database: str = Field(..., description="Base de datos consultada")
    total_hits: int = Field(..., description="Número total de hits")
    hits: List[Dict[str, Any]] = Field(..., description="Lista de hits encontrados")
    search_time: float = Field(..., description="Tiempo de búsqueda en segundos")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parámetros de búsqueda")

class UniProtResult(BaseModel):
    """Resultado de consulta UniProt."""
    query_ids: List[str] = Field(..., description="IDs de proteínas consultadas")
    total_found: int = Field(..., description="Número de anotaciones encontradas")
    annotations: List[Dict[str, Any]] = Field(..., description="Anotaciones obtenidas")
    search_time: float = Field(..., description="Tiempo de consulta en segundos")
    database_version: str = Field(..., description="Versión de la base de datos")

class LLMResult(BaseModel):
    """Resultado de análisis con LLM."""
    prompt: str = Field(..., description="Prompt utilizado")
    response: Dict[str, Any] = Field(..., description="Respuesta del LLM")
    model_used: str = Field(..., description="Modelo de LLM utilizado")
    tokens_used: int = Field(0, description="Tokens consumidos")
    processing_time: float = Field(..., description="Tiempo de procesamiento")

class PipelineResult(BaseModel):
    """Resultado completo del pipeline para una secuencia."""
    sequence_id: str = Field(..., description="ID de la secuencia procesada")
    success: bool = Field(..., description="Éxito del pipeline")
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="Pasos ejecutados")
    processing_time: float = Field(..., description="Tiempo total de procesamiento")
    final_result: Optional[Dict[str, Any]] = Field(None, description="Resultado final")
    error: Optional[str] = Field(None, description="Mensaje de error si falló")

# ============================================================================
# MODELOS EXISTENTES ACTUALIZADOS
# ============================================================================

class AnalysisRequest(BaseModel):
    """Modelo para una nueva solicitud de análisis."""
    workspace_id: str = Field(..., description="ID del workspace")
    protocol_type: PromptProtocolType = Field(..., description="Tipo de protocolo a ejecutar")
    sequence: Optional[str] = Field(None, min_length=10, description="Secuencia biológica")
    target_protein: Optional[str] = Field(None, description="Proteína objetivo")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parámetros específicos")
    priority: int = Field(1, ge=1, le=5, description="Prioridad del análisis (1=alta, 5=baja)")
    
    # Campos específicos para pipeline batch
    sequences: Optional[List[SequenceData]] = Field(None, description="Lista de secuencias para batch")
    batch_size: Optional[int] = Field(None, ge=1, le=100, description="Tamaño del lote")

class AnalysisContext(BaseModel):
    """Modelo que representa el estado de un análisis en curso."""
    context_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: AnalysisStatus = Field(default=AnalysisStatus.PENDING)
    workspace_id: str
    user_id: str
    protocol_type: PromptProtocolType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    progress: int = Field(0, ge=0, le=100, description="Progreso del análisis (0-100)")
    current_step: Optional[str] = Field(None, description="Paso actual del protocolo")
    results: Dict[str, Any] = Field(default_factory=dict, description="Resultados del análisis")
    error_message: Optional[str] = Field(None, description="Mensaje de error si falló")
    
    # Campos específicos para pipeline batch
    batch_info: Optional[Dict[str, Any]] = Field(None, description="Información del lote si aplica")
    
    model_config = ConfigDict(from_attributes=True)

class JobPayload(BaseModel):
    """Payload que se envía a la cola SQS para procesamiento."""
    context_id: str
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    priority: int = Field(1, ge=1, le=5)
    job_type: str = Field("analysis", description="Tipo de trabajo: analysis, pipeline_batch")
    
class PromptNode(BaseModel):
    """Nodo individual de un Prompt Protocol."""
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Nombre del nodo")
    description: str = Field(..., description="Descripción del paso")
    tool_name: Optional[str] = Field(None, description="Herramienta a usar")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list, description="IDs de nodos dependientes")
    
class PromptProtocol(BaseModel):
    """Protocolo científico completo con sus pasos."""
    protocol_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Nombre del protocolo")
    description: str = Field(..., description="Descripción del protocolo")
    protocol_type: PromptProtocolType
    nodes: List[PromptNode] = Field(..., description="Nodos del protocolo")
    version: str = Field("1.0", description="Versión del protocolo")
    
class ToolResult(BaseModel):
    """Resultado de la ejecución de una herramienta."""
    tool_name: str
    success: bool
    result: Any = Field(None, description="Resultado de la herramienta")
    error_message: Optional[str] = None
    execution_time: float = Field(0.0, description="Tiempo de ejecución en segundos")
    
class EventStoreEntry(BaseModel):
    """Entrada del EventStore para auditoría."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    context_id: str
    event_type: str = Field(..., description="Tipo de evento")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    agent: str = Field("system", description="Agente que generó el evento")

# ============================================================================
# MODELOS PARA LOGGING ESTRUCTURADO
# ============================================================================

class StructuredLogEntry(BaseModel):
    """Entrada de log estructurada."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str = Field(..., description="Nivel de log: INFO, WARNING, ERROR")
    service: str = Field(..., description="Servicio que genera el log")
    event_type: str = Field(..., description="Tipo de evento")
    context_id: Optional[str] = Field(None, description="ID de contexto si aplica")
    message: str = Field(..., description="Mensaje del log")
    data: Dict[str, Any] = Field(default_factory=dict, description="Datos adicionales")
    trace_id: Optional[str] = Field(None, description="ID de traza distribuida")

class MetricEntry(BaseModel):
    """Entrada de métrica."""
    metric_name: str = Field(..., description="Nombre de la métrica")
    value: float = Field(..., description="Valor de la métrica")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = Field(default_factory=dict, description="Tags adicionales")
    unit: Optional[str] = Field(None, description="Unidad de medida")

# ============================================================================
# MODELOS DE RESPUESTA PARA API
# ============================================================================

class PipelineBatchRequest(BaseModel):
    """Solicitud para ejecutar pipeline en lote."""
    sequences: List[SequenceData] = Field(..., description="Lista de secuencias a procesar")
    pipeline_config: Dict[str, Any] = Field(default_factory=dict, description="Configuración del pipeline")
    notification_webhook: Optional[str] = Field(None, description="URL para notificaciones")

class PipelineBatchResponse(BaseModel):
    """Respuesta del pipeline en lote."""
    batch_id: str = Field(..., description="ID del lote procesado")
    total_sequences: int = Field(..., description="Total de secuencias procesadas")
    successful: int = Field(..., description="Secuencias procesadas exitosamente")
    failed: int = Field(..., description="Secuencias que fallaron")
    total_processing_time: float = Field(..., description="Tiempo total de procesamiento")
    average_time_per_sequence: float = Field(..., description="Tiempo promedio por secuencia")
    results: List[Dict[str, Any]] = Field(..., description="Resultados detallados")

class HealthCheckResponse(BaseModel):
    """Respuesta de health check."""
    service: str = Field(..., description="Nombre del servicio")
    status: str = Field(..., description="Estado: healthy, unhealthy, degraded")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict, description="Detalles adicionales")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Estado de dependencias")