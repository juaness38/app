# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - INTELLIGENT ORCHESTRATOR
LUIS: El cerebro orquestador. Gestiona el flujo de análisis.
"""
import logging
import uuid
from typing import Optional
from datetime import datetime
from src.services.interfaces import (
    IOrchestrator, IContextManager, ICapacityManager, ISQSDispatcher, 
    IEventStore, IMetricsService
)
from src.models.analysis import (
    AnalysisRequest, AnalysisContext, JobPayload, AnalysisStatus, EventStoreEntry
)
from src.core.exceptions import ServiceUnavailableException, AnalysisNotFoundException

class IntelligentOrchestrator(IOrchestrator):
    """
    LUIS: El cerebro orquestador. No contiene lógica de bajo nivel,
    solo dirige a los servicios a través de sus interfaces.
    """
    
    def __init__(
        self,
        context_manager: IContextManager,
        capacity_manager: ICapacityManager,
        sqs_dispatcher: ISQSDispatcher,
        event_store: IEventStore,
        metrics: IMetricsService
    ):
        self.context_manager = context_manager
        self.capacity_manager = capacity_manager
        self.sqs_dispatcher = sqs_dispatcher
        self.event_store = event_store
        self.metrics = metrics
        self.logger = logging.getLogger(__name__)
        self.logger.info("Intelligent Orchestrator inicializado")

    async def start_new_analysis(self, request: AnalysisRequest, user_id: str) -> AnalysisContext:
        """
        LUIS: Punto de entrada para una nueva solicitud de análisis.
        1. Verifica capacidad
        2. Crea el contexto en la DB
        3. Despacha el trabajo a la cola
        """
        self.logger.info(f"Iniciando nuevo análisis: {request.protocol_type} para usuario {user_id}")
        
        # Registra métrica de inicio
        self.metrics.record_analysis_started()
        
        try:
            # Verifica capacidad del sistema
            can_process = await self.capacity_manager.can_process_request()
            
            # Crea el contexto de análisis
            context = await self.context_manager.create_context(request, user_id)
            
            # Registra evento de inicio
            await self.event_store.store_event(EventStoreEntry(
                context_id=context.context_id,
                event_type="analysis_requested",
                data={
                    "protocol_type": request.protocol_type,
                    "user_id": user_id,
                    "workspace_id": request.workspace_id,
                    "priority": request.priority
                },
                agent="orchestrator"
            ))
            
            if can_process:
                # Procesa inmediatamente
                await self._dispatch_for_processing(context, request.priority)
                
                # Marca capacidad como ocupada
                await self.capacity_manager.record_job_started()
                
                self.logger.info(f"Análisis despachado para procesamiento: {context.context_id}")
                
            else:
                # Añade a lista de espera
                position = await self.capacity_manager.add_to_waitlist(context.context_id)
                
                # Actualiza estado a encolado
                context.status = AnalysisStatus.QUEUED
                await self.context_manager.update_context(context)
                
                # Registra evento de encolado
                await self.event_store.store_event(EventStoreEntry(
                    context_id=context.context_id,
                    event_type="analysis_queued",
                    data={"position": position},
                    agent="orchestrator"
                ))
                
                self.logger.info(f"Análisis añadido a lista de espera: {context.context_id}, posición: {position}")
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error iniciando análisis: {e}")
            
            # Registra métrica de fallo
            self.metrics.record_analysis_failed()
            
            # Registra evento de error
            await self.event_store.store_event(EventStoreEntry(
                context_id=getattr(context, 'context_id', str(uuid.uuid4())),
                event_type="analysis_start_failed",
                data={"error": str(e)},
                agent="orchestrator"
            ))
            
            raise ServiceUnavailableException(f"No se pudo iniciar el análisis: {e}")

    async def _dispatch_for_processing(self, context: AnalysisContext, priority: int) -> None:
        """LUIS: Despacha un contexto para procesamiento."""
        # Crea payload del trabajo
        payload = JobPayload(
            context_id=context.context_id,
            priority=priority
        )
        
        # Envía a cola SQS
        await self.sqs_dispatcher.dispatch_analysis_job(payload)
        
        # Actualiza estado del contexto
        context.status = AnalysisStatus.QUEUED
        await self.context_manager.update_context(context)

    async def process_analysis_from_queue(self, payload: JobPayload) -> None:
        """
        LUIS: Procesa un análisis desde la cola SQS.
        Este método sería llamado por el worker que consume de SQS.
        """
        context_id = payload.context_id
        self.logger.info(f"Procesando análisis desde cola: {context_id}")
        
        try:
            # Obtiene el contexto
            context = await self.context_manager.get_context(context_id)
            if not context:
                raise AnalysisNotFoundException(f"Contexto no encontrado: {context_id}")
            
            # Registra evento de procesamiento
            await self.event_store.store_event(EventStoreEntry(
                context_id=context_id,
                event_type="analysis_processing_started",
                data={"trace_id": payload.trace_id},
                agent="orchestrator"
            ))
            
            # Actualiza estado a procesando
            context.status = AnalysisStatus.PROCESSING
            await self.context_manager.update_context(context)
            
            # Aquí iría la lógica específica del pipeline científico
            # Por ahora, simulamos procesamiento
            await self._simulate_processing(context)
            
        except Exception as e:
            self.logger.error(f"Error procesando análisis desde cola {context_id}: {e}")
            
            # Marca como fallido
            await self.context_manager.mark_failed(context_id, str(e))
            
            # Registra evento de error
            await self.event_store.store_event(EventStoreEntry(
                context_id=context_id,
                event_type="analysis_processing_failed",
                data={"error": str(e)},
                agent="orchestrator"
            ))
            
            raise

    async def _simulate_processing(self, context: AnalysisContext) -> None:
        """LUIS: Simula el procesamiento de un análisis."""
        import asyncio
        
        # Simula progreso
        for progress in [25, 50, 75, 100]:
            await asyncio.sleep(1)
            await self.context_manager.update_progress(
                context.context_id, 
                progress, 
                f"Procesando... {progress}%"
            )
        
        # Simula resultados
        results = {
            "simulation": True,
            "protocol_type": context.protocol_type,
            "completed_at": datetime.utcnow().isoformat(),
            "results": {
                "status": "completed",
                "findings": ["Análisis completado exitosamente"],
                "confidence": 0.95
            }
        }
        
        await self.context_manager.set_results(context.context_id, results)
        await self.context_manager.mark_completed(context.context_id)
        
        # Registra métrica de finalización
        self.metrics.record_analysis_completed(5.0)  # 5 segundos simulados

    async def get_analysis_status(self, context_id: str) -> Optional[AnalysisContext]:
        """LUIS: Obtiene el estado de un análisis."""
        try:
            return await self.context_manager.get_context(context_id)
        except Exception as e:
            self.logger.error(f"Error obteniendo estado del análisis {context_id}: {e}")
            return None

    async def cancel_analysis(self, context_id: str) -> bool:
        """LUIS: Cancela un análisis."""
        try:
            context = await self.context_manager.get_context(context_id)
            if not context:
                return False
            
            # Solo se puede cancelar si está pendiente o en cola
            if context.status in [AnalysisStatus.PENDING, AnalysisStatus.QUEUED]:
                context.status = AnalysisStatus.CANCELLED
                await self.context_manager.update_context(context)
                
                # Registra evento de cancelación
                await self.event_store.store_event(EventStoreEntry(
                    context_id=context_id,
                    event_type="analysis_cancelled",
                    data={"previous_status": context.status},
                    agent="orchestrator"
                ))
                
                self.logger.info(f"Análisis cancelado: {context_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error cancelando análisis {context_id}: {e}")
            return False

    async def get_user_analyses(self, user_id: str, limit: int = 50) -> list:
        """LUIS: Obtiene los análisis de un usuario."""
        try:
            return await self.context_manager.get_contexts_by_user(user_id, limit)
        except Exception as e:
            self.logger.error(f"Error obteniendo análisis del usuario {user_id}: {e}")
            return []

    async def get_system_stats(self) -> dict:
        """LUIS: Obtiene estadísticas del sistema."""
        try:
            # Capacidad actual
            capacity_info = await self.capacity_manager.get_current_capacity()
            
            # Estado de la cola
            queue_status = await self.sqs_dispatcher.get_queue_status()
            
            # Estadísticas de uso
            usage_stats = await self.event_store.get_usage_statistics()
            
            return {
                "capacity": capacity_info,
                "queue": queue_status,
                "usage": usage_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas del sistema: {e}")
            return {"error": str(e)}

    async def health_check(self) -> dict:
        """LUIS: Verificación de salud del orquestador."""
        try:
            health_status = {
                "orchestrator": "healthy",
                "components": {}
            }
            
            # Verifica Context Manager
            try:
                test_context = await self.context_manager.get_context("test")
                health_status["components"]["context_manager"] = "healthy"
            except Exception as e:
                health_status["components"]["context_manager"] = f"unhealthy: {e}"
            
            # Verifica Capacity Manager
            try:
                capacity = await self.capacity_manager.get_current_capacity()
                health_status["components"]["capacity_manager"] = "healthy"
            except Exception as e:
                health_status["components"]["capacity_manager"] = f"unhealthy: {e}"
            
            # Verifica SQS Dispatcher
            try:
                queue_status = await self.sqs_dispatcher.get_queue_status()
                health_status["components"]["sqs_dispatcher"] = "healthy"
            except Exception as e:
                health_status["components"]["sqs_dispatcher"] = f"unhealthy: {e}"
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error en health check: {e}")
            return {"orchestrator": "unhealthy", "error": str(e)}