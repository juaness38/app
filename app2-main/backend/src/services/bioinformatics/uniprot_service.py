# -*- coding: utf-8 -*-
"""
ASTROFLORA - SERVICIO UNIPROT REAL
Implementación real del servicio UniProt usando su API REST
"""
import logging
import asyncio
import time
from typing import Dict, Any, List, Optional
import httpx
import json
from src.services.interfaces import IUniProtService, ICircuitBreaker
from src.models.analysis import UniProtResult
from src.core.exceptions import ToolGatewayException

class RealUniProtService(IUniProtService):
    """
    Servicio UniProt real que conecta con la API REST oficial.
    Obtiene anotaciones funcionales de proteínas.
    """
    
    def __init__(self, circuit_breaker_factory):
        self.circuit_breaker_factory = circuit_breaker_factory
        self.circuit_breaker = circuit_breaker_factory("uniprot_api")
        self.logger = logging.getLogger(__name__)
        
        # Cliente HTTP para UniProt API
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={
                "User-Agent": "Astroflora/1.0 (astroflora@example.com)",
                "Accept": "application/json"
            }
        )
        
        # URLs de la API UniProt
        self.base_url = "https://rest.uniprot.org"
        self.search_url = f"{self.base_url}/uniprotkb/search"
        self.retrieve_url = f"{self.base_url}/uniprotkb"
        
        self.logger.info("🔬 UniProt Service Real inicializado")

    async def get_protein_annotations(self, protein_ids: List[str]) -> UniProtResult:
        """
        Obtiene anotaciones de proteínas usando IDs (accessions).
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"📋 Obteniendo anotaciones UniProt para {len(protein_ids)} proteínas")
            
            if not protein_ids:
                raise ToolGatewayException("Lista de IDs de proteínas vacía")
            
            # Filtra y limpia IDs
            clean_ids = self._clean_protein_ids(protein_ids)
            
            if not clean_ids:
                raise ToolGatewayException("No se encontraron IDs válidos")
            
            # Ejecuta consulta usando circuit breaker
            annotations = await self.circuit_breaker.call(
                self._fetch_uniprot_entries,
                clean_ids
            )
            
            search_time = time.time() - start_time
            
            result = UniProtResult(
                query_ids=clean_ids,
                total_found=len(annotations),
                annotations=annotations,
                search_time=search_time,
                database_version="2024.1"
            )
            
            self.logger.info(f"✅ UniProt completado: {len(annotations)} anotaciones en {search_time:.2f}s")
            return result
            
        except Exception as e:
            search_time = time.time() - start_time
            self.logger.error(f"❌ Error en UniProt: {e}")
            
            # Fallback con resultado simulado
            return await self._fallback_uniprot_result(protein_ids, search_time)

    def _clean_protein_ids(self, protein_ids: List[str]) -> List[str]:
        """Limpia y valida IDs de proteínas."""
        clean_ids = []
        
        for protein_id in protein_ids:
            if not protein_id:
                continue
                
            # Limpia el ID
            clean_id = protein_id.strip().upper()
            
            # Valida formato básico (UniProt accession patterns)
            if (len(clean_id) >= 6 and 
                (clean_id.startswith(('P', 'Q', 'O', 'A', 'B', 'C')) or 
                 clean_id.startswith(('NP_', 'XP_', 'WP_')))):
                clean_ids.append(clean_id)
        
        return clean_ids[:50]  # Limita a 50 para evitar sobrecarga

    async def _fetch_uniprot_entries(self, protein_ids: List[str]) -> List[Dict[str, Any]]:
        """Obtiene entradas de UniProt via API REST."""
        annotations = []
        
        try:
            # Método 1: Bulk retrieval (más eficiente)
            if len(protein_ids) > 1:
                annotations = await self._bulk_retrieve_entries(protein_ids)
            else:
                # Método 2: Individual retrieval
                annotations = await self._individual_retrieve_entries(protein_ids)
            
            return annotations
            
        except Exception as e:
            self.logger.error(f"Error fetching UniProt entries: {e}")
            raise

    async def _bulk_retrieve_entries(self, protein_ids: List[str]) -> List[Dict[str, Any]]:
        """Recuperación bulk de entradas UniProt."""
        try:
            # Convierte IDs a query string
            query = " OR ".join([f"accession:{pid}" for pid in protein_ids])
            
            params = {
                "query": query,
                "format": "json",
                "size": len(protein_ids),
                "fields": "accession,protein_name,gene_names,organism_name,length,cc_function,ft_domain,go,cc_pathway,keywords"
            }
            
            self.logger.info(f"🌐 Consultando UniProt bulk: {len(protein_ids)} IDs")
            
            response = await self.http_client.get(
                self.search_url, 
                params=params,
                timeout=30.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Procesa resultados
            annotations = []
            for entry in data.get("results", []):
                annotation = self._process_uniprot_entry(entry)
                if annotation:
                    annotations.append(annotation)
            
            return annotations
            
        except Exception as e:
            self.logger.warning(f"⚠️ Bulk retrieval falló: {e}, intentando individual")
            return await self._individual_retrieve_entries(protein_ids)

    async def _individual_retrieve_entries(self, protein_ids: List[str]) -> List[Dict[str, Any]]:
        """Recuperación individual de entradas UniProt."""
        annotations = []
        
        # Procesa en lotes pequeños para evitar rate limiting
        batch_size = 5
        
        for i in range(0, len(protein_ids), batch_size):
            batch = protein_ids[i:i + batch_size]
            
            # Procesa batch en paralelo
            tasks = [self._fetch_single_entry(pid) for pid in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, dict):
                    annotations.append(result)
                elif isinstance(result, Exception):
                    self.logger.warning(f"Error en entrada individual: {result}")
            
            # Rate limiting: pausa entre lotes
            if i + batch_size < len(protein_ids):
                await asyncio.sleep(0.5)
        
        return annotations

    async def _fetch_single_entry(self, protein_id: str) -> Dict[str, Any]:
        """Obtiene una entrada individual de UniProt."""
        try:
            url = f"{self.retrieve_url}/{protein_id}"
            params = {
                "format": "json",
                "fields": "accession,protein_name,gene_names,organism_name,length,cc_function,ft_domain,go,cc_pathway,keywords"
            }
            
            response = await self.http_client.get(url, params=params, timeout=10.0)
            
            if response.status_code == 200:
                entry_data = response.json()
                return self._process_uniprot_entry(entry_data)
            elif response.status_code == 404:
                self.logger.debug(f"Proteína no encontrada: {protein_id}")
                return None
            else:
                response.raise_for_status()
                
        except Exception as e:
            self.logger.warning(f"Error obteniendo {protein_id}: {e}")
            return None

    def _process_uniprot_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Procesa una entrada de UniProt y extrae información relevante."""
        try:
            processed = {
                "accession": entry.get("primaryAccession", ""),
                "protein_name": "",
                "gene_names": [],
                "organism": entry.get("organism", {}).get("scientificName", ""),
                "length": entry.get("sequence", {}).get("length", 0),
                "function": "",
                "domains": [],
                "go_terms": [],
                "pathways": [],
                "keywords": []
            }
            
            # Nombre de proteína
            protein_name = entry.get("proteinDescription", {})
            if "recommendedName" in protein_name:
                processed["protein_name"] = protein_name["recommendedName"].get("fullName", {}).get("value", "")
            elif "submissionNames" in protein_name:
                submission_names = protein_name["submissionNames"]
                if submission_names:
                    processed["protein_name"] = submission_names[0].get("fullName", {}).get("value", "")
            
            # Nombres de genes
            genes = entry.get("genes", [])
            for gene in genes:
                if "geneName" in gene:
                    processed["gene_names"].append(gene["geneName"]["value"])
            
            # Función
            comments = entry.get("comments", [])
            for comment in comments:
                if comment.get("commentType") == "FUNCTION":
                    texts = comment.get("texts", [])
                    if texts:
                        processed["function"] = texts[0].get("value", "")[:500]  # Limita longitud
                        break
            
            # Dominios
            features = entry.get("features", [])
            for feature in features:
                if feature.get("type") == "DOMAIN":
                    domain_desc = feature.get("description", "")
                    if domain_desc:
                        processed["domains"].append(domain_desc)
            
            # Términos GO
            db_references = entry.get("uniProtKBCrossReferences", [])
            for ref in db_references:
                if ref.get("database") == "GO":
                    go_term = {
                        "id": ref.get("id", ""),
                        "description": ""
                    }
                    # Busca descripción en propiedades
                    properties = ref.get("properties", [])
                    for prop in properties:
                        if prop.get("key") == "GoTerm":
                            go_term["description"] = prop.get("value", "")
                            break
                    processed["go_terms"].append(go_term)
            
            # Keywords
            keywords = entry.get("keywords", [])
            for keyword in keywords:
                processed["keywords"].append(keyword.get("name", ""))
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Error procesando entrada UniProt: {e}")
            return None

    async def search_by_function(self, function_term: str) -> List[Dict[str, Any]]:
        """Busca proteínas por término funcional."""
        try:
            self.logger.info(f"🔍 Buscando proteínas por función: {function_term}")
            
            params = {
                "query": f"cc_function:{function_term}",
                "format": "json",
                "size": 20,
                "fields": "accession,protein_name,gene_names,organism_name,cc_function"
            }
            
            response = await self.http_client.get(
                self.search_url,
                params=params,
                timeout=20.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            results = []
            for entry in data.get("results", []):
                processed = self._process_uniprot_entry(entry)
                if processed:
                    results.append(processed)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda funcional: {e}")
            return []

    async def get_protein_details(self, protein_id: str) -> Dict[str, Any]:
        """Obtiene detalles completos de una proteína."""
        try:
            annotation_result = await self.get_protein_annotations([protein_id])
            
            if annotation_result.annotations:
                return annotation_result.annotations[0]
            else:
                return {}
                
        except Exception as e:
            self.logger.error(f"Error obteniendo detalles de {protein_id}: {e}")
            return {}

    async def _fallback_uniprot_result(
        self, 
        protein_ids: List[str], 
        search_time: float
    ) -> UniProtResult:
        """Resultado simulado cuando UniProt real falla."""
        self.logger.warning("⚠️ Usando resultado UniProt simulado (fallback)")
        
        simulated_annotations = []
        
        for i, protein_id in enumerate(protein_ids[:10]):
            simulated_annotations.append({
                "accession": protein_id,
                "protein_name": f"Hypothetical protein {i+1}",
                "gene_names": [f"gene{i+1}"],
                "organism": "Organism species",
                "length": 250 + (i * 50),
                "function": f"Putative function {i+1} - involved in cellular processes",
                "domains": [f"Domain_{i+1}", f"Functional_domain_{i+1}"],
                "go_terms": [
                    {"id": f"GO:000000{i+1}", "description": f"Biological process {i+1}"}
                ],
                "pathways": [f"Metabolic pathway {i+1}"],
                "keywords": ["Hypothetical", "Predicted", f"Function{i+1}"]
            })
        
        return UniProtResult(
            query_ids=protein_ids,
            total_found=len(simulated_annotations),
            annotations=simulated_annotations,
            search_time=search_time,
            database_version="Simulated"
        )

    async def health_check(self) -> bool:
        """Verifica si UniProt API está accesible."""
        try:
            response = await self.http_client.get(
                self.base_url, 
                timeout=5.0
            )
            return response.status_code == 200
        except:
            return False

    async def close(self):
        """Cierra el cliente HTTP."""
        if self.http_client:
            await self.http_client.aclose()