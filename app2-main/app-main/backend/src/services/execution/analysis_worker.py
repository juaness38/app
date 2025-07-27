# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - ANALYSIS WORKER
LUIS: Worker que procesa trabajos de análisis. El laboratorio autónomo.
"""
import logging
import asyncio
from typing import Dict, Any
from src.services.interfaces import (
    IAnalysisWorker, IDriverIA, IContextManager, ICapacityManager, IEventStore
)
from src.models.analysis import JobPayload, AnalysisStatus, EventStoreEntry, AnalysisRequest
from src.core.exceptions import AnalysisNotFoundException, DriverIAException

class AnalysisWorker(IAnalysisWorker):
    """
    LUIS: Worker que procesa trabajos de análisis.
    Es el laboratorio autónomo que ejecuta los protocolos.
    """
    
    def __init__(
        self,
        driver_ia: IDriverIA,
        context_manager: IContextManager,
        capacity_manager: ICapacityManager,
        event_store: IEventStore
    ):
        self.driver_ia = driver_ia
        self.context_manager = context_manager
        self.capacity_manager = capacity_manager
        self.event_store = event_store
        self.logger = logging.getLogger(__name__)
        self.logger.info("Analysis Worker inicializado")

    async def process_job(self, payload: JobPayload) -> None:
        """
        LUIS: Procesa un trabajo de análisis.
        Este es el corazón del laboratorio autónomo.
        """
        context_id = payload.context_id
        trace_id = payload.trace_id
        
        self.logger.info(f"Procesando trabajo: {context_id} [trace: {trace_id}]")
        
        try:
            # Registra inicio del trabajo
            await self.event_store.store_event(EventStoreEntry(
                context_id=context_id,
                event_type="worker_started",
                data={"trace_id": trace_id, "priority": payload.priority},
                agent="analysis_worker"
            ))
            
            # Obtiene el contexto
            context = await self.context_manager.get_context(context_id)
            if not context:
                raise AnalysisNotFoundException(f"Contexto no encontrado: {context_id}")
            
            # Actualiza estado a procesando
            context.status = AnalysisStatus.PROCESSING
            await self.context_manager.update_context(context)
            
            # Genera el protocolo basado en el tipo de análisis
            protocol = await self.driver_ia.generate_protocol(AnalysisRequest(
                workspace_id=context.workspace_id,
                protocol_type=context.protocol_type,
                parameters=context.results.get("request_parameters", {})
            ))
            
            # Registra el protocolo generado
            await self.event_store.store_event(EventStoreEntry(
                context_id=context_id,
                event_type="protocol_generated",
                data={
                    "protocol_name": protocol.name,
                    "protocol_type": protocol.protocol_type,
                    "nodes_count": len(protocol.nodes)
                },
                agent="analysis_worker"
            ))
            
            # Ejecuta el protocolo con el Driver IA
            await self.driver_ia.execute_protocol(protocol, context)
            
            # Obtiene el contexto actualizado
            updated_context = await self.context_manager.get_context(context_id)
            
            # Realiza análisis final de resultados
            if updated_context and updated_context.results:
                final_analysis = await self.driver_ia.analyze_results(
                    context_id, 
                    updated_context.results
                )
                
                # Guarda análisis final
                results = updated_context.results.copy()
                results["final_analysis"] = final_analysis
                await self.context_manager.set_results(context_id, results)
                
                # Registra análisis final
                await self.event_store.store_event(EventStoreEntry(
                    context_id=context_id,
                    event_type="final_analysis_completed",
                    data=final_analysis,
                    agent="analysis_worker"
                ))
            
            # Registra éxito del trabajo
            await self.event_store.store_event(EventStoreEntry(
                context_id=context_id,
                event_type="worker_completed",
                data={"trace_id": trace_id},
                agent="analysis_worker"
            ))
            
            self.logger.info(f"Trabajo completado exitosamente: {context_id}")
            
        except Exception as e:
            self.logger.error(f"Error procesando trabajo {context_id}: {e}")
            
            # Marca como fallido
            await self.context_manager.mark_failed(context_id, str(e))
            
            # Registra error
            await self.event_store.store_event(EventStoreEntry(
                context_id=context_id,
                event_type="worker_failed",
                data={"trace_id": trace_id, "error": str(e)},
                agent="analysis_worker"
            ))
            
            raise
            
        finally:
            # Libera capacidad
            await self.capacity_manager.record_job_finished()
            
            # Procesa siguiente trabajo en lista de espera si existe
            await self._process_next_from_waitlist()

    async def _process_next_from_waitlist(self) -> None:
        """LUIS: Procesa el siguiente trabajo de la lista de espera."""
        try:
            next_context_id = await self.capacity_manager.get_next_from_waitlist()
            if next_context_id:
                self.logger.info(f"Procesando siguiente trabajo de lista de espera: {next_context_id}")
                
                # Crea payload para el trabajo
                payload = JobPayload(
                    context_id=next_context_id,
                    priority=3  # Prioridad media para trabajos de lista de espera
                )
                
                # Procesa de forma asíncrona
                asyncio.create_task(self.process_job(payload))
                
        except Exception as e:
            self.logger.error(f"Error procesando trabajo de lista de espera: {e}")

    async def health_check(self) -> bool:
        """LUIS: Verificación de salud del worker."""
        try:
            # Verifica que todos los servicios estén disponibles
            services_healthy = True
            
            # Verifica Driver IA
            if not hasattr(self.driver_ia, 'http_client'):
                services_healthy = False
            
            # Verifica Context Manager
            if not hasattr(self.context_manager, 'collection'):
                services_healthy = False
            
            # Verifica Event Store
            if not hasattr(self.event_store, 'collection'):
                services_healthy = False
            
            return services_healthy
            
        except Exception as e:
            self.logger.error(f"Error en health check: {e}")
            return False

    async def get_worker_stats(self) -> Dict[str, Any]:
        """LUIS: Obtiene estadísticas del worker."""
        try:
            # Obtiene capacidad actual
            capacity_info = await self.capacity_manager.get_current_capacity()
            
            # Obtiene estadísticas de eventos recientes
            from datetime import datetime, timedelta
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            recent_events = await self.event_store.get_events_in_timerange(
                one_hour_ago, 
                datetime.utcnow()
            )
            
            # Agrupa eventos por tipo
            event_counts = {}
            for event in recent_events:
                event_type = event.event_type
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            return {
                "capacity": capacity_info,
                "recent_events": event_counts,
                "health_status": await self.health_check(),
                "uptime": "active"  # Placeholder
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas: {e}")
            return {"error": str(e)}

    async def shutdown(self) -> None:
        """LUIS: Cierra el worker de forma limpia."""
        try:
            self.logger.info("Cerrando Analysis Worker...")
            
            # Espera a que terminen trabajos actuales
            await asyncio.sleep(1)
            
            # Cierra servicios
            if hasattr(self.driver_ia, 'close'):
                await self.driver_ia.close()
            
            self.logger.info("Analysis Worker cerrado")
            
        except Exception as e:
            self.logger.error(f"Error cerrando worker: {e}")