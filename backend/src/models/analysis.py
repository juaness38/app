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
    """LUIS: Estados posibles de un análisis."""
    PENDING = "PENDING"
    QUEUED = "QUEUED"  
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class PromptProtocolType(str, Enum):
    """LUIS: Tipos de protocolos científicos disponibles."""
    PROTEIN_FUNCTION_ANALYSIS = "PROTEIN_FUNCTION_ANALYSIS"
    SEQUENCE_ALIGNMENT = "SEQUENCE_ALIGNMENT"
    STRUCTURE_PREDICTION = "STRUCTURE_PREDICTION"
    DRUG_DESIGN = "DRUG_DESIGN"
    BIOREACTOR_OPTIMIZATION = "BIOREACTOR_OPTIMIZATION"

class AnalysisRequest(BaseModel):
    """LUIS: Modelo para una nueva solicitud de análisis."""
    workspace_id: str = Field(..., description="ID del workspace")
    protocol_type: PromptProtocolType = Field(..., description="Tipo de protocolo a ejecutar")
    sequence: Optional[str] = Field(None, min_length=10, description="Secuencia biológica")
    target_protein: Optional[str] = Field(None, description="Proteína objetivo")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parámetros específicos")
    priority: int = Field(1, ge=1, le=5, description="Prioridad del análisis (1=alta, 5=baja)")

class AnalysisContext(BaseModel):
    """LUIS: Modelo que representa el estado de un análisis en curso."""
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
    
    model_config = ConfigDict(from_attributes=True)

class JobPayload(BaseModel):
    """LUIS: Payload que se envía a la cola SQS para procesamiento."""
    context_id: str
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    priority: int = Field(1, ge=1, le=5)
    
class PromptNode(BaseModel):
    """LUIS: Nodo individual de un Prompt Protocol."""
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Nombre del nodo")
    description: str = Field(..., description="Descripción del paso")
    tool_name: Optional[str] = Field(None, description="Herramienta a usar")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list, description="IDs de nodos dependientes")
    
class PromptProtocol(BaseModel):
    """LUIS: Protocolo científico completo con sus pasos."""
    protocol_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Nombre del protocolo")
    description: str = Field(..., description="Descripción del protocolo")
    protocol_type: PromptProtocolType
    nodes: List[PromptNode] = Field(..., description="Nodos del protocolo")
    version: str = Field("1.0", description="Versión del protocolo")
    
class ToolResult(BaseModel):
    """LUIS: Resultado de la ejecución de una herramienta."""
    tool_name: str
    success: bool
    result: Any = Field(None, description="Resultado de la herramienta")
    error_message: Optional[str] = None
    execution_time: float = Field(0.0, description="Tiempo de ejecución en segundos")
    
class EventStoreEntry(BaseModel):
    """LUIS: Entrada del EventStore para auditoría."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    context_id: str
    event_type: str = Field(..., description="Tipo de evento")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)
    agent: str = Field("system", description="Agente que generó el evento")