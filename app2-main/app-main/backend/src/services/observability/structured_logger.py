# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - SERVICIO DE LOGGING ESTRUCTURADO
Logging estructurado en formato JSON para observabilidad.
"""
import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from src.services.interfaces import IStructuredLogger
from src.models.analysis import StructuredLogEntry, MetricEntry

class StructuredJSONLogger(IStructuredLogger):
    """
    Logger estructurado que emite logs en formato JSON.
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"structured.{service_name}")
        
        # Configurar handler para JSON
        self._setup_json_handler()
        
    def _setup_json_handler(self):
        """Configura handler para logs JSON."""
        # Crear formatter personalizado para JSON
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "service": getattr(record, 'service', 'unknown'),
                    "event_type": getattr(record, 'event_type', 'general'),
                    "message": record.getMessage(),
                    "context_id": getattr(record, 'context_id', None),
                    "trace_id": getattr(record, 'trace_id', None),
                    "data": getattr(record, 'data', {})
                }
                return json.dumps(log_entry)
        
        # Añadir handler si no existe
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JSONFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_pipeline_step(
        self, 
        step_name: str, 
        context_id: str, 
        data: Dict[str, Any]
    ) -> None:
        """Registra un paso del pipeline."""
        extra = {
            'service': self.service_name,
            'event_type': 'pipeline_step',
            'context_id': context_id,
            'data': {
                'step_name': step_name,
                **data
            }
        }
        self.logger.info(f"Pipeline step completed: {step_name}", extra=extra)

    def log_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Registra un error con contexto."""
        extra = {
            'service': self.service_name,
            'event_type': 'error',
            'context_id': context.get('context_id'),
            'trace_id': context.get('trace_id'),
            'data': {
                'error_type': error.__class__.__name__,
                'error_message': str(error),
                **context
            }
        }
        self.logger.error(f"Error occurred: {error}", extra=extra)

    def log_metric(
        self, 
        metric_name: str, 
        value: float, 
        tags: Dict[str, str] = None
    ) -> None:
        """Registra una métrica."""
        extra = {
            'service': self.service_name,
            'event_type': 'metric',
            'data': {
                'metric_name': metric_name,
                'value': value,
                'tags': tags or {},
                'unit': tags.get('unit') if tags else None
            }
        }
        self.logger.info(f"Metric recorded: {metric_name}={value}", extra=extra)

    def log_service_event(
        self,
        event_type: str,
        message: str,
        context_id: Optional[str] = None,
        data: Dict[str, Any] = None
    ) -> None:
        """Registra un evento general del servicio."""
        extra = {
            'service': self.service_name,
            'event_type': event_type,
            'context_id': context_id,
            'data': data or {}
        }
        self.logger.info(message, extra=extra)

    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        context_id: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Registra métricas de rendimiento."""
        extra = {
            'service': self.service_name,
            'event_type': 'performance',
            'context_id': context_id,
            'data': {
                'operation': operation,
                'duration_ms': duration_ms,
                'metadata': metadata or {}
            }
        }
        self.logger.info(f"Performance: {operation} took {duration_ms:.2f}ms", extra=extra)

# Instancias globales para diferentes servicios
pipeline_logger = StructuredJSONLogger("pipeline")
orchestrator_logger = StructuredJSONLogger("orchestrator") 
driver_ia_logger = StructuredJSONLogger("driver_ia")
blast_logger = StructuredJSONLogger("blast")
uniprot_logger = StructuredJSONLogger("uniprot")
api_logger = StructuredJSONLogger("api")