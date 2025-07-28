# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - PIPELINE CIENTÍFICO MEJORADO
Pipeline científico con configuración centralizada, caching y retry logic.
BLAST → UniProt → Preprocesado → LLM
"""
import logging
import asyncio
import time
import hashlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from cachetools import TTLCache

from src.services.interfaces import IPipelineService, IBlastService, IUniProtService, ILLMService
from src.core.exceptions import PipelineException
from src.models.analysis import (
    PipelineResult, SequenceData, BlastResult, UniProtResult, LLMResult,
    PipelineConfig, CacheableResult
)

logger = logging.getLogger(__name__)

@dataclass
class PipelineStep:
    """Representa un paso individual del pipeline."""
    name: str
    description: str
    duration: float = 0.0
    success: bool = False
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    cached: bool = False

class ScientificPipeline(IPipelineService):
    """
    Pipeline científico mejorado con configuración centralizada y caching.
    Implementa el flujo: BLAST → UniProt → Preprocesado → LLM
    """
    
    def __init__(
        self,
        blast_service: IBlastService,
        uniprot_service: IUniProtService,
        llm_service: ILLMService,
        circuit_breaker_factory,
        config: Optional[PipelineConfig] = None
    ):
        self.blast_service = blast_service
        self.uniprot_service = uniprot_service
        self.llm_service = llm_service
        self.circuit_breaker_factory = circuit_breaker_factory
        
        # Configuración centralizada
        self.config = config or PipelineConfig()
        
        # Circuit Breakers para servicios externos
        self.blast_cb = circuit_breaker_factory("blast_pipeline")
        self.uniprot_cb = circuit_breaker_factory("uniprot_pipeline")
        self.llm_cb = circuit_breaker_factory("llm_pipeline")
        
        # Cache estratégico con TTL
        self.blast_cache = TTLCache(maxsize=1000, ttl=3600)  # 1 hora
        self.uniprot_cache = TTLCache(maxsize=500, ttl=7200)  # 2 horas
        self.sequence_features_cache = TTLCache(maxsize=2000, ttl=86400)  # 24 horas
        
        # Métricas del pipeline
        self.pipeline_metrics = {
            "total_sequences_processed": 0,
            "cache_hits": {"blast": 0, "uniprot": 0, "features": 0},
            "cache_misses": {"blast": 0, "uniprot": 0, "features": 0},
            "average_processing_time": 0.0,
            "success_rate": 0.0
        }
        
        logger.info(f"Pipeline Científico inicializado con configuración: {self.config}")

    async def run_batch_analysis(self, sequences: List[SequenceData]) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo para un batch de secuencias.
        
        Args:
            sequences: Lista de secuencias para analizar
            
        Returns:
            Resultados estructurados del pipeline
        """
        logger.info(f"Iniciando análisis en lote de {len(sequences)} secuencias")
        
        start_time = time.time()
        pipeline_results = []
        
        try:
            # Procesa secuencias con concurrencia controlada
            semaphore = asyncio.Semaphore(self.config.max_concurrent_sequences)
            tasks = [
                self._process_sequence_with_semaphore(semaphore, i, sequence, len(sequences))
                for i, sequence in enumerate(sequences)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Procesa resultados y maneja excepciones
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error procesando secuencia {sequences[i].id}: {result}")
                    pipeline_results.append(PipelineResult(
                        sequence_id=sequences[i].id,
                        success=False,
                        error=str(result),
                        steps=[],
                        processing_time=0.0
                    ))
                else:
                    pipeline_results.append(result)
            
            total_time = time.time() - start_time
            
            # Actualiza métricas
            self.pipeline_metrics["total_sequences_processed"] += len(sequences)
            successful = sum(1 for r in pipeline_results if r.success)
            self.pipeline_metrics["success_rate"] = successful / len(pipeline_results) if pipeline_results else 0
            
            # Estadísticas del batch
            failed = len(pipeline_results) - successful
            
            return {
                "batch_id": f"batch_{int(start_time)}",
                "total_sequences": len(sequences),
                "successful": successful,
                "failed": failed,
                "total_processing_time": total_time,
                "average_time_per_sequence": total_time / len(sequences) if sequences else 0,
                "cache_efficiency": self._calculate_cache_efficiency(),
                "results": [result.model_dump() for result in pipeline_results]
            }
            
        except Exception as e:
            logger.error(f"Error crítico en pipeline batch: {e}")
            raise PipelineException(f"Fallo crítico en pipeline: {e}")

    async def _process_sequence_with_semaphore(
        self, 
        semaphore: asyncio.Semaphore,
        index: int,
        sequence: SequenceData,
        total: int
    ) -> PipelineResult:
        """Procesa una secuencia con control de concurrencia."""
        async with semaphore:
            logger.info(f"Procesando secuencia {index+1}/{total}: {sequence.id}")
            return await self._run_single_sequence_pipeline(sequence)

    async def _run_single_sequence_pipeline(self, sequence: SequenceData) -> PipelineResult:
        """Ejecuta el pipeline completo para una secuencia individual."""
        
        start_time = time.time()
        steps = []
        
        try:
            # Paso 1: BLAST vs base de datos con caching
            blast_step = await self._run_blast_step_with_cache(sequence)
            steps.append(blast_step)
            
            if not blast_step.success:
                raise PipelineException(f"BLAST falló: {blast_step.error}")
            
            # Paso 2: Consulta a UniProt con caching
            uniprot_step = await self._run_uniprot_step_with_cache(blast_step.result)
            steps.append(uniprot_step)
            
            if not uniprot_step.success:
                logger.warning(f"UniProt falló, continuando: {uniprot_step.error}")
            
            # Paso 3: Preprocesado de secuencias con caching
            preprocessing_step = await self._run_preprocessing_step_with_cache(
                sequence, blast_step.result, uniprot_step.result
            )
            steps.append(preprocessing_step)
            
            if not preprocessing_step.success:
                raise PipelineException(f"Preprocesado falló: {preprocessing_step.error}")
            
            # Paso 4: Invocación al LLM con configuración
            llm_step = await self._run_llm_step_with_config(preprocessing_step.result)
            steps.append(llm_step)
            
            if not llm_step.success:
                logger.warning(f"LLM falló, usando resultados parciales: {llm_step.error}")
            
            total_time = time.time() - start_time
            
            return PipelineResult(
                sequence_id=sequence.id,
                success=True,
                steps=[step.__dict__ for step in steps],
                processing_time=total_time,
                final_result=llm_step.result if llm_step.success else preprocessing_step.result
            )
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Pipeline falló para secuencia {sequence.id}: {e}")
            
            return PipelineResult(
                sequence_id=sequence.id,
                success=False,
                error=str(e),
                steps=[step.__dict__ for step in steps],
                processing_time=total_time
            )

    async def _run_blast_step_with_cache(self, sequence: SequenceData) -> PipelineStep:
        """Ejecuta el paso de BLAST con caching estratégico."""
        step = PipelineStep("BLAST", "Búsqueda de homología en base de datos")
        start_time = time.time()
        
        try:
            # Genera hash de la secuencia para caching
            sequence_hash = hashlib.md5(sequence.sequence.encode()).hexdigest()
            
            # Verifica cache
            if sequence_hash in self.blast_cache:
                cached_result = self.blast_cache[sequence_hash]
                if cached_result.is_cache_valid():
                    step.duration = time.time() - start_time
                    step.success = True
                    step.result = cached_result.result
                    step.cached = True
                    self.pipeline_metrics["cache_hits"]["blast"] += 1
                    logger.info(f"BLAST cache hit para {sequence.id}")
                    return step
            
            # Cache miss - ejecuta BLAST con retry
            blast_result = await self._execute_blast_with_retry(sequence)
            
            # Almacena en cache
            cacheable_result = CacheableResult(
                cache_key=sequence_hash,
                result=blast_result.model_dump() if hasattr(blast_result, 'model_dump') else blast_result,
                cached_at=datetime.utcnow()
            )
            self.blast_cache[sequence_hash] = cacheable_result
            self.pipeline_metrics["cache_misses"]["blast"] += 1
            
            step.duration = time.time() - start_time
            step.success = True
            step.result = cacheable_result.result
            
            logger.info(f"BLAST completado para {sequence.id} en {step.duration:.2f}s")
            
        except Exception as e:
            step.duration = time.time() - start_time
            step.success = False
            step.error = str(e)
            logger.error(f"BLAST falló para {sequence.id}: {e}")
        
        return step

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _execute_blast_with_retry(self, sequence: SequenceData):
        """Ejecuta BLAST con retry logic."""
        return await self.blast_cb.call(
            self.blast_service.search_homology,
            sequence.sequence,
            database=self.config.blast_database,
            max_hits=self.config.max_target_seqs
        )

    async def _run_uniprot_step_with_cache(self, blast_result: Dict[str, Any]) -> PipelineStep:
        """Ejecuta el paso de consulta a UniProt con caching."""
        step = PipelineStep("UniProt", "Consulta de anotaciones funcionales")
        start_time = time.time()
        
        try:
            # Extrae IDs de proteínas del resultado de BLAST
            protein_ids = self._extract_protein_ids(blast_result)
            
            if not protein_ids:
                raise Exception("No se encontraron IDs de proteínas en resultado BLAST")
            
            # Genera hash para caching
            ids_hash = hashlib.md5(','.join(sorted(protein_ids[:self.config.uniprot_batch_size])).encode()).hexdigest()
            
            # Verifica cache
            if ids_hash in self.uniprot_cache:
                cached_result = self.uniprot_cache[ids_hash]
                if cached_result.is_cache_valid():
                    step.duration = time.time() - start_time
                    step.success = True
                    step.result = cached_result.result
                    step.cached = True
                    self.pipeline_metrics["cache_hits"]["uniprot"] += 1
                    logger.info("UniProt cache hit")
                    return step
            
            # Cache miss - ejecuta UniProt con retry
            uniprot_result = await self._execute_uniprot_with_retry(protein_ids[:self.config.uniprot_batch_size])
            
            # Almacena en cache
            cacheable_result = CacheableResult(
                cache_key=ids_hash,
                result=uniprot_result.model_dump() if hasattr(uniprot_result, 'model_dump') else uniprot_result,
                cached_at=datetime.utcnow()
            )
            self.uniprot_cache[ids_hash] = cacheable_result
            self.pipeline_metrics["cache_misses"]["uniprot"] += 1
            
            step.duration = time.time() - start_time
            step.success = True
            step.result = cacheable_result.result
            
            logger.info(f"UniProt completado en {step.duration:.2f}s")
            
        except Exception as e:
            step.duration = time.time() - start_time
            step.success = False
            step.error = str(e)
            logger.error(f"UniProt falló: {e}")
        
        return step

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _execute_uniprot_with_retry(self, protein_ids: List[str]):
        """Ejecuta UniProt con retry logic."""
        return await self.uniprot_cb.call(
            self.uniprot_service.get_protein_annotations,
            protein_ids
        )

    async def _run_preprocessing_step_with_cache(
        self, 
        sequence: SequenceData, 
        blast_result: Dict[str, Any], 
        uniprot_result: Optional[Dict[str, Any]]
    ) -> PipelineStep:
        """Ejecuta el paso de preprocesado con caching de características."""
        step = PipelineStep("Preprocesado", "Integración y preparación de datos")
        start_time = time.time()
        
        try:
            # Cache de características de secuencia
            sequence_hash = hashlib.md5(sequence.sequence.encode()).hexdigest()
            
            if sequence_hash in self.sequence_features_cache:
                cached_features = self.sequence_features_cache[sequence_hash]
                self.pipeline_metrics["cache_hits"]["features"] += 1
            else:
                cached_features = self._compute_sequence_features(sequence.sequence)
                self.sequence_features_cache[sequence_hash] = cached_features
                self.pipeline_metrics["cache_misses"]["features"] += 1
            
            # Integra todos los datos disponibles
            integrated_data = {
                "sequence_info": {
                    "id": sequence.id,
                    "length": len(sequence.sequence),
                    "sequence": sequence.sequence[:100] + "..." if len(sequence.sequence) > 100 else sequence.sequence,
                    "type": sequence.sequence_type or "unknown"
                },
                "blast_summary": self._summarize_blast_results(blast_result),
                "uniprot_annotations": self._process_uniprot_data(uniprot_result) if uniprot_result else None,
                "computed_features": cached_features
            }
            
            step.duration = time.time() - start_time
            step.success = True
            step.result = integrated_data
            
            logger.info(f"Preprocesado completado en {step.duration:.2f}s")
            
        except Exception as e:
            step.duration = time.time() - start_time
            step.success = False
            step.error = str(e)
            logger.error(f"Preprocesado falló: {e}")
        
        return step

    async def _run_llm_step_with_config(self, preprocessed_data: Dict[str, Any]) -> PipelineStep:
        """Ejecuta el paso de análisis con LLM usando configuración."""
        step = PipelineStep("LLM Analysis", "Resumen y anotaciones con IA")
        start_time = time.time()
        
        try:
            # Prepara prompt para LLM usando template configurado
            prompt = self._build_llm_prompt_with_template(preprocessed_data)
            
            # Usa circuit breaker para LLM con parámetros configurados
            llm_result = await self._execute_llm_with_retry(prompt)
            
            # Estructura resultado final
            final_result = {
                "sequence_analysis": preprocessed_data,
                "ai_insights": llm_result,
                "summary": {
                    "function_prediction": llm_result.get("function", "Unknown"),
                    "confidence": llm_result.get("confidence", 0.0),
                    "key_findings": llm_result.get("findings", []),
                    "recommendations": llm_result.get("recommendations", [])
                },
                "analysis_depth": self.config.llm_analysis_depth
            }
            
            step.duration = time.time() - start_time
            step.success = True
            step.result = final_result
            
            logger.info(f"Análisis LLM completado en {step.duration:.2f}s")
            
        except Exception as e:
            step.duration = time.time() - start_time
            step.success = False
            step.error = str(e)
            
            # Fallback: devuelve análisis sin IA
            step.result = {
                "sequence_analysis": preprocessed_data,
                "ai_insights": None,
                "summary": {
                    "function_prediction": "Analysis failed",
                    "confidence": 0.0,
                    "key_findings": ["LLM analysis unavailable"],
                    "recommendations": ["Manual review recommended"]
                }
            }
            
            logger.error(f"Análisis LLM falló: {e}")
        
        return step

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def _execute_llm_with_retry(self, prompt: str):
        """Ejecuta LLM con retry logic."""
        return await self.llm_cb.call(
            self.llm_service.analyze_sequence_data,
            prompt,
            max_tokens=self.config.llm_max_tokens,
            temperature=self.config.llm_temperature
        )

    def _build_llm_prompt_with_template(self, data: Dict[str, Any]) -> str:
        """Construye el prompt para el LLM usando template configurado."""
        sequence_info = data.get("sequence_info", {})
        blast_summary = data.get("blast_summary", {})
        uniprot_annotations = data.get("uniprot_annotations", {})
        
        # Template base según profundidad de análisis
        if self.config.llm_analysis_depth == "basic":
            template = self._get_basic_prompt_template()
        elif self.config.llm_analysis_depth == "comprehensive":
            template = self._get_comprehensive_prompt_template()
        else:  # detailed
            template = self._get_detailed_prompt_template()
        
        return template.format(
            sequence_id=sequence_info.get('id', 'N/A'),
            sequence_length=sequence_info.get('length', 'N/A'),
            sequence_type=sequence_info.get('type', 'N/A'),
            total_hits=blast_summary.get('total_hits', 0),
            avg_identity=blast_summary.get('avg_identity', 0),
            functions=', '.join(uniprot_annotations.get('functions', [])) if uniprot_annotations else 'N/A',
            pathways=', '.join(uniprot_annotations.get('pathways', [])) if uniprot_annotations else 'N/A'
        )

    def _get_basic_prompt_template(self) -> str:
        """Template básico para análisis LLM."""
        return """
        Analiza esta secuencia biológica:
        ID: {sequence_id}, Longitud: {sequence_length}, Tipo: {sequence_type}
        BLAST hits: {total_hits}, Identidad promedio: {avg_identity:.1f}%
        
        Proporciona función más probable y confianza (0-1) en formato JSON.
        """

    def _get_detailed_prompt_template(self) -> str:
        """Template detallado para análisis LLM."""
        return """
        Analiza la siguiente secuencia biológica y proporciona un resumen científico:
        
        INFORMACIÓN DE LA SECUENCIA:
        - ID: {sequence_id}
        - Longitud: {sequence_length} bases/aminoácidos
        - Tipo: {sequence_type}
        
        RESULTADOS BLAST:
        - Hits encontrados: {total_hits}
        - Identidad promedio: {avg_identity:.1f}%
        
        ANOTACIONES UNIPROT:
        - Funciones identificadas: {functions}
        - Rutas metabólicas: {pathways}
        
        Por favor proporciona:
        1. Predicción de función más probable
        2. Nivel de confianza (0-1)
        3. Hallazgos clave
        4. Recomendaciones para análisis adicionales
        
        Responde en formato JSON estructurado.
        """

    def _get_comprehensive_prompt_template(self) -> str:
        """Template comprehensivo para análisis LLM."""
        return """
        ANÁLISIS EXHAUSTIVO DE SECUENCIA BIOLÓGICA
        
        DATOS DE LA SECUENCIA:
        - Identificador: {sequence_id}
        - Longitud: {sequence_length} bases/aminoácidos
        - Tipo molecular: {sequence_type}
        
        ANÁLISIS DE HOMOLOGÍA (BLAST):
        - Total de hits: {total_hits}
        - Identidad promedio: {avg_identity:.1f}%
        
        ANOTACIONES FUNCIONALES (UniProt):
        - Funciones conocidas: {functions}
        - Vías metabólicas: {pathways}
        
        SOLICITUD DE ANÁLISIS COMPREHENSIVO:
        1. Predicción de función molecular detallada
        2. Análisis de dominios estructurales
        3. Predicción de localización celular
        4. Análisis evolutivo y filogenético
        5. Interacciones proteína-proteína potenciales
        6. Relevancia biomédica
        7. Experimentos de validación sugeridos
        8. Nivel de confianza global (0-1)
        
        Proporciona análisis en formato JSON estructurado con secciones claramente definidas.
        """

    def _calculate_cache_efficiency(self) -> Dict[str, float]:
        """Calcula la eficiencia del cache."""
        efficiency = {}
        for service in ["blast", "uniprot", "features"]:
            hits = self.pipeline_metrics["cache_hits"][service]
            misses = self.pipeline_metrics["cache_misses"][service]
            total = hits + misses
            efficiency[service] = hits / total if total > 0 else 0.0
        
        return efficiency

    # Métodos de utilidad (sin cambios significativos)
    def _extract_protein_ids(self, blast_result: Dict[str, Any]) -> List[str]:
        """Extrae IDs de proteínas del resultado BLAST."""
        try:
            hits = blast_result.get("hits", [])
            return [hit.get("accession") or hit.get("id") for hit in hits if hit.get("accession") or hit.get("id")]
        except Exception:
            return []

    def _summarize_blast_results(self, blast_result: Dict[str, Any]) -> Dict[str, Any]:
        """Resume los resultados de BLAST."""
        try:
            hits = blast_result.get("hits", [])
            return {
                "total_hits": len(hits),
                "best_hit": hits[0] if hits else None,
                "avg_identity": sum(hit.get("identity", 0) for hit in hits[:10]) / min(len(hits), 10) if hits else 0,
                "coverage_range": {
                    "min": min(hit.get("coverage", 0) for hit in hits) if hits else 0,
                    "max": max(hit.get("coverage", 0) for hit in hits) if hits else 0
                }
            }
        except Exception:
            return {"error": "Failed to summarize BLAST results"}

    def _process_uniprot_data(self, uniprot_result: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa datos de UniProt."""
        try:
            annotations = uniprot_result.get("annotations", [])
            return {
                "total_proteins": len(annotations),
                "functions": list(set(ann.get("function", "") for ann in annotations if ann.get("function"))),
                "pathways": list(set(ann.get("pathway", "") for ann in annotations if ann.get("pathway"))),
                "domains": list(set(ann.get("domain", "") for ann in annotations if ann.get("domain")))
            }
        except Exception:
            return {"error": "Failed to process UniProt data"}

    def _compute_sequence_features(self, sequence: str) -> Dict[str, Any]:
        """Calcula características computacionales de la secuencia."""
        try:
            return {
                "length": len(sequence),
                "gc_content": (sequence.count("G") + sequence.count("C")) / len(sequence) if sequence else 0,
                "composition": {
                    "A": sequence.count("A") / len(sequence) if sequence else 0,
                    "T": sequence.count("T") / len(sequence) if sequence else 0,
                    "G": sequence.count("G") / len(sequence) if sequence else 0,
                    "C": sequence.count("C") / len(sequence) if sequence else 0
                },
                "complexity": len(set(sequence)) / len(sequence) if sequence else 0
            }
        except Exception:
            return {"error": "Failed to compute sequence features"}

    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del pipeline con métricas."""
        return {
            "pipeline_name": "Scientific Pipeline v2.0 - Enhanced",
            "configuration": self.config.model_dump(),
            "services_status": {
                "blast": not await self.blast_cb.is_open(),
                "uniprot": not await self.uniprot_cb.is_open(), 
                "llm": not await self.llm_cb.is_open()
            },
            "cache_status": {
                "blast_cache_size": len(self.blast_cache),
                "uniprot_cache_size": len(self.uniprot_cache),
                "features_cache_size": len(self.sequence_features_cache)
            },
            "metrics": self.pipeline_metrics,
            "cache_efficiency": self._calculate_cache_efficiency(),
            "supported_steps": [
                "BLAST homology search (with caching)",
                "UniProt annotation retrieval (with caching)", 
                "Sequence preprocessing (with feature caching)",
                "LLM analysis with configurable depth"
            ]
        }
