# -*- coding: utf-8 -*-
"""
ASTROFLORA - ANALYSIS WORKER INDEPENDIENTE
Worker separado para procesamiento de análisis científicos
"""
import asyncio
import logging
import signal
import sys
import json
import socket
import os
import time
from typing import Dict, Any, Optional
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.config.settings import settings
from src.container import AstrofloraContainer
from src.models.analysis import AnalysisContext, JobPayload
from src.core.pipeline import ScientificPipeline

class AnalysisWorker:
    """
    Worker independiente que procesa análisis científicos.
    Consume trabajos de Redis y ejecuta pipelines bioinformáticos.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.container = None
        self.redis_client = None
        
        # Configuración de la cola
        self.queue_key = "astroflora:analysis_queue"
        self.processing_key = "astroflora:processing"
        
        # Worker ID único
        self.worker_id = f"{socket.gethostname()}-{os.getpid()}-{int(time.time())}"
        
        # Configuración de timeouts
        self.job_timeout = 1800  # 30 minutos por job
        self.step_timeout = 300   # 5 minutos por paso
        
        self.logger.info(f"🔬 Analysis Worker inicializado - ID: {self.worker_id}")

    async def start(self):
        """Inicia el worker."""
        try:
            self.logger.info(f"🚀 Iniciando Analysis Worker {self.worker_id}...")
            
            # Inicializa contenedor
            self.container = AstrofloraContainer()
            
            # Cliente Redis usando configuración
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
            self.redis_client = aioredis.from_url(
                redis_url,
                decode_responses=True
            )
            
            # Verifica conexión Redis
            await self._verify_redis_connection()
            
            # Configura signal handlers
            self._setup_signal_handlers()
            
            # Inicia el pipeline científico
            await self._init_scientific_pipeline()
            
            self.running = True
            self.logger.info(f"✅ Analysis Worker {self.worker_id} iniciado exitosamente")
            
            # Loop principal
            await self._worker_loop()
            
        except Exception as e:
            self.logger.error(f"❌ Error iniciando worker: {e}")
            await self.shutdown()
            raise

    async def _verify_redis_connection(self):
        """Verifica conexión con Redis."""
        try:
            await self.redis_client.ping()
            self.logger.info("✅ Conexión Redis verificada")
        except Exception as e:
            self.logger.error(f"❌ Error conectando Redis: {e}")
            raise

    async def _init_scientific_pipeline(self):
        """Inicializa el pipeline científico."""
        from src.services.bioinformatics.blast_service import RealBlastService
        from src.services.bioinformatics.uniprot_service import RealUniProtService
        
        # Servicios bioinformáticos REALES
        self.blast_service = RealBlastService(
            self.container.circuit_breaker_factory
        )
        
        self.uniprot_service = RealUniProtService(
            self.container.circuit_breaker_factory
        )
        
        # Pipeline científico completo
        self.scientific_pipeline = ScientificPipeline(
            self.blast_service,
            self.uniprot_service,
            self.container.driver_ia,  # También es ILLMService
            self.container.circuit_breaker_factory
        )
        
        self.logger.info("🧬 Pipeline científico inicializado")

    def _setup_signal_handlers(self):
        """Configura manejo de señales para shutdown graceful."""
        def signal_handler(sig, frame):
            self.logger.info(f"🛑 Señal {sig} recibida, cerrando worker...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def _worker_loop(self):
        """Loop principal del worker."""
        self.logger.info("🔄 Iniciando loop de procesamiento...")
        
        while self.running:
            try:
                # Consume trabajo de la cola (BLPOP con timeout)
                result = await self.redis_client.blpop(
                    self.queue_key, 
                    timeout=5  # 5 segundos timeout
                )
                
                if result:
                    queue_name, job_data = result
                    await self._process_job(job_data)
                
            except Exception as e:
                self.logger.error(f"❌ Error en worker loop: {e}")
                await asyncio.sleep(1)  # Prevent tight error loop
        
        self.logger.info("✅ Worker loop terminado")

    async def _process_job(self, job_data: str):
        """Procesa un trabajo individual con timeout y reintentos."""
        job_id = None
        
        try:
            # Parse job payload
            job_payload = json.loads(job_data)
            job_id = job_payload.get('context_id', 'unknown')
            
            self.logger.info(f"📥 Procesando job: {job_id}")
            
            # Marca trabajo como en procesamiento
            await self.redis_client.hset(
                f"{self.processing_key}:{job_id}",
                mapping={
                    "status": "processing",
                    "worker_id": self.worker_id,  # Worker ID único
                    "started_at": time.time()
                }
            )
            
            # Procesa con timeout global
            async with asyncio.timeout(self.job_timeout):
                await self._execute_job_with_retries(job_id, job_payload)
            
            # Marca como completado
            await self._mark_job_completed(job_id)
            
            self.logger.info(f"✅ Job completado: {job_id}")
            
        except asyncio.TimeoutError:
            error_msg = f"Job timeout después de {self.job_timeout}s"
            self.logger.error(f"⏰ {error_msg}: {job_id}")
            await self._mark_job_failed(job_id, error_msg)
            
        except Exception as e:
            self.logger.error(f"❌ Error procesando job {job_id}: {e}")
            await self._mark_job_failed(job_id, str(e))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception))
    )
    async def _execute_job_with_retries(self, job_id: str, job_payload: Dict[str, Any]):
        """Ejecuta job con reintentos automáticos."""
        try:
            # Obtiene contexto del análisis
            context = await self.container.context_manager.get_context(job_id)
            if not context:
                raise Exception(f"Contexto no encontrado: {job_id}")
            
            # Sincroniza payload con context (para consistencia)
            await self._sync_context_with_payload(context, job_payload)
            
            # Ejecuta análisis según el tipo
            await self._execute_analysis(context, job_payload)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Reintentando job {job_id} debido a: {e}")
            raise  # Para que retry lo capture

    async def _sync_context_with_payload(self, context: AnalysisContext, payload: Dict[str, Any]):
        """Sincroniza datos entre context y payload para consistencia."""
        try:
            # Si payload tiene secuencias, las guarda en context
            if 'sequences' in payload and payload['sequences']:
                if not hasattr(context, 'request_data'):
                    context.request_data = {}
                context.request_data['sequences'] = payload['sequences']
                
                # Actualiza context en BD
                await self.container.context_manager.update_context(context)
                
            self.logger.debug(f"🔄 Context sincronizado para job: {context.context_id}")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error sincronizando context: {e}")
            # No es crítico, continúa

    async def _execute_analysis(self, context: AnalysisContext, job_payload: Dict[str, Any]):
        """Ejecuta el análisis según el tipo."""
        protocol_type = context.protocol_type
        
        if protocol_type == "PROTEIN_FUNCTION_ANALYSIS":
            await self._execute_protein_analysis(context)
        elif protocol_type == "SEQUENCE_ALIGNMENT":
            await self._execute_sequence_alignment(context)
        elif protocol_type == "STRUCTURE_PREDICTION":
            await self._execute_structure_prediction(context)
        elif protocol_type == "PIPELINE_BATCH":
            await self._execute_pipeline_batch(context, job_payload)
        else:
            # Análisis genérico con Driver IA
            await self._execute_generic_analysis(context)

    async def _execute_generic_analysis(self, context: AnalysisContext):
        """Ejecuta análisis genérico usando Driver IA."""
        try:
            # Convierte context a AnalysisRequest de forma segura
            if hasattr(context, 'to_analysis_request') and callable(context.to_analysis_request):
                analysis_request = context.to_analysis_request()
            else:
                # Fallback: construye manualmente
                from src.models.analysis import AnalysisRequest
                analysis_request = AnalysisRequest(
                    workspace_id=context.workspace_id,
                    protocol_type=context.protocol_type,
                    **context.request_data
                )
            
            protocol = await self.container.driver_ia.generate_protocol(analysis_request)
            await self.container.driver_ia.execute_protocol(protocol, context)
            
        except Exception as e:
            raise Exception(f"Error en análisis genérico: {e}")

    async def _execute_protein_analysis(self, context: AnalysisContext):
        """Ejecuta análisis de función de proteína con timeouts por paso."""
        try:
            # Actualiza progreso
            await self.container.context_manager.update_progress(
                context.context_id, 10, "Iniciando análisis de proteína"
            )
            
            # Obtiene secuencia
            sequence = context.request_data.get('sequence', '')
            if not sequence:
                raise Exception("Secuencia de proteína requerida")
            
            # Pipeline: BLAST → UniProt → LLM Analysis con timeouts
            
            # 1. BLAST Search (25% progreso) con timeout
            await self.container.context_manager.update_progress(
                context.context_id, 25, "Ejecutando búsqueda BLAST"
            )
            
            blast_result = await asyncio.wait_for(
                self.blast_service.search_homology(sequence, database="nr", max_hits=50),
                timeout=self.step_timeout
            )
            
            # 2. UniProt Annotations (50% progreso) con timeout
            await self.container.context_manager.update_progress(
                context.context_id, 50, "Obteniendo anotaciones UniProt"
            )
            
            protein_ids = self._extract_protein_ids(blast_result)
            uniprot_result = await asyncio.wait_for(
                self.uniprot_service.get_protein_annotations(protein_ids[:10]),
                timeout=self.step_timeout
            )
            
            # 3. LLM Analysis (75% progreso) con timeout
            await self.container.context_manager.update_progress(
                context.context_id, 75, "Analizando con IA"
            )
            
            # Prepara datos para LLM
            analysis_data = {
                "sequence": sequence,
                "blast_results": blast_result,
                "uniprot_annotations": uniprot_result
            }
            
            llm_analysis = await asyncio.wait_for(
                self.container.driver_ia.analyze_results(context.context_id, analysis_data),
                timeout=self.step_timeout
            )
            
            # Resultado final
            final_results = {
                "analysis_type": "protein_function",
                "sequence_analyzed": sequence,
                "blast_summary": blast_result,
                "uniprot_summary": uniprot_result,
                "ai_analysis": llm_analysis,
                "completed_at": time.time(),
                "worker_id": self.worker_id
            }
            
            await self.container.context_manager.set_results(
                context.context_id, 
                final_results
            )
            
            await self.container.context_manager.update_progress(
                context.context_id, 100, "Análisis completado"
            )
            
        except asyncio.TimeoutError as e:
            raise Exception(f"Timeout en análisis de proteína: {e}")
        except Exception as e:
            raise Exception(f"Error en análisis de proteína: {e}")

    async def _execute_sequence_alignment(self, context: AnalysisContext):
        """Ejecuta análisis de alineamiento de secuencias."""
        try:
            await self.container.context_manager.update_progress(
                context.context_id, 10, "Iniciando alineamiento de secuencias"
            )
            
            # Implementación placeholder - expandir según necesidades
            sequences = context.request_data.get('sequences', [])
            if not sequences or len(sequences) < 2:
                raise Exception("Mínimo 2 secuencias requeridas para alineamiento")
            
            # Simula procesamiento
            await asyncio.sleep(2)
            
            final_results = {
                "analysis_type": "sequence_alignment",
                "sequences_count": len(sequences),
                "alignment_result": "Placeholder - implementar MAFFT/MUSCLE",
                "completed_at": time.time(),
                "worker_id": self.worker_id
            }
            
            await self.container.context_manager.set_results(context.context_id, final_results)
            await self.container.context_manager.update_progress(context.context_id, 100, "Alineamiento completado")
            
        except Exception as e:
            raise Exception(f"Error en alineamiento de secuencias: {e}")

    async def _execute_structure_prediction(self, context: AnalysisContext):
        """Ejecuta predicción de estructura."""
        try:
            await self.container.context_manager.update_progress(
                context.context_id, 10, "Iniciando predicción de estructura"
            )
            
            sequence = context.request_data.get('sequence', '')
            if not sequence:
                raise Exception("Secuencia requerida para predicción de estructura")
            
            # Placeholder para AlphaFold/ChimeraX
            await asyncio.sleep(3)
            
            final_results = {
                "analysis_type": "structure_prediction",
                "sequence": sequence,
                "structure_result": "Placeholder - implementar AlphaFold",
                "completed_at": time.time(),
                "worker_id": self.worker_id
            }
            
            await self.container.context_manager.set_results(context.context_id, final_results)
            await self.container.context_manager.update_progress(context.context_id, 100, "Predicción completada")
            
        except Exception as e:
            raise Exception(f"Error en predicción de estructura: {e}")

    async def _execute_pipeline_batch(self, context: AnalysisContext, job_payload: Dict[str, Any]):
        """Ejecuta pipeline científico en lote - usa context preferentemente."""
        try:
            # Prioriza secuencias del context, fallback al payload
            sequences = context.request_data.get('sequences')
            if not sequences:
                sequences = job_payload.get('sequences', [])
            
            if not sequences:
                raise Exception("Lista de secuencias requerida para batch")
            
            self.logger.info(f"🧬 Ejecutando pipeline batch: {len(sequences)} secuencias")
            
            await self.container.context_manager.update_progress(
                context.context_id, 10, f"Iniciando pipeline batch ({len(sequences)} secuencias)"
            )
            
            # Ejecuta pipeline batch con timeout
            batch_results = await asyncio.wait_for(
                self.scientific_pipeline.run_batch_analysis(sequences),
                timeout=self.job_timeout * 0.8  # 80% del timeout global
            )
            
            # Añade metadatos del worker
            batch_results["worker_id"] = self.worker_id
            batch_results["completed_at"] = time.time()
            
            await self.container.context_manager.set_results(
                context.context_id,
                batch_results
            )
            
            await self.container.context_manager.update_progress(
                context.context_id, 100, "Pipeline batch completado"
            )
            
        except asyncio.TimeoutError:
            raise Exception("Timeout en pipeline batch")
        except Exception as e:
            raise Exception(f"Error en pipeline batch: {e}")

    async def _mark_job_completed(self, job_id: str):
        """Marca trabajo como completado."""
        try:
            await self.redis_client.hset(
                f"{self.processing_key}:{job_id}",
                mapping={
                    "status": "completed",
                    "completed_at": time.time(),
                    "worker_id": self.worker_id
                }
            )
            
            # Libera capacidad
            await self.container.capacity_manager.record_job_finished()
            
            self.logger.info(f"✅ Job marcado como completado: {job_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Error marcando job como completado: {e}")

    async def _mark_job_failed(self, job_id: str, error: str):
        """Marca trabajo como fallido."""
        if job_id:
            try:
                await self.redis_client.hset(
                    f"{self.processing_key}:{job_id}",
                    mapping={
                        "status": "failed", 
                        "error": error,
                        "failed_at": time.time(),
                        "worker_id": self.worker_id
                    }
                )
                
                # Marca contexto como fallido
                await self.container.context_manager.mark_failed(job_id, error)
                
                # Libera capacidad
                await self.container.capacity_manager.record_job_finished()
                
                self.logger.error(f"❌ Job marcado como fallido: {job_id} - {error}")
                
            except Exception as e:
                self.logger.error(f"❌ Error marcando job como fallido: {e}")

    async def get_worker_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del worker."""
        try:
            # Cuenta trabajos en procesamiento de este worker
            processing_keys = await self.redis_client.keys(f"{self.processing_key}:*")
            my_jobs = 0
            
            for key in processing_keys:
                job_data = await self.redis_client.hgetall(key)
                if job_data.get("worker_id") == self.worker_id:
                    my_jobs += 1
            
            return {
                "worker_id": self.worker_id,
                "status": "running" if self.running else "stopped",
                "jobs_in_progress": my_jobs,
                "uptime_seconds": time.time() - getattr(self, '_start_time', time.time()),
                "job_timeout": self.job_timeout,
                "step_timeout": self.step_timeout
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo stats: {e}")
            return {
                "worker_id": self.worker_id,
                "status": "error",
                "error": str(e)
            }

    def _extract_protein_ids(self, blast_result) -> list:
        """Extrae IDs de proteínas del resultado BLAST."""
        try:
            if hasattr(blast_result, 'hits'):
                return [hit.get('accession') or hit.get('id') for hit in blast_result.hits if hit.get('accession') or hit.get('id')]
            elif isinstance(blast_result, dict):
                hits = blast_result.get('hits', [])
                return [hit.get('accession') or hit.get('id') for hit in hits if hit.get('accession') or hit.get('id')]
            return []
        except Exception as e:
            self.logger.warning(f"Error extrayendo protein IDs: {e}")
            return []

    async def shutdown(self):
        """Shutdown graceful del worker."""
        try:
            self.logger.info(f"🔄 Cerrando Analysis Worker {self.worker_id}...")
            
            self.running = False
            
            if self.redis_client:
                await self.redis_client.close()
            
            if self.container:
                await self.container.shutdown()
            
            self.logger.info(f"✅ Analysis Worker {self.worker_id} cerrado")
            
        except Exception as e:
            self.logger.error(f"Error cerrando worker: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """Health check del worker."""
        try:
            health_status = {
                "worker_id": self.worker_id,
                "status": "healthy" if self.running else "stopped",
                "redis_connection": False,
                "container_health": {}
            }
            
            # Verifica Redis
            if self.redis_client:
                try:
                    await self.redis_client.ping()
                    health_status["redis_connection"] = True
                except:
                    health_status["redis_connection"] = False
            
            # Verifica Container
            if self.container:
                health_status["container_health"] = await self.container.health_check()
            
            return health_status
            
        except Exception as e:
            return {
                "worker_id": self.worker_id,
                "status": "unhealthy",
                "error": str(e)
            }

async def main():
    """Función principal del worker."""
    # Configuración de logging mejorada
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(process)d] - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/tmp/analysis_worker.log', mode='a')
        ]
    )
    
    worker = AnalysisWorker()
    worker._start_time = time.time()  # Para estadísticas de uptime
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        print(f"\n🛑 Interrupción del usuario - Worker {worker.worker_id}")
    except Exception as e:
        print(f"❌ Error fatal en Worker {worker.worker_id}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await worker.shutdown()

if __name__ == "__main__":
    asyncio.run(main())