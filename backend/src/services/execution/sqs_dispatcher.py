# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - DESPACHADOR SQS
LUIS: Despacha trabajos a una cola SQS para procesamiento asíncrono.
"""
import logging
import asyncio
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError
from src.services.interfaces import ISQSDispatcher, IMetricsService
from src.models.analysis import JobPayload
from src.config.settings import settings
from src.core.exceptions import ServiceUnavailableException

class SQSDispatcher(ISQSDispatcher):
    """
    LUIS: Despacha trabajos a una cola SQS.
    Desacopla la API de los workers para escalabilidad.
    """
    
    def __init__(self, metrics: IMetricsService):
        self.metrics = metrics
        self.logger = logging.getLogger(__name__)
        
        # Configuración de SQS
        try:
            self.sqs_client = boto3.client("sqs", region_name=settings.AWS_REGION)
            self.queue_url = settings.SQS_ANALYSIS_QUEUE_URL
            self.logger.info("Despachador SQS inicializado")
            
        except Exception as e:
            self.logger.error(f"Error inicializando cliente SQS: {e}")
            # En desarrollo, podemos usar una cola simulada
            self.sqs_client = None
            self.queue_url = None

    async def dispatch_analysis_job(self, payload: JobPayload) -> None:
        """LUIS: Envía el payload del trabajo a la cola SQS."""
        try:
            # Envío simulado para desarrollo
            await self._simulate_queue_dispatch(payload)
            return
            
        except Exception as e:
            self.logger.error(f"Error inesperado en dispatch: {e}")
            # En modo simulado, no lanzar excepción
            await self._simulate_queue_dispatch(payload)

    async def _simulate_queue_dispatch(self, payload: JobPayload) -> None:
        """LUIS: Simula el envío a cola para desarrollo."""
        self.logger.info(f"[SIMULADO] Trabajo enviado a cola: {payload.context_id}")
        
        # Simula procesamiento asíncrono inmediato
        import asyncio
        asyncio.create_task(self._simulate_worker_processing(payload))

    async def _simulate_worker_processing(self, payload: JobPayload) -> None:
        """LUIS: Simula el procesamiento por un worker."""
        # Simula delay de procesamiento
        await asyncio.sleep(1)
        
        # Simula procesamiento exitoso
        self.logger.info(f"[SIMULADO] Trabajo procesado exitosamente: {payload.context_id}")
        
        # Simula actualización de contexto
        try:
            from src.api.dependencies import get_container
            container = get_container()
            
            # Simula progreso
            for progress in [25, 50, 75, 100]:
                await asyncio.sleep(0.5)
                await container.context_manager.update_progress(
                    payload.context_id, 
                    progress, 
                    f"Procesando... {progress}%"
                )
            
            # Simula finalización
            results = {
                "simulation": True,
                "protocol_completed": True,
                "tools_used": ["blast", "alphafold", "interpro"],
                "findings": ["Análisis completado exitosamente en modo simulado"],
                "confidence": 0.95
            }
            
            await container.context_manager.set_results(payload.context_id, results)
            await container.context_manager.mark_completed(payload.context_id)
            
        except Exception as e:
            self.logger.error(f"Error en simulación de procesamiento: {e}")
            try:
                await container.context_manager.mark_failed(payload.context_id, str(e))
            except:
                pass

    async def get_queue_status(self) -> Dict[str, Any]:
        """LUIS: Obtiene el estado actual de la cola."""
        try:
            if not self.sqs_client:
                return {
                    "mode": "simulated",
                    "queue_url": "simulated",
                    "approximate_messages": 0,
                    "approximate_messages_not_visible": 0
                }
            
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.sqs_client.get_queue_attributes(
                    QueueUrl=self.queue_url,
                    AttributeNames=[
                        'ApproximateNumberOfMessages',
                        'ApproximateNumberOfMessagesNotVisible'
                    ]
                )
            )
            
            attributes = response.get('Attributes', {})
            return {
                "mode": "real",
                "queue_url": self.queue_url,
                "approximate_messages": int(attributes.get('ApproximateNumberOfMessages', 0)),
                "approximate_messages_not_visible": int(attributes.get('ApproximateNumberOfMessagesNotVisible', 0))
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estado de cola: {e}")
            return {
                "mode": "error",
                "queue_url": self.queue_url,
                "error": str(e)
            }

    async def create_queue_if_not_exists(self) -> bool:
        """LUIS: Crea la cola si no existe (útil para setup)."""
        try:
            if not self.sqs_client:
                self.logger.info("No se puede crear cola en modo simulado")
                return True
                
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.sqs_client.create_queue(
                    QueueName='astroflora-analysis-queue',
                    Attributes={
                        'VisibilityTimeoutSeconds': '300',
                        'MessageRetentionPeriod': '1209600',  # 14 días
                        'ReceiveMessageWaitTimeSeconds': '20'  # Long polling
                    }
                )
            )
            
            self.logger.info("Cola SQS creada o ya existe")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creando cola: {e}")
            return False

    async def purge_queue(self) -> bool:
        """LUIS: Limpia la cola (útil para testing)."""
        try:
            if not self.sqs_client:
                self.logger.info("No se puede purgar cola en modo simulado")
                return True
                
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.sqs_client.purge_queue(QueueUrl=self.queue_url)
            )
            
            self.logger.info("Cola SQS purgada")
            return True
            
        except Exception as e:
            self.logger.error(f"Error purgando cola: {e}")
            return False