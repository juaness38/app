# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - SERVICIO DE MÉTRICAS
LUIS: Implementación usando Prometheus para observabilidad.
"""
import logging
from prometheus_client import Counter, Histogram, Gauge, REGISTRY
from src.services.interfaces import IMetricsService

class PrometheusMetricsService(IMetricsService):
    """
    LUIS: Implementación de métricas usando Prometheus.
    Estas métricas se expondrán en un endpoint /metrics.
    """
    
    def __init__(self):
        # Contadores de análisis
        self.analysis_started = Counter(
            "astroflora_analysis_started_total", 
            "Total de análisis iniciados"
        )
        self.analysis_completed = Counter(
            "astroflora_analysis_completed_total", 
            "Total de análisis completados"
        )
        self.analysis_failed = Counter(
            "astroflora_analysis_failed_total", 
            "Total de análisis fallidos"
        )
        
        # Métricas de cola y capacidad
        self.jobs_queued = Counter(
            "astroflora_jobs_queued_total", 
            "Total de trabajos encolados por alta carga"
        )
        self.current_capacity = Gauge(
            "astroflora_current_capacity", 
            "Capacidad actual del sistema"
        )
        
        # Métricas de duración
        self.analysis_duration = Histogram(
            "astroflora_analysis_duration_seconds", 
            "Duración de los análisis completados"
        )
        self.external_call_duration = Histogram(
            "astroflora_external_call_duration_seconds", 
            "Duración de llamadas a servicios externos", 
            ["service"]
        )
        
        # Métricas de fallos externos
        self.external_call_failures = Counter(
            "astroflora_external_call_failures_total", 
            "Fallos en llamadas a servicios externos", 
            ["service"]
        )
        
        # Métricas específicas del Driver IA
        self.driver_ia_invocations = Counter(
            "astroflora_driver_ia_invocations_total",
            "Total de invocaciones del Driver IA",
            ["protocol_type"]
        )
        
        # Métricas de herramientas
        self.tool_invocations = Counter(
            "astroflora_tool_invocations_total",
            "Total de invocaciones de herramientas",
            ["tool_name"]
        )
        self.tool_failures = Counter(
            "astroflora_tool_failures_total",
            "Total de fallos de herramientas",
            ["tool_name"]
        )
        
        logging.getLogger(__name__).info("Servicio de Métricas (Prometheus) inicializado.")

    def record_analysis_started(self) -> None:
        """Registra el inicio de un análisis."""
        self.analysis_started.inc()

    def record_analysis_completed(self, duration_s: float) -> None:
        """Registra la finalización exitosa de un análisis."""
        self.analysis_completed.inc()
        self.analysis_duration.observe(duration_s)

    def record_analysis_failed(self) -> None:
        """Registra el fallo de un análisis."""
        self.analysis_failed.inc()

    def record_job_queued(self) -> None:
        """Registra que un trabajo fue encolado."""
        self.jobs_queued.inc()

    def record_external_call(self, service_name: str, duration_s: float) -> None:
        """Registra una llamada exitosa a un servicio externo."""
        self.external_call_duration.labels(service=service_name).observe(duration_s)

    def record_external_call_failure(self, service_name: str) -> None:
        """Registra un fallo en una llamada a servicio externo."""
        self.external_call_failures.labels(service=service_name).inc()

    def record_driver_ia_invocation(self, protocol_type: str) -> None:
        """Registra una invocación del Driver IA."""
        self.driver_ia_invocations.labels(protocol_type=protocol_type).inc()
        
    def record_tool_invocation(self, tool_name: str) -> None:
        """Registra una invocación de herramienta."""
        self.tool_invocations.labels(tool_name=tool_name).inc()
        
    def record_tool_failure(self, tool_name: str) -> None:
        """Registra un fallo de herramienta."""
        self.tool_failures.labels(tool_name=tool_name).inc()
        
    def set_current_capacity(self, capacity: int) -> None:
        """Actualiza la capacidad actual del sistema."""
        self.current_capacity.set(capacity)