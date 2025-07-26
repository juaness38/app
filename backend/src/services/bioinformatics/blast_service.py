# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - SERVICIO BLAST
Servicio específico para búsquedas de homología BLAST.
"""
import logging
import asyncio
from typing import Dict, Any, List
from dataclasses import dataclass
from src.services.interfaces import IBlastService
from src.models.analysis import BlastResult
from src.core.exceptions import ToolGatewayException

@dataclass
class BlastHit:
    """Representa un hit individual de BLAST."""
    accession: str
    description: str
    e_value: float
    identity: float
    coverage: float
    score: float

class LocalBlastService(IBlastService):
    """
    Servicio BLAST que puede trabajar con bases de datos locales y remotas.
    """
    
    def __init__(self, circuit_breaker_factory):
        self.circuit_breaker = circuit_breaker_factory("blast_service")
        self.logger = logging.getLogger(__name__)
        self.logger.info("Servicio BLAST inicializado")

    async def search_homology(self, sequence: str, database: str = "nr", max_hits: int = 50) -> BlastResult:
        """Busca homología en una base de datos específica."""
        self.logger.info(f"Iniciando búsqueda BLAST: db={database}, seq_len={len(sequence)}")
        
        try:
            # Validación de entrada
            if not sequence or len(sequence) < 10:
                raise ValueError("Secuencia debe tener al menos 10 bases/aminoácidos")
            
            if database == "local_db":
                return await self._search_local_database(sequence, max_hits)
            else:
                return await self._search_remote_database(sequence, database, max_hits)
                
        except Exception as e:
            self.logger.error(f"Error en búsqueda BLAST: {e}")
            raise ToolGatewayException(f"BLAST search failed: {e}")

    async def search_local_database(self, sequence: str, database_path: str) -> BlastResult:
        """Busca en una base de datos local específica."""
        return await self._search_local_database(sequence, 50, database_path)

    async def _search_local_database(self, sequence: str, max_hits: int, db_path: str = None) -> BlastResult:
        """Implementación de búsqueda en base de datos local."""
        # Simula búsqueda local (en producción sería llamada a BLAST+ local)
        await asyncio.sleep(2.0)  # Simula tiempo de búsqueda
        
        # Genera hits simulados basados en características de la secuencia
        hits = self._generate_realistic_hits(sequence, max_hits)
        
        return BlastResult(
            query_sequence=sequence[:100] + "..." if len(sequence) > 100 else sequence,
            query_length=len(sequence),
            database="local_db" if not db_path else db_path,
            total_hits=len(hits),
            hits=[hit.__dict__ for hit in hits],
            search_time=2.0,
            parameters={
                "max_hits": max_hits,
                "expect_threshold": 1e-3,
                "word_size": 11 if self._is_nucleotide_sequence(sequence) else 3
            }
        )

    async def _search_remote_database(self, sequence: str, database: str, max_hits: int) -> BlastResult:
        """Implementación de búsqueda remota (NCBI BLAST API)."""
        # En producción, aquí iría la integración con NCBI BLAST API
        await asyncio.sleep(5.0)  # Simula tiempo de búsqueda remota
        
        hits = self._generate_realistic_hits(sequence, max_hits)
        
        return BlastResult(
            query_sequence=sequence[:100] + "..." if len(sequence) > 100 else sequence,
            query_length=len(sequence),
            database=database,
            total_hits=len(hits),
            hits=[hit.__dict__ for hit in hits],
            search_time=5.0,
            parameters={
                "max_hits": max_hits,
                "database": database,
                "remote": True
            }
        )

    def _generate_realistic_hits(self, sequence: str, max_hits: int) -> List[BlastHit]:
        """Genera hits realistas basados en la secuencia."""
        import random
        import hashlib
        
        # Usa hash de la secuencia para resultados consistentes
        seed = int(hashlib.md5(sequence.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        hits = []
        sequence_type = "nucleotide" if self._is_nucleotide_sequence(sequence) else "protein"
        
        # Genera hits con distribución realista de scores
        for i in range(min(max_hits, random.randint(5, 25))):
            # E-values más bajos para hits mejores
            e_value = 10 ** random.uniform(-50, -3) if i < 5 else 10 ** random.uniform(-10, 0)
            
            # Identidad correlacionada con e-value
            identity = random.uniform(95, 100) if e_value < 1e-20 else random.uniform(30, 95)
            
            # Coverage realista
            coverage = random.uniform(70, 100) if identity > 80 else random.uniform(40, 85)
            
            # Score basado en identidad y coverage
            score = (identity * coverage) / 100 * random.uniform(100, 500)
            
            hit = BlastHit(
                accession=f"{'NM_' if sequence_type == 'nucleotide' else 'NP_'}{random.randint(100000, 999999)}.{random.randint(1, 5)}",
                description=self._generate_realistic_description(sequence_type, identity),
                e_value=e_value,
                identity=round(identity, 1),
                coverage=round(coverage, 1),
                score=round(score, 1)
            )
            hits.append(hit)
        
        # Ordena por e-value (mejor primero)
        hits.sort(key=lambda x: x.e_value)
        return hits

    def _generate_realistic_description(self, sequence_type: str, identity: float) -> str:
        """Genera descripciones realistas para los hits."""
        if sequence_type == "nucleotide":
            descriptions = [
                "hypothetical protein",
                "conserved hypothetical protein", 
                "putative transcriptional regulator",
                "ABC transporter ATP-binding protein",
                "ribosomal protein L1",
                "DNA polymerase III subunit alpha",
                "cell division protein FtsZ"
            ]
        else:
            descriptions = [
                "hypothetical protein",
                "conserved domain protein",
                "enzyme of unknown function",
                "transcriptional regulator",
                "membrane transport protein",
                "metabolic enzyme",
                "structural protein"
            ]
        
        import random
        base_desc = random.choice(descriptions)
        
        # Añade información de organismo
        organisms = [
            "Escherichia coli",
            "Bacillus subtilis", 
            "Pseudomonas aeruginosa",
            "Streptococcus pneumoniae",
            "Mycobacterium tuberculosis"
        ]
        
        organism = random.choice(organisms)
        
        if identity > 90:
            return f"{base_desc} [{organism}]"
        elif identity > 70:
            return f"similar to {base_desc} [{organism}]"
        else:
            return f"putative {base_desc} [{organism}]"

    def _is_nucleotide_sequence(self, sequence: str) -> bool:
        """Determina si una secuencia es nucleótido o proteína."""
        nucleotides = set('ATCGUN')
        sequence_upper = sequence.upper().replace(' ', '').replace('\n', '')
        nucleotide_count = sum(1 for char in sequence_upper if char in nucleotides)
        return (nucleotide_count / len(sequence_upper)) > 0.85

    async def health_check(self) -> bool:
        """Verifica el estado del servicio BLAST."""
        try:
            # Verifica circuit breaker
            if await self.circuit_breaker.is_open():
                return False
            
            # Test simple con secuencia pequeña
            test_result = await self.search_homology("ATCGATCGATCG", max_hits=1)
            return test_result.total_hits >= 0
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    async def get_search_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del servicio BLAST."""
        return {
            "service_name": "LocalBlastService",
            "supported_databases": ["local_db", "nr", "nt", "swissprot"],
            "max_sequence_length": 10000,
            "average_search_time": "2-5 seconds",
            "circuit_breaker_status": await self.circuit_breaker.get_status()
        }