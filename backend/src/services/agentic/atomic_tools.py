# -*- coding: utf-8 -*-
"""
ASTROFLORA - HERRAMIENTAS ATÓMICAS AGÉNTICAS
Herramientas atómicas que el DriverIA puede orquestar dinámicamente.
FASE 1: Coexistencia y Estabilización - Preparación para la descomposición.
"""
import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from datetime import datetime
import time

from src.models.analysis import ToolResult, EnhancedSequenceData

logger = logging.getLogger(__name__)

# ============================================================================
# HERRAMIENTAS ATÓMICAS - BUILDING BLOCKS DEL DRIVERIA
# ============================================================================

class AtomicTool(ABC):
    """Base para herramientas atómicas que el DriverIA puede usar."""

    def __init__(self, name: str, description: str, scientific_purpose: str = ""):
        self.name = name
        self.description = description
        self.scientific_purpose = scientific_purpose
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.success_count = 0

    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Ejecuta la herramienta con parámetros dados."""
        pass

    @abstractmethod
    def get_parameter_schema(self) -> Dict[str, Any]:
        """Retorna el schema de parámetros esperados."""
        pass

    @abstractmethod
    async def assess_applicability(self, context: Dict[str, Any]) -> float:
        """¿Qué tan apropiada es esta herramienta para este contexto?"""
        pass

    def get_scientific_metadata(self) -> Dict[str, Any]:
        """Retorna metadatos científicos de la herramienta."""
        return {
            "name": self.name,
            "description": self.description,
            "scientific_purpose": self.scientific_purpose,
            "execution_stats": {
                "total_executions": self.execution_count,
                "successful_executions": self.success_count,
                "success_rate": self.success_count / self.execution_count if self.execution_count > 0 else 0.0,
                "average_execution_time": self.total_execution_time / self.execution_count if self.execution_count > 0 else 0.0
            }
        }

    async def _track_execution(self, func, *args, **kwargs):
        """Wrapper para rastrear ejecuciones."""
        start_time = time.time()
        self.execution_count += 1
        
        try:
            result = await func(*args, **kwargs)
            if result.success:
                self.success_count += 1
            return result
        finally:
            execution_time = time.time() - start_time
            self.total_execution_time += execution_time

class BlastSearchTool(AtomicTool):
    """Herramienta atómica para búsqueda BLAST."""

    def __init__(self, blast_service, circuit_breaker_factory):
        super().__init__(
            name="blast_search",
            description="Búsqueda de homología usando BLAST",
            scientific_purpose="Identifica secuencias similares en bases de datos para inferir función y relaciones evolutivas"
        )
        self.blast_service = blast_service
        self.blast_cb = circuit_breaker_factory("blast_atomic")

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Ejecuta búsqueda BLAST."""
        return await self._track_execution(self._execute_blast, parameters)

    async def _execute_blast(self, parameters: Dict[str, Any]) -> ToolResult:
        try:
            sequence = parameters.get("sequence")
            database = parameters.get("database", "nr")
            max_hits = parameters.get("max_hits", 50)
            evalue = parameters.get("evalue", 1e-10)

            if not sequence:
                raise ValueError("Parámetro 'sequence' requerido")

            # Validación de secuencia
            if len(sequence) < 10:
                raise ValueError("Secuencia demasiado corta para BLAST (mínimo 10 caracteres)")

            result = await self.blast_cb.call(
                self.blast_service.search_homology,
                sequence,
                database=database,
                max_hits=max_hits
            )

            # Enriquece el resultado con metadatos científicos
            enriched_result = {
                "raw_result": result.dict() if hasattr(result, 'dict') else result,
                "scientific_summary": self._analyze_blast_result(result, sequence),
                "parameters_used": {
                    "database": database,
                    "max_hits": max_hits,
                    "evalue": evalue,
                    "sequence_length": len(sequence)
                }
            }

            return ToolResult(
                tool_name=self.name,
                success=True,
                result=enriched_result,
                execution_time_ms=None  # Se asigna en _track_execution
            )

        except Exception as e:
            logger.error(f"BlastSearchTool falló: {e}")
            return ToolResult(
                tool_name=self.name,
                success=False,
                error_message=str(e)
            )

    def _analyze_blast_result(self, result, query_sequence: str) -> Dict[str, Any]:
        """Analiza científicamente el resultado de BLAST."""
        try:
            hits = result.get("hits", []) if isinstance(result, dict) else getattr(result, 'hits', [])
            
            if not hits:
                return {
                    "significance": "No significant homologs found",
                    "evolutionary_inference": "Possibly novel or highly divergent sequence",
                    "functional_prediction_confidence": "Low"
                }

            best_hit = hits[0] if hits else {}
            identity_scores = [hit.get("identity", 0) for hit in hits[:10]]
            avg_identity = sum(identity_scores) / len(identity_scores) if identity_scores else 0

            # Análisis científico basado en identidad
            if avg_identity > 90:
                significance = "High sequence conservation"
                evolutionary_inference = "Likely orthologs with conserved function"
                confidence = "High"
            elif avg_identity > 70:
                significance = "Moderate sequence conservation"
                evolutionary_inference = "Probable functional homologs"
                confidence = "Medium-High"
            elif avg_identity > 40:
                significance = "Distant homology detected"
                evolutionary_inference = "Possible functional relationship"
                confidence = "Medium"
            else:
                significance = "Weak or no homology"
                evolutionary_inference = "Uncertain functional relationship"
                confidence = "Low"

            return {
                "total_hits": len(hits),
                "best_identity": best_hit.get("identity", 0),
                "average_identity": avg_identity,
                "significance": significance,
                "evolutionary_inference": evolutionary_inference,
                "functional_prediction_confidence": confidence,
                "taxonomic_distribution": self._analyze_taxonomic_distribution(hits)
            }

        except Exception as e:
            return {"analysis_error": str(e)}

    def _analyze_taxonomic_distribution(self, hits: List[Dict]) -> Dict[str, Any]:
        """Analiza la distribución taxonómica de los hits."""
        try:
            organisms = [hit.get("organism", "Unknown") for hit in hits[:20]]
            organism_counts = {}
            for org in organisms:
                organism_counts[org] = organism_counts.get(org, 0) + 1
            
            return {
                "unique_organisms": len(organism_counts),
                "most_common": max(organism_counts.items(), key=lambda x: x[1]) if organism_counts else ("Unknown", 0),
                "distribution": organism_counts
            }
        except:
            return {"distribution_error": "Could not analyze taxonomic distribution"}

    async def assess_applicability(self, context: Dict[str, Any]) -> float:
        """Evalúa qué tan aplicable es BLAST para el contexto dado."""
        try:
            sequence_info = context.get("sequence_info", {})
            sequence_length = sequence_info.get("length", 0)
            sequence_type = sequence_info.get("type", "unknown")
            
            # BLAST es más efectivo con secuencias más largas
            length_score = min(1.0, sequence_length / 100.0) if sequence_length > 0 else 0.0
            
            # BLAST funciona bien con todos los tipos de secuencia
            type_score = 1.0 if sequence_type in ["protein", "dna", "rna"] else 0.7
            
            # Si ya hay resultados BLAST, menor necesidad
            has_blast_results = "blast_results" in context
            redundancy_score = 0.3 if has_blast_results else 1.0
            
            return length_score * type_score * redundancy_score
            
        except:
            return 0.5  # Puntuación neutra si no se puede evaluar

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sequence": {"type": "string", "description": "Secuencia biológica"},
                "database": {"type": "string", "default": "nr", "description": "Base de datos BLAST"},
                "max_hits": {"type": "integer", "default": 50, "description": "Máximo número de hits"},
                "evalue": {"type": "number", "default": 1e-10, "description": "E-value threshold"}
            },
            "required": ["sequence"]
        }

