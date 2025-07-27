# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - PIPELINE CIENTÍFICO
Pipeline científico específico para análisis de secuencias biológicas.
BLAST → UniProt → Preprocesado → LLM
"""
import logging
import asyncio
import time
from typing import Dict, Any, List, Optional
import httpx
from dataclasses import dataclass
from src.services.interfaces import IPipelineService, IBlastService, IUniProtService, ILLMService
from src.core.exceptions import PipelineException
from src.models.analysis import PipelineResult, SequenceData, BlastResult, UniProtResult, LLMResult

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

class ScientificPipeline(IPipelineService):
    """
    Pipeline científico principal para análisis de secuencias.
    Implementa el flujo: BLAST vs base de datos local → UniProt → Preprocesado → LLM
    """
    
    def __init__(
        self,
        blast_service: IBlastService,
        uniprot_service: IUniProtService,
        llm_service: ILLMService,
        circuit_breaker_factory
    ):
        self.blast_service = blast_service
        self.uniprot_service = uniprot_service
        self.llm_service = llm_service
        self.circuit_breaker_factory = circuit_breaker_factory
        
        # Circuit Breakers para servicios externos
        self.blast_cb = circuit_breaker_factory("blast_pipeline")
        self.uniprot_cb = circuit_breaker_factory("uniprot_pipeline")
        self.llm_cb = circuit_breaker_factory("llm_pipeline")
        
        logger.info("Pipeline Científico inicializado")

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
            # Procesa cada secuencia en el pipeline
            for i, sequence in enumerate(sequences):
                logger.info(f"Procesando secuencia {i+1}/{len(sequences)}: {sequence.id}")
                
                try:
                    result = await self._run_single_sequence_pipeline(sequence)
                    pipeline_results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error procesando secuencia {sequence.id}: {e}")
                    # Continúa con las demás secuencias
                    pipeline_results.append(PipelineResult(
                        sequence_id=sequence.id,
                        success=False,
                        error=str(e),
                        steps=[],
                        processing_time=0.0
                    ))
            
            total_time = time.time() - start_time
            
            # Estadísticas del batch
            successful = sum(1 for r in pipeline_results if r.success)
            failed = len(pipeline_results) - successful
            
            return {
                "batch_id": f"batch_{int(start_time)}",
                "total_sequences": len(sequences),
                "successful": successful,
                "failed": failed,
                "total_processing_time": total_time,
                "average_time_per_sequence": total_time / len(sequences) if sequences else 0,
                "results": [result.model_dump() for result in pipeline_results]
            }
            
        except Exception as e:
            logger.error(f"Error crítico en pipeline batch: {e}")
            raise PipelineException(f"Fallo crítico en pipeline: {e}")

    async def _run_single_sequence_pipeline(self, sequence: SequenceData) -> PipelineResult:
        """Ejecuta el pipeline completo para una secuencia individual."""
        
        start_time = time.time()
        steps = []
        
        try:
            # Paso 1: BLAST vs base de datos local
            blast_step = await self._run_blast_step(sequence)
            steps.append(blast_step)
            
            if not blast_step.success:
                raise PipelineException(f"BLAST falló: {blast_step.error}")
            
            # Paso 2: Consulta a UniProt
            uniprot_step = await self._run_uniprot_step(blast_step.result)
            steps.append(uniprot_step)
            
            if not uniprot_step.success:
                logger.warning(f"UniProt falló, continuando: {uniprot_step.error}")
            
            # Paso 3: Preprocesado de secuencias
            preprocessing_step = await self._run_preprocessing_step(
                sequence, blast_step.result, uniprot_step.result
            )
            steps.append(preprocessing_step)
            
            if not preprocessing_step.success:
                raise PipelineException(f"Preprocesado falló: {preprocessing_step.error}")
            
            # Paso 4: Invocación al LLM
            llm_step = await self._run_llm_step(preprocessing_step.result)
            steps.append(llm_step)
            
            if not llm_step.success:
                logger.warning(f"LLM falló, usando resultados parciales: {llm_step.error}")
            
            total_time = time.time() - start_time
            
            return PipelineResult(
                sequence_id=sequence.id,
                success=True,
                steps=steps,
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
                steps=steps,
                processing_time=total_time
            )

    async def _run_blast_step(self, sequence: SequenceData) -> PipelineStep:
        """Ejecuta el paso de BLAST."""
        step = PipelineStep("BLAST", "Búsqueda de homología en base de datos local")
        start_time = time.time()
        
        try:
            # Usa circuit breaker para BLAST
            blast_result = await self.blast_cb.call(
                self.blast_service.search_homology,
                sequence.sequence,
                database="local_db",
                max_hits=50
            )
            
            step.duration = time.time() - start_time
            step.success = True
            step.result = blast_result.model_dump() if hasattr(blast_result, 'model_dump') else blast_result
            
            logger.info(f"BLAST completado para {sequence.id} en {step.duration:.2f}s")
            
        except Exception as e:
            step.duration = time.time() - start_time
            step.success = False
            step.error = str(e)
            logger.error(f"BLAST falló para {sequence.id}: {e}")
        
        return step

    async def _run_uniprot_step(self, blast_result: Dict[str, Any]) -> PipelineStep:
        """Ejecuta el paso de consulta a UniProt."""
        step = PipelineStep("UniProt", "Consulta de anotaciones funcionales")
        start_time = time.time()
        
        try:
            # Extrae IDs de proteínas del resultado de BLAST
            protein_ids = self._extract_protein_ids(blast_result)
            
            if not protein_ids:
                raise Exception("No se encontraron IDs de proteínas en resultado BLAST")
            
            # Usa circuit breaker para UniProt
            uniprot_result = await self.uniprot_cb.call(
                self.uniprot_service.get_protein_annotations,
                protein_ids[:10]  # Limita a 10 proteínas para evitar timeout
            )
            
            step.duration = time.time() - start_time
            step.success = True
            step.result = uniprot_result.model_dump() if hasattr(uniprot_result, 'model_dump') else uniprot_result
            
            logger.info(f"UniProt completado en {step.duration:.2f}s")
            
        except Exception as e:
            step.duration = time.time() - start_time
            step.success = False
            step.error = str(e)
            logger.error(f"UniProt falló: {e}")
        
        return step

    async def _run_preprocessing_step(
        self, 
        sequence: SequenceData, 
        blast_result: Dict[str, Any], 
        uniprot_result: Optional[Dict[str, Any]]
    ) -> PipelineStep:
        """Ejecuta el paso de preprocesado."""
        step = PipelineStep("Preprocesado", "Integración y preparación de datos")
        start_time = time.time()
        
        try:
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
                "computed_features": self._compute_sequence_features(sequence.sequence)
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

    async def _run_llm_step(self, preprocessed_data: Dict[str, Any]) -> PipelineStep:
        """Ejecuta el paso de análisis con LLM."""
        step = PipelineStep("LLM Analysis", "Resumen y anotaciones con IA")
        start_time = time.time()
        
        try:
            # Prepara prompt para LLM
            prompt = self._build_llm_prompt(preprocessed_data)
            
            # Usa circuit breaker para LLM
            llm_result = await self.llm_cb.call(
                self.llm_service.analyze_sequence_data,
                prompt,
                max_tokens=1000,
                temperature=0.3
            )
            
            # Estructura resultado final
            final_result = {
                "sequence_analysis": preprocessed_data,
                "ai_insights": llm_result,
                "summary": {
                    "function_prediction": llm_result.get("function", "Unknown"),
                    "confidence": llm_result.get("confidence", 0.0),
                    "key_findings": llm_result.get("findings", []),
                    "recommendations": llm_result.get("recommendations", [])
                }
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

    def _build_llm_prompt(self, data: Dict[str, Any]) -> str:
        """Construye el prompt para el LLM."""
        sequence_info = data.get("sequence_info", {})
        blast_summary = data.get("blast_summary", {})
        uniprot_annotations = data.get("uniprot_annotations", {})
        
        prompt = f"""
        Analiza la siguiente secuencia biológica y proporciona un resumen científico:
        
        INFORMACIÓN DE LA SECUENCIA:
        - ID: {sequence_info.get('id', 'N/A')}
        - Longitud: {sequence_info.get('length', 'N/A')} bases/aminoácidos
        - Tipo: {sequence_info.get('type', 'N/A')}
        
        RESULTADOS BLAST:
        - Hits encontrados: {blast_summary.get('total_hits', 0)}
        - Identidad promedio: {blast_summary.get('avg_identity', 0):.1f}%
        
        ANOTACIONES UNIPROT:
        - Funciones identificadas: {', '.join(uniprot_annotations.get('functions', [])) if uniprot_annotations else 'N/A'}
        - Rutas metabólicas: {', '.join(uniprot_annotations.get('pathways', [])) if uniprot_annotations else 'N/A'}
        
        Por favor proporciona:
        1. Predicción de función más probable
        2. Nivel de confianza (0-1)
        3. Hallazgos clave
        4. Recomendaciones para análisis adicionales
        
        Responde en formato JSON estructurado.
        """
        
        return prompt.strip()

    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del pipeline."""
        return {
            "pipeline_name": "Scientific Pipeline v1.0",
            "services_status": {
                "blast": not await self.blast_cb.is_open(),
                "uniprot": not await self.uniprot_cb.is_open(), 
                "llm": not await self.llm_cb.is_open()
            },
            "supported_steps": [
                "BLAST homology search",
                "UniProt annotation retrieval", 
                "Sequence preprocessing",
                "LLM analysis and summarization"
            ]
        }