# -*- coding: utf-8 -*-
"""
ASTROFLORA - MODELOS DE ANÁLISIS CIENTÍFICO
Modelos Pydantic para análisis bioinformático integrado con PostgreSQL
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from datetime import datetime
import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from src.models.orm import Base

# ============================================================================
# ENUMS Y TIPOS
# ============================================================================

class AnalysisStatus(str, Enum):
    """Estados de un análisis científico."""
    PENDING = "PENDING"
    QUEUED = "QUEUED"  
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class PromptProtocolType(str, Enum):
    """Tipos de análisis científicos disponibles."""
    PROTEIN_FUNCTION_ANALYSIS = "PROTEIN_FUNCTION_ANALYSIS"
    SEQUENCE_ALIGNMENT = "SEQUENCE_ALIGNMENT"
    STRUCTURE_PREDICTION = "STRUCTURE_PREDICTION"
    DRUG_DESIGN = "DRUG_DESIGN"
    BIOREACTOR_OPTIMIZATION = "BIOREACTOR_OPTIMIZATION"
    PIPELINE_BATCH = "PIPELINE_BATCH"

# ============================================================================
# MODELOS PYDANTIC PARA API
# ============================================================================

class AnalysisRequest(BaseModel):
    """Solicitud de análisis científico."""
    workspace_id: str = Field(..., description="ID del workspace")
    protocol_type: PromptProtocolType = Field(..., description="Tipo de análisis")
    sequence: Optional[str] = Field(None, min_length=10, description="Secuencia biológica")
    target_protein: Optional[str] = Field(None, description="Proteína objetivo")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parámetros específicos")
    priority: int = Field(1, ge=1, le=5, description="Prioridad (1=alta, 5=baja)")
    
    # Para análisis batch
    sequences: Optional[List['SequenceData']] = Field(None, description="Lista de secuencias")
    batch_size: Optional[int] = Field(None, ge=1, le=100, description="Tamaño del lote")

class AnalysisContext(BaseModel):
    """Estado de un análisis científico."""
    model_config = ConfigDict(from_attributes=True)
    
    context_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: AnalysisStatus = Field(default=AnalysisStatus.PENDING)
    workspace_id: str
    user_id: str
    protocol_type: PromptProtocolType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    progress: int = Field(0, ge=0, le=100, description="Progreso 0-100%")
    current_step: Optional[str] = Field(None, description="Paso actual")
    results: Dict[str, Any] = Field(default_factory=dict, description="Resultados")
    error_message: Optional[str] = Field(None, description="Mensaje de error")
    request_data: Dict[str, Any] = Field(default_factory=dict, description="Datos de la solicitud")
    
    def to_analysis_request(self) -> AnalysisRequest:
        """Convierte a AnalysisRequest."""
        return AnalysisRequest(
            workspace_id=self.workspace_id,
            protocol_type=self.protocol_type,
            **self.request_data
        )

class JobPayload(BaseModel):
    """Payload para trabajos en cola."""
    context_id: str
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    priority: int = Field(1, ge=1, le=5)
    job_type: str = Field("analysis", description="Tipo de trabajo")
    sequences: Optional[List['SequenceData']] = Field(None, description="Secuencias para batch")

class SequenceData(BaseModel):
    """Datos de secuencia biológica."""
    id: str = Field(..., description="ID único")
    sequence: str = Field(..., min_length=10, description="Secuencia")
    sequence_type: Optional[str] = Field(None, description="Tipo: DNA, RNA, protein")
    description: Optional[str] = Field(None, description="Descripción")
    organism: Optional[str] = Field(None, description="Organismo")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolResult(BaseModel):
    """Resultado de herramienta bioinformática."""
    tool_name: str
    success: bool
    result: Any = Field(None, description="Resultado de la herramienta")
    error_message: Optional[str] = None
    execution_time: float = Field(0.0, description="Tiempo de ejecución")

class BlastResult(BaseModel):
    """Resultado de búsqueda BLAST."""
    query_sequence: str
    query_length: int
    database: str
    total_hits: int
    hits: List[Dict[str, Any]]
    search_time: float
    parameters: Dict[str, Any] = Field(default_factory=dict)

class UniProtResult(BaseModel):
    """Resultado de consulta UniProt."""
    query_ids: List[str]
    total_found: int
    annotations: List[Dict[str, Any]]
    search_time: float
    database_version: str

class EventStoreEntry(BaseModel):
    """Entrada del Event Store."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    context_id: str
    event_type: str = Field(..., description="Tipo de evento")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    agent: str = Field("system", description="Agente generador")

class PromptNode(BaseModel):
    """Nodo de protocolo científico."""
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Nombre del nodo")
    description: str = Field(..., description="Descripción")
    tool_name: Optional[str] = Field(None, description="Herramienta a usar")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)

class PromptProtocol(BaseModel):
    """Protocolo científico completo."""
    protocol_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Nombre del protocolo")
    description: str = Field(..., description="Descripción")
    protocol_type: PromptProtocolType
    nodes: List[PromptNode] = Field(..., description="Nodos del protocolo")
    version: str = Field("1.0")

# ============================================================================
# MODELOS SQLALCHEMY PARA POSTGRESQL
# ============================================================================

class AnalysisContextORM(Base):
    """Contexto de análisis en PostgreSQL."""
    __tablename__ = "analysis_contexts"

    context_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(50), nullable=False, default="PENDING")
    workspace_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    protocol_type = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    progress = Column(Integer, nullable=False, default=0)
    current_step = Column(String(500), nullable=True)
    results = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    request_data = Column(JSON, nullable=True)

class EventStoreORM(Base):
    """Event Store en PostgreSQL."""
    __tablename__ = "event_store"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    context_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    data = Column(JSON, nullable=True)
    agent = Column(String(100), nullable=False, default="system")

class SequenceDataORM(Base):
    """Datos de secuencias en PostgreSQL."""
    __tablename__ = "sequence_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sequence_id = Column(String(255), nullable=False, unique=True, index=True)
    sequence = Column(Text, nullable=False)
    sequence_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    organism = Column(String(255), nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

# ============================================================================
# RESPUESTAS API
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Respuesta de health check."""
    service: str = Field(..., description="Nombre del servicio")
    status: str = Field(..., description="Estado: healthy, unhealthy")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)
    dependencies: Dict[str, str] = Field(default_factory=dict)

class SystemStatsResponse(BaseModel):
    """Estadísticas del sistema."""
    active_analyses: int
    completed_analyses: int
    failed_analyses: int
    queue_size: int
    capacity_utilization: float
    uptime_seconds: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)