class UniProtAnnotationTool(AtomicTool):
    """Herramienta atómica para anotaciones UniProt."""

    def __init__(self, uniprot_service, circuit_breaker_factory):
        super().__init__(
            name="uniprot_annotations",
            description="Obtiene anotaciones funcionales de UniProt",
            scientific_purpose="Recopila información funcional curada experimentalmente sobre proteínas"
        )
        self.uniprot_service = uniprot_service
        self.uniprot_cb = circuit_breaker_factory("uniprot_atomic")

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Obtiene anotaciones de UniProt."""
        return await self._track_execution(self._execute_uniprot, parameters)

    async def _execute_uniprot(self, parameters: Dict[str, Any]) -> ToolResult:
        try:
            protein_ids = parameters.get("protein_ids", [])
            fields = parameters.get("fields", ["function", "pathway"])

            if not protein_ids:
                raise ValueError("Parámetro 'protein_ids' requerido")

            # Limita a un número razonable de IDs
            protein_ids = protein_ids[:20]

            result = await self.uniprot_cb.call(
                self.uniprot_service.get_protein_annotations,
                protein_ids
            )

            # Enriquece el resultado con análisis científico
            enriched_result = {
                "raw_result": result.dict() if hasattr(result, 'dict') else result,
                "scientific_analysis": self._analyze_uniprot_annotations(result),
                "parameters_used": {
                    "protein_ids_count": len(protein_ids),
                    "fields_requested": fields
                }
            }

            return ToolResult(
                tool_name=self.name,
                success=True,
                result=enriched_result
            )

        except Exception as e:
            logger.error(f"UniProtAnnotationTool falló: {e}")
            return ToolResult(
                tool_name=self.name,
                success=False,
                error_message=str(e)
            )

    def _analyze_uniprot_annotations(self, result) -> Dict[str, Any]:
        """Analiza científicamente las anotaciones de UniProt."""
        try:
            annotations = result.get("annotations", []) if isinstance(result, dict) else getattr(result, 'annotations', [])
            
            if not annotations:
                return {
                    "annotation_quality": "No annotations found",
                    "functional_confidence": "Unknown",
                    "data_completeness": "Empty"
                }

            # Analiza funciones
            functions = []
            pathways = []
            domains = []
            
            for ann in annotations:
                if ann.get("function"):
                    functions.append(ann["function"])
                if ann.get("pathway"):
                    pathways.append(ann["pathway"])
                if ann.get("domain"):
                    domains.append(ann["domain"])

            # Evalúa consistencia funcional
            unique_functions = len(set(functions))
            function_consistency = "High" if unique_functions <= 2 else "Medium" if unique_functions <= 5 else "Low"

            return {
                "total_annotations": len(annotations),
                "functional_annotations": len(functions),
                "pathway_annotations": len(pathways),
                "domain_annotations": len(domains),
                "function_consistency": function_consistency,
                "annotation_quality": "High" if len(annotations) > 5 else "Medium" if len(annotations) > 2 else "Low",
                "functional_confidence": "High" if functions and pathways else "Medium" if functions else "Low",
                "dominant_functions": list(set(functions))[:5] if functions else [],
                "associated_pathways": list(set(pathways))[:5] if pathways else []
            }

        except Exception as e:
            return {"analysis_error": str(e)}

    async def assess_applicability(self, context: Dict[str, Any]) -> float:
        """Evalúa aplicabilidad de UniProt para el contexto."""
        try:
            # UniProt es más útil si hay resultados BLAST con protein IDs
            blast_results = context.get("blast_results", {})
            has_protein_ids = bool(blast_results.get("hits", []))
            
            sequence_type = context.get("sequence_info", {}).get("type", "unknown")
            is_protein = sequence_type == "protein"
            
            # UniProt es específico para proteínas
            type_score = 1.0 if is_protein else 0.2
            
            # Mayor utilidad si hay protein IDs de BLAST
            id_score = 1.0 if has_protein_ids else 0.4
            
            # Si already tiene anotaciones UniProt, menor necesidad
            has_uniprot = "uniprot_annotations" in context
            redundancy_score = 0.3 if has_uniprot else 1.0
            
            return type_score * id_score * redundancy_score
            
        except:
            return 0.6  # Puntuación moderada

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "protein_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de IDs de proteínas"
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["function", "pathway"],
                    "description": "Campos a obtener"
                }
            },
            "required": ["protein_ids"]
        }

class SequenceFeaturesTool(AtomicTool):
    """Herramienta atómica para calcular características de secuencias."""

    def __init__(self):
        super().__init__(
            name="sequence_features",
            description="Calcula características computacionales de secuencias",
            scientific_purpose="Extrae características fisicoquímicas y estructurales de secuencias biológicas"
        )

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Calcula características de secuencia."""
        return await self._track_execution(self._execute_features, parameters)

    async def _execute_features(self, parameters: Dict[str, Any]) -> ToolResult:
        try:
            sequence = parameters.get("sequence")
            analysis_type = parameters.get("analysis_type", "basic")

            if not sequence:
                raise ValueError("Parámetro 'sequence' requerido")

            features = self._compute_features(sequence, analysis_type)

            return ToolResult(
                tool_name=self.name,
                success=True,
                result={
                    "features": features,
                    "analysis_type": analysis_type,
                    "scientific_interpretation": self._interpret_features(features, sequence)
                }
            )

        except Exception as e:
            logger.error(f"SequenceFeaturesTool falló: {e}")
            return ToolResult(
                tool_name=self.name,
                success=False,
                error_message=str(e)
            )

    def _compute_features(self, sequence: str, analysis_type: str) -> Dict[str, Any]:
        """Computa características según el tipo de análisis."""
        features = {
            "length": len(sequence),
            "composition": self._get_composition(sequence)
        }

        if analysis_type in ["detailed", "comprehensive"]:
            features.update({
                "gc_content": self._get_gc_content(sequence),
                "complexity": self._get_complexity(sequence),
                "charge_properties": self._get_charge_properties(sequence)
            })

        if analysis_type == "comprehensive":
            features.update({
                "molecular_weight": self._estimate_molecular_weight(sequence),
                "isoelectric_point": self._estimate_isoelectric_point(sequence),
                "hydrophobicity": self._get_hydrophobicity_profile(sequence),
                "secondary_structure_propensity": self._predict_secondary_structure_propensity(sequence)
            })

        return features

    def _interpret_features(self, features: Dict[str, Any], sequence: str) -> Dict[str, Any]:
        """Interpreta científicamente las características."""
        interpretation = {}
        
        # Interpreta longitud
        length = features.get("length", 0)
        if length < 50:
            interpretation["length_significance"] = "Short peptide - may be a fragment or small functional domain"
        elif length < 200:
            interpretation["length_significance"] = "Small protein - likely single domain"
        elif length < 500:
            interpretation["length_significance"] = "Medium protein - may have multiple domains"
        else:
            interpretation["length_significance"] = "Large protein - likely multi-domain with complex function"

        # Interpreta complejidad
        complexity = features.get("complexity", 0)
        if complexity < 0.1:
            interpretation["complexity_significance"] = "Very low complexity - may be repetitive or biased composition"
        elif complexity < 0.3:
            interpretation["complexity_significance"] = "Low complexity - possible structural or regulatory role"
        else:
            interpretation["complexity_significance"] = "Normal complexity - typical globular protein"

        # Interpreta carga (si disponible)
        charge_props = features.get("charge_properties", {})
        if charge_props:
            net_charge = charge_props.get("net_charge", 0)
            if abs(net_charge) > 10:
                interpretation["charge_significance"] = "Highly charged - may interact with nucleic acids or membranes"
            elif abs(net_charge) > 5:
                interpretation["charge_significance"] = "Moderately charged - typical for soluble proteins"
            else:
                interpretation["charge_significance"] = "Neutral charge - may be membrane-associated"

        return interpretation

    def _get_composition(self, sequence: str) -> Dict[str, float]:
        """Calcula composición de aminoácidos/nucleótidos."""
        total = len(sequence)
        if total == 0:
            return {}

        composition = {}
        for char in set(sequence.upper()):
            composition[char] = sequence.upper().count(char) / total

        return composition

    def _get_gc_content(self, sequence: str) -> float:
        """Calcula contenido GC para secuencias de DNA/RNA."""
        if not sequence:
            return 0.0
        gc_count = sequence.upper().count('G') + sequence.upper().count('C')
        return gc_count / len(sequence)

    def _get_complexity(self, sequence: str) -> float:
        """Calcula complejidad de secuencia."""
        if not sequence:
            return 0.0
        return len(set(sequence.upper())) / len(sequence)

    def _get_charge_properties(self, sequence: str) -> Dict[str, Any]:
        """Calcula propiedades de carga para proteínas."""
        positive_residues = "RK"
        negative_residues = "DE"
        
        positive_count = sum(sequence.upper().count(aa) for aa in positive_residues)
        negative_count = sum(sequence.upper().count(aa) for aa in negative_residues)
        
        return {
            "positive_residues": positive_count,
            "negative_residues": negative_count,
            "net_charge": positive_count - negative_count,
            "charge_density": (positive_count + negative_count) / len(sequence) if sequence else 0
        }

    def _estimate_molecular_weight(self, sequence: str) -> float:
        """Estima peso molecular (simplificado para proteínas)."""
        avg_aa_weight = 110.0  # Daltons
        return len(sequence) * avg_aa_weight

    def _estimate_isoelectric_point(self, sequence: str) -> float:
        """Estima punto isoeléctrico (simplificado)."""
        # Implementación básica - en producción usar herramientas especializadas
        positive = sum(sequence.upper().count(aa) for aa in "RK")
        negative = sum(sequence.upper().count(aa) for aa in "DE")
        
        if positive > negative:
            return 8.5  # Básico
        elif negative > positive:
            return 5.5  # Ácido
        else:
            return 7.0  # Neutro

    def _get_hydrophobicity_profile(self, sequence: str) -> Dict[str, Any]:
        """Calcula perfil de hidrofobicidad."""
        # Escala de hidrofobicidad simplificada
        hydrophobicity_scale = {
            'A': 1.8, 'R': -4.5, 'N': -3.5, 'D': -3.5, 'C': 2.5,
            'Q': -3.5, 'E': -3.5, 'G': -0.4, 'H': -3.2, 'I': 4.5,
            'L': 3.8, 'K': -3.9, 'M': 1.9, 'F': 2.8, 'P': -1.6,
            'S': -0.8, 'T': -0.7, 'W': -0.9, 'Y': -1.3, 'V': 4.2
        }

        profile = [hydrophobicity_scale.get(aa.upper(), 0.0) for aa in sequence]
        
        return {
            "profile": profile,
            "average_hydrophobicity": sum(profile) / len(profile) if profile else 0,
            "hydrophobic_residues": len([h for h in profile if h > 0]),
            "hydrophilic_residues": len([h for h in profile if h < 0])
        }

    def _predict_secondary_structure_propensity(self, sequence: str) -> Dict[str, Any]:
        """Predice propensión a estructura secundaria (muy simplificado)."""
        # Propensidades simplificadas
        helix_forming = "ALERKHQ"
        sheet_forming = "VIFYC"
        turn_forming = "GSPD"
        
        helix_score = sum(sequence.upper().count(aa) for aa in helix_forming) / len(sequence) if sequence else 0
        sheet_score = sum(sequence.upper().count(aa) for aa in sheet_forming) / len(sequence) if sequence else 0
        turn_score = sum(sequence.upper().count(aa) for aa in turn_forming) / len(sequence) if sequence else 0
        
        return {
            "helix_propensity": helix_score,
            "sheet_propensity": sheet_score,
            "turn_propensity": turn_score,
            "predicted_dominant": max([("helix", helix_score), ("sheet", sheet_score), ("turn", turn_score)], key=lambda x: x[1])[0]
        }

    async def assess_applicability(self, context: Dict[str, Any]) -> float:
        """Evalúa aplicabilidad del análisis de características."""
        try:
            sequence_info = context.get("sequence_info", {})
            sequence_length = sequence_info.get("length", 0)
            
            # Siempre útil, pero más útil para secuencias más largas
            length_score = min(1.0, sequence_length / 50.0) if sequence_length > 0 else 0.0
            
            # Si ya tiene features, menor necesidad
            has_features = "sequence_features" in context
            redundancy_score = 0.2 if has_features else 1.0
            
            return max(0.3, length_score * redundancy_score)  # Mínimo 0.3 porque siempre es útil
            
        except:
            return 0.7  # Puntuación moderada-alta

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sequence": {"type": "string", "description": "Secuencia biológica"},
                "analysis_type": {
                    "type": "string",
                    "enum": ["basic", "detailed", "comprehensive"],
                    "default": "basic",
                    "description": "Nivel de análisis"
                }
            },
            "required": ["sequence"]
        }

class LLMAnalysisTool(AtomicTool):
    """Herramienta atómica para análisis con LLM."""

    def __init__(self, llm_service, circuit_breaker_factory):
        super().__init__(
            name="llm_analysis",
            description="Análisis de datos científicos usando LLM",
            scientific_purpose="Integra y analiza datos científicos usando inteligencia artificial para generar insights"
        )
        self.llm_service = llm_service
        self.llm_cb = circuit_breaker_factory("llm_atomic")

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Ejecuta análisis con LLM."""
        return await self._track_execution(self._execute_llm, parameters)

    async def _execute_llm(self, parameters: Dict[str, Any]) -> ToolResult:
        try:
            data = parameters.get("data")
            analysis_type = parameters.get("analysis_type", "general")
            max_tokens = parameters.get("max_tokens", 1000)
            temperature = parameters.get("temperature", 0.3)

            if not data:
                raise ValueError("Parámetro 'data' requerido")

            # Construye prompt basado en tipo de análisis
            prompt = self._build_prompt(data, analysis_type)

            result = await self.llm_cb.call(
                self.llm_service.analyze_sequence_data,
                prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )

            return ToolResult(
                tool_name=self.name,
                success=True,
                result={
                    "analysis_result": result,
                    "analysis_type": analysis_type,
                    "parameters_used": {
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    },
                    "confidence_assessment": self._assess_confidence(result, data)
                }
            )

        except Exception as e:
            logger.error(f"LLMAnalysisTool falló: {e}")
            return ToolResult(
                tool_name=self.name,
                success=False,
                error_message=str(e)
            )

    def _assess_confidence(self, result, input_data) -> Dict[str, Any]:
        """Evalúa la confianza del análisis basado en la cantidad y calidad de datos."""
        confidence_factors = {}
        
        # Evalúa cantidad de datos de entrada
        data_quantity = len(str(input_data))
        if data_quantity > 2000:
            confidence_factors["data_quantity"] = "High"
        elif data_quantity > 500:
            confidence_factors["data_quantity"] = "Medium"
        else:
            confidence_factors["data_quantity"] = "Low"
        
        # Evalúa presencia de datos estructurados
        has_blast = "blast" in str(input_data).lower()
        has_uniprot = "uniprot" in str(input_data).lower()
        has_features = "features" in str(input_data).lower()
        
        data_sources = sum([has_blast, has_uniprot, has_features])
        confidence_factors["data_sources"] = f"{data_sources}/3 sources available"
        
        # Confianza general
        if data_sources >= 2 and confidence_factors["data_quantity"] in ["High", "Medium"]:
            confidence_factors["overall_confidence"] = "High"
        elif data_sources >= 1:
            confidence_factors["overall_confidence"] = "Medium"
        else:
            confidence_factors["overall_confidence"] = "Low"
            
        return confidence_factors

    def _build_prompt(self, data: Dict[str, Any], analysis_type: str) -> str:
        """Construye prompt específico para el tipo de análisis."""
        if analysis_type == "function_prediction":
            return self._build_function_prediction_prompt(data)
        elif analysis_type == "structural_analysis":
            return self._build_structural_analysis_prompt(data)
        elif analysis_type == "evolutionary_analysis":
            return self._build_evolutionary_analysis_prompt(data)
        else:
            return self._build_general_analysis_prompt(data)

    def _build_function_prediction_prompt(self, data: Dict[str, Any]) -> str:
        """Prompt específico para predicción de función."""
        return f"""
        Basándote en los siguientes datos científicos, predice la función más probable de esta proteína:

        DATOS DE ENTRADA:
        {self._format_data_for_prompt(data)}

        SOLICITUD:
        Como científico experto en bioinformática, analiza estos datos y proporciona:
        1. Función molecular más probable
        2. Confianza de la predicción (0-1)
        3. Evidencia de apoyo de los datos
        4. Funciones alternativas posibles
        5. Experimentos recomendados para validación

        Responde en formato JSON estructurado con razonamiento científico.
        """

    def _build_structural_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """Prompt específico para análisis estructural."""
        return f"""
        Analiza la estructura potencial de esta proteína basándote en:

        {self._format_data_for_prompt(data)}

        ANÁLISIS SOLICITADO:
        Como experto en biología estructural, proporciona:
        1. Dominios estructurales probables
        2. Motivos funcionales identificables
        3. Predicción de plegamiento
        4. Sitios activos potenciales
        5. Interacciones moleculares probables

        Formato JSON con justificación científica requerido.
        """

    def _build_evolutionary_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """Prompt específico para análisis evolutivo."""
        return f"""
        Realiza un análisis evolutivo basado en:

        {self._format_data_for_prompt(data)}

        ANÁLISIS EVOLUTIVO:
        Como experto en evolución molecular, determina:
        1. Familia proteica probable
        2. Origen evolutivo inferido
        3. Patrones de conservación funcional
        4. Presión selectiva aparente
        5. Relaciones filogenéticas

        Respuesta en JSON con contexto evolutivo.
        """

    def _build_general_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """Prompt general para análisis."""
        return f"""
        Analiza estos datos científicos como un bioinformático experto:

        {self._format_data_for_prompt(data)}

        Proporciona un análisis comprehensivo integrando toda la información disponible.
        Incluye predicciones funcionales, significancia biológica y confianza en las conclusiones.
        
        Formato JSON requerido con razonamiento científico detallado.
        """

    def _format_data_for_prompt(self, data: Dict[str, Any]) -> str:
        """Formatea datos para inclusión en prompt."""
        formatted_parts = []

        for key, value in data.items():
            if isinstance(value, dict):
                formatted_parts.append(f"{key.upper()}:")
                for subkey, subvalue in value.items():
                    formatted_parts.append(f"  - {subkey}: {subvalue}")
            elif isinstance(value, list):
                formatted_parts.append(f"{key.upper()}: {', '.join(map(str, value[:10]))}")  # Limita listas largas
            else:
                formatted_parts.append(f"{key.upper()}: {value}")

        return "\n".join(formatted_parts)

    async def assess_applicability(self, context: Dict[str, Any]) -> float:
        """Evalúa aplicabilidad del análisis LLM."""
        try:
            # LLM es más útil cuando hay múltiples fuentes de datos
            data_sources = 0
            if "blast_results" in context:
                data_sources += 1
            if "uniprot_annotations" in context:
                data_sources += 1
            if "sequence_features" in context:
                data_sources += 1
            
            # Más datos = más útil el LLM
            data_score = min(1.0, data_sources / 2.0)
            
            # Si ya hay análisis LLM, menor necesidad
            has_llm_analysis = "llm_analysis" in context
            redundancy_score = 0.3 if has_llm_analysis else 1.0
            
            return max(0.4, data_score * redundancy_score)  # Mínimo 0.4 porque siempre puede aportar
            
        except:
            return 0.6  # Puntuación moderada

    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {"type": "object", "description": "Datos para analizar"},
                "analysis_type": {
                    "type": "string",
                    "enum": ["general", "function_prediction", "structural_analysis", "evolutionary_analysis"],
                    "default": "general",
                    "description": "Tipo de análisis"
                },
                "max_tokens": {"type": "integer", "default": 1000, "description": "Máximo tokens"},
                "temperature": {"type": "number", "default": 0.3, "description": "Temperatura LLM"}
            },
            "required": ["data"]
        }