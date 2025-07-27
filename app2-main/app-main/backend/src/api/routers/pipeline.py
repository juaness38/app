# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - ROUTER DEL PIPELINE CIENTÍFICO
Endpoints específicos para el pipeline científico batch.
"""
import logging
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from src.api.dependencies import get_container, get_current_user
from src.models.analysis import (
    PipelineBatchRequest, PipelineBatchResponse, SequenceData,
    HealthCheckResponse
)
from src.services.observability.structured_logger import pipeline_logger
from src.container import AppContainer

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    "/run",
    response_model=PipelineBatchResponse,
    summary="Ejecutar Pipeline Científico",
    description="Ejecuta el pipeline científico completo para un lote de secuencias: BLAST → UniProt → Preprocesado → LLM"
)
async def run_pipeline_batch(
    request: PipelineBatchRequest,
    current_user: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container)
) -> PipelineBatchResponse:
    """
    Endpoint principal para ejecutar el pipeline científico en lote.
    
    Pipeline:
    1. BLAST vs base de datos local
    2. Consulta a UniProt
    3. Preprocesado de secuencias
    4. Invocación al LLM para resumen y anotaciones
    """
    start_time = time.time()
    
    try:
        # Validación de entrada
        if not request.sequences:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere al menos una secuencia"
            )
        
        if len(request.sequences) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Máximo 50 secuencias por lote"
            )
        
        # Log estructurado del inicio
        pipeline_logger.log_service_event(
            "pipeline_batch_started",
            f"Iniciando pipeline batch con {len(request.sequences)} secuencias",
            data={
                "user_id": current_user,
                "sequence_count": len(request.sequences),
                "pipeline_config": request.pipeline_config
            }
        )
        
        # Obtiene el pipeline del contenedor
        pipeline_service = container.pipeline_service
        
        # Ejecuta el pipeline batch
        result = await pipeline_service.run_batch_analysis(request.sequences)
        
        # Convierte resultado a modelo de respuesta
        response = PipelineBatchResponse(**result)
        
        # Log estructurado del éxito
        total_time = time.time() - start_time
        pipeline_logger.log_performance(
            "pipeline_batch_completed",
            total_time * 1000,  # ms
            metadata={
                "user_id": current_user,
                "total_sequences": response.total_sequences,
                "successful": response.successful,
                "failed": response.failed
            }
        )
        
        logger.info(f"Pipeline batch completado para {current_user}: {response.successful}/{response.total_sequences} exitosos")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        total_time = time.time() - start_time
        
        # Log estructurado del error
        pipeline_logger.log_error(
            e,
            {
                "user_id": current_user,
                "sequence_count": len(request.sequences) if request.sequences else 0,
                "processing_time": total_time
            }
        )
        
        logger.error(f"Error en pipeline batch para {current_user}: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ejecutando pipeline: {str(e)}"
        )

@router.get(
    "/status",
    response_model=HealthCheckResponse,
    summary="Estado del Pipeline",
    description="Obtiene el estado actual del pipeline científico y sus componentes"
)
async def get_pipeline_status(
    current_user: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container)
) -> HealthCheckResponse:
    """Obtiene el estado completo del pipeline científico."""
    try:
        pipeline_service = container.pipeline_service
        status_info = await pipeline_service.get_pipeline_status()
        
        return HealthCheckResponse(
            service="Scientific Pipeline",
            status="healthy" if all(status_info["services_status"].values()) else "degraded",
            details=status_info,
            dependencies=status_info["services_status"]
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo estado del pipeline: {e}")
        
        return HealthCheckResponse(
            service="Scientific Pipeline",
            status="unhealthy",
            details={"error": str(e)},
            dependencies={}
        )

@router.post(
    "/validate",
    summary="Validar Secuencias",
    description="Valida un lote de secuencias antes de ejecutar el pipeline"
)
async def validate_sequences(
    sequences: List[SequenceData],
    current_user: str = Depends(get_current_user)
) -> dict:
    """Valida secuencias antes del procesamiento."""
    try:
        validation_results = []
        
        for seq in sequences:
            # Validaciones básicas
            is_valid = True
            issues = []
            
            # Longitud mínima
            if len(seq.sequence) < 10:
                is_valid = False
                issues.append("Secuencia muy corta (mínimo 10 bases/aminoácidos)")
            
            # Longitud máxima
            if len(seq.sequence) > 10000:
                is_valid = False
                issues.append("Secuencia muy larga (máximo 10,000 bases/aminoácidos)")
            
            # Caracteres válidos
            valid_chars = set('ATCGUNRYSWKMBDHV-') if _is_nucleotide(seq.sequence) else set('ACDEFGHIKLMNPQRSTVWY*-')
            invalid_chars = set(seq.sequence.upper()) - valid_chars
            
            if invalid_chars:
                is_valid = False
                issues.append(f"Caracteres inválidos: {', '.join(invalid_chars)}")
            
            validation_results.append({
                "sequence_id": seq.id,
                "valid": is_valid,
                "issues": issues,
                "sequence_type": "nucleotide" if _is_nucleotide(seq.sequence) else "protein",
                "length": len(seq.sequence)
            })
        
        # Estadísticas generales
        total_valid = sum(1 for r in validation_results if r["valid"])
        
        return {
            "total_sequences": len(sequences),
            "valid_sequences": total_valid,
            "invalid_sequences": len(sequences) - total_valid,
            "validation_results": validation_results,
            "ready_for_pipeline": total_valid > 0
        }
        
    except Exception as e:
        logger.error(f"Error validando secuencias: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en validación: {str(e)}"
        )

@router.get(
    "/tools/status",
    summary="Estado de Herramientas",
    description="Verifica el estado de todas las herramientas del pipeline"
)
async def get_tools_status(
    current_user: str = Depends(get_current_user),
    container: AppContainer = Depends(get_container)
) -> dict:
    """Verifica el estado de las herramientas del pipeline."""
    try:
        tools_status = {}
        
        # Verifica BLAST
        blast_service = container.blast_service
        tools_status["blast"] = await blast_service.health_check()
        
        # Verifica UniProt
        uniprot_service = container.uniprot_service
        tools_status["uniprot"] = await uniprot_service.health_check()
        
        # Verifica LLM
        driver_ia = container.driver_ia
        tools_status["llm"] = await driver_ia.health_check()
        
        # Estado general
        all_healthy = all(tools_status.values())
        
        return {
            "overall_status": "healthy" if all_healthy else "degraded",
            "tools": tools_status,
            "healthy_count": sum(tools_status.values()),
            "total_count": len(tools_status),
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error verificando herramientas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verificando herramientas: {str(e)}"
        )

@router.get(
    "/examples",
    summary="Ejemplos de Secuencias",
    description="Obtiene secuencias de ejemplo para probar el pipeline"
)
async def get_example_sequences() -> dict:
    """Proporciona secuencias de ejemplo para testing."""
    examples = {
        "dna_sequences": [
            {
                "id": "example_dna_1",
                "sequence": "ATGAAACGCATTAGCACCACCATTACCACCACCATCACCATTACCACAGGTAACGGTGCGGGCTGA",
                "sequence_type": "DNA",
                "description": "Gen sintético de ejemplo",
                "organism": "Synthetic"
            },
            {
                "id": "example_dna_2", 
                "sequence": "ATGGCTAGCAAAGGAGAAGAACTTTTCACTGGAGTTGTCCCAATTCTTGTTGAATTAGATGGTGATGTTAAT",
                "sequence_type": "DNA",
                "description": "Fragmento GFP",
                "organism": "Aequorea victoria"
            }
        ],
        "protein_sequences": [
            {
                "id": "example_protein_1",
                "sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
                "sequence_type": "protein",
                "description": "Proteína hipotética",
                "organism": "Escherichia coli"
            },
            {
                "id": "example_protein_2",
                "sequence": "MGSSHHHHHHSSGLVPRGSHMVSKGEELFTGVVPILVELDGDVNGHKFSVSGEGEGDATYGKLTLKF",
                "sequence_type": "protein", 
                "description": "Green Fluorescent Protein",
                "organism": "Aequorea victoria"
            }
        ]
    }
    
    return {
        "examples": examples,
        "usage": "Usa estas secuencias para probar el pipeline científico",
        "note": "Las secuencias están validadas y listas para procesamiento"
    }

def _is_nucleotide(sequence: str) -> bool:
    """Determina si una secuencia es nucleótido o proteína."""
    nucleotides = set('ATCGUN')
    sequence_clean = sequence.upper().replace(' ', '').replace('\n', '')
    nucleotide_count = sum(1 for char in sequence_clean if char in nucleotides)
    return (nucleotide_count / len(sequence_clean)) > 0.85 if sequence_clean else False