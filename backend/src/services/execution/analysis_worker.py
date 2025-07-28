# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - ANALYSIS WORKER MEJORADO
LUIS: Worker con circuit breakers, retry logic y monitoreo de recursos.
"""
import asyncio
import psutil
import logging
import time
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime

from src.services.interfaces import (
    IAnalysisWorker, IDriverIA, IContextManager, 
    ICapacityManager, IEventStore
)
from src.models.analysis import (
    AnalysisContext, AnalysisStatus, AnalysisEvent, 
    EventType, PromptProtocol
)
from src.core.exceptions import (
    AstrofloraException, CapacityExceededException,
    CircuitBreakerOpenException
)

logger = logging.getLogger(__name__)

class AnalysisWorker(IAnalysisWorker):
    """LUIS: Worker mejorado con resiliencia avanzada."""
    
    def __init__(
        self,
        driver_ia: IDriverIA,
        context_manager: IContextManager,
        capacity_manager: ICapacityManager,
        event_store: IEventStore
    ):
        """LUIS: Inicializa el worker con dependencias mejoradas."""
        self.driver_ia = driver_ia
        self.context_manager = context_manager
        self.capacity_manager = capacity_manager
        self.event_store = event_store
        self.logger = logger
        self.is_running = False
        self.current_jobs = 0
        self.total_processed = 0
        self.start_time = datetime.utcnow()
        
    async def process_analysis(self, context_id: str) -> None:
        """LUIS: Procesa un análisis con manejo mejorado de errores."""
        start_time = time.time()
        
        try:
            # Incrementa contador de trabajos
            self.current_jobs += 1
            
            # Verifica disponibilidad de recursos
            await self._check_resource_usage()
            
            # Obtiene contexto del análisis
            context = await self.context_manager.get_context(context_id)
            if not context:
                raise AstrofloraException(f"Context {context_id} not found")
            
            # Log inicio del análisis
            await self._log_event(
                context_id,
                EventType.ANALYSIS_STARTED,
                {"worker_pid": psutil.Process().pid},
                agent="analysis_worker"
            )
            
            # Actualiza estado a PROCESSING
            await self.context_manager.update_context(
                context_id,
                {"status": AnalysisStatus.PROCESSING, "current_step": "initializing"}
            )
            
            # Procesa con retry y circuit breaker
            result = await self._execute_with_retry(
                self._process_analysis_safely,
                context_id,
                context
            )
            
            # Marca como completado
            await self.context_manager.update_context(
                context_id,
                {
                    "status": AnalysisStatus.COMPLETED,
                    "results": result,
                    "completed_at": datetime.utcnow(),
                    "duration_seconds": int(time.time() - start_time)
                }
            )
            
            await self._log_event(
                context_id,
                EventType.ANALYSIS_COMPLETED,
                {"duration_seconds": int(time.time() - start_time)},
                agent="analysis_worker"
            )
            
            self.total_processed += 1
            
        except Exception as e:
            self.logger.error(f"Error processing analysis {context_id}: {e}")
            
            # Marca como fallido
            await self.context_manager.update_context(
                context_id,
                {
                    "status": AnalysisStatus.FAILED,
                    "error_message": str(e),
                    "completed_at": datetime.utcnow(),
                    "duration_seconds": int(time.time() - start_time)
                }
            )
            
            await self._log_event(
                context_id,
                EventType.ERROR_OCCURRED,
                {"error": str(e), "error_type": e.__class__.__name__},
                agent="analysis_worker"
            )
            
        finally:
            # Decrementa contador de trabajos
            self.current_jobs = max(0, self.current_jobs - 1)
            
            # Libera capacidad
            await self.capacity_manager.release_capacity(context_id)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _execute_with_retry(self, operation, *args):
        """LUIS: Ejecuta operaciones con retry exponencial."""
        return await operation(*args)

    async def _process_analysis_safely(self, context_id: str, context: AnalysisContext) -> Dict[str, Any]:
        """LUIS: Procesa análisis con circuit breaker para DriverIA."""
        try:
            # Llama al DriverIA con circuit breaker
            result = await self._call_driver_ia_safely(
                self.driver_ia.execute_prompt_protocol,
                context
            )
            
            return result
            
        except CircuitBreakerOpenException:
            self.logger.warning(f"Circuit breaker open for DriverIA on context {context_id}")
            raise
        except Exception as e:
            self.logger.error(f"Error in safe analysis processing: {e}")
            raise

    async def _call_driver_ia_safely(self, method, *args):
        """LUIS: Llama al DriverIA con circuit breaker."""
        # Implementación simplificada - en producción usar circuit breaker real
        try:
            return await method(*args)
        except Exception as e:
            # Aquí se implementaría el circuit breaker real
            self.logger.error(f"DriverIA call failed: {e}")
            raise

    async def _check_resource_usage(self) -> None:
        """LUIS: Monitoreo de recursos del sistema."""
        try:
            # Verifica memoria
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > 80:
                self.logger.warning(f"High memory usage: {memory_percent}%")
                await self._trigger_cleanup()
            
            # Verifica CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                self.logger.warning(f"High CPU usage: {cpu_percent}%")
                # Pausa breve para reducir carga
                await asyncio.sleep(2)
            
        except Exception as e:
            self.logger.error(f"Error checking resource usage: {e}")

    async def _trigger_cleanup(self) -> None:
        """LUIS: Limpieza de recursos cuando hay alta utilización."""
        try:
            # Fuerza garbage collection
            import gc
            gc.collect()
            
            # Log acción de limpieza
            self.logger.info("Resource cleanup triggered due to high memory usage")
            
        except Exception as e:
            self.logger.error(f"Error in resource cleanup: {e}")

    async def _log_event(
        self, 
        context_id: str, 
        event_type: EventType, 
        data: Dict[str, Any],
        agent: str = "analysis_worker"
    ) -> None:
        """LUIS: Log de eventos mejorado."""
        try:
            event = AnalysisEvent(
                context_id=context_id,
                event_type=event_type,
                data=data,
                agent=agent
            )
            
            await self.event_store.store_event(event)
            
        except Exception as e:
            self.logger.error(f"Error logging event: {e}")

    async def health_check(self) -> bool:
        """LUIS: Verifica salud del worker."""
        try:
            # Verifica que los servicios dependientes estén funcionando
            driver_health = await self.driver_ia.health_check()
            
            # Verifica recursos del sistema
            memory_percent = psutil.virtual_memory().percent
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Worker está saludable si:
            # - DriverIA funciona
            # - Memoria < 90%
            # - CPU < 95%
            is_healthy = (
                driver_health and 
                memory_percent < 90 and 
                cpu_percent < 95
            )
            
            return is_healthy
            
        except Exception as e:
            self.logger.error(f"Error in worker health check: {e}")
            return False

    async def get_worker_stats(self) -> Dict[str, Any]:
        """LUIS: Estadísticas completas del worker."""
        try:
            current_time = datetime.utcnow()
            uptime_seconds = (current_time - self.start_time).total_seconds()
            
            # Estadísticas del sistema
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            stats = {
                "worker_status": {
                    "is_running": self.is_running,
                    "current_jobs": self.current_jobs,
                    "total_processed": self.total_processed,
                    "uptime_seconds": int(uptime_seconds),
                    "start_time": self.start_time.isoformat()
                },
                "system_resources": {
                    "memory_total_gb": round(memory.total / (1024**3), 2),
                    "memory_used_gb": round(memory.used / (1024**3), 2),
                    "memory_percent": memory.percent,
                    "cpu_percent": cpu_percent,
                    "available_cpu_count": psutil.cpu_count()
                },
                "performance": {
                    "avg_processing_time": 0,  # Se calcularía con métricas históricas
                    "success_rate": 0,  # Se calcularía con métricas históricas
                    "jobs_per_hour": round(self.total_processed / max(uptime_seconds / 3600, 0.1), 2)
                }
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting worker stats: {e}")
            return {"error": str(e)}

    async def start(self) -> None:
        """LUIS: Inicia el worker."""
        self.is_running = True
        self.start_time = datetime.utcnow()
        self.logger.info("Analysis Worker started")

    async def stop(self) -> None:
        """LUIS: Detiene el worker de forma limpia."""
        self.is_running = False
        
        # Espera a que terminen los trabajos actuales
        while self.current_jobs > 0:
            self.logger.info(f"Waiting for {self.current_jobs} jobs to complete...")
            await asyncio.sleep(1)
        
        self.logger.info("Analysis Worker stopped cleanly")

    async def shutdown(self) -> None:
        """LUIS: Cierre completo del worker."""
        await self.stop()
        self.logger.info("Analysis Worker shutdown complete")