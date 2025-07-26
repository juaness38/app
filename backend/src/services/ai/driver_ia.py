# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - DRIVER IA REFINADO
Driver IA con soporte específico para pipeline científico y LLM.
"""
import logging
import asyncio
import time
from typing import Dict, Any, List
import httpx
import json
from src.services.interfaces import IDriverIA, IToolGateway, IContextManager, IEventStore, ILLMService
from src.models.analysis import (
    AnalysisRequest, AnalysisContext, PromptProtocol, PromptNode, 
    PromptProtocolType, ToolResult, EventStoreEntry
)
from src.config.settings import settings
from src.core.exceptions import DriverIAException

class OpenAIDriverIA(IDriverIA, ILLMService):
    """
    Driver IA refinado que también implementa servicios LLM.
    """
    
    def __init__(
        self, 
        tool_gateway: IToolGateway,
        context_manager: IContextManager,
        event_store: IEventStore
    ):
        self.tool_gateway = tool_gateway
        self.context_manager = context_manager
        self.event_store = event_store
        self.logger = logging.getLogger(__name__)
        
        # Configuración del cliente OpenAI
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"
        self.model = "gpt-4o"
        
        # Cliente HTTP para llamadas a OpenAI
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        
        self.logger.info("Driver IA (OpenAI) refinado inicializado")

    # ========================================================================
    # IMPLEMENTACIÓN DE ILLMService
    # ========================================================================

    async def analyze_sequence_data(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.3) -> Dict[str, Any]:
        """Analiza datos de secuencia usando LLM."""
        if self.api_key == "sk-placeholder-openai-key":
            # Modo simulado
            return await self._simulate_llm_analysis(prompt)
        
        try:
            response = await self.http_client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system", 
                            "content": "Eres un bioinformático experto. Analiza datos de secuencias y proporciona insights científicos en formato JSON."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                try:
                    # Intenta parsear como JSON
                    return json.loads(content)
                except json.JSONDecodeError:
                    # Si no es JSON válido, estructura la respuesta
                    return {
                        "analysis": content,
                        "function": "Unknown",
                        "confidence": 0.7,
                        "findings": [content[:100] + "..."],
                        "recommendations": ["Revisar análisis manual"]
                    }
            else:
                raise Exception(f"OpenAI API error: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error en análisis LLM: {e}")
            return await self._simulate_llm_analysis(prompt)

    async def generate_summary(self, data: Dict[str, Any]) -> str:
        """Genera un resumen de los datos."""
        prompt = f"""
        Genera un resumen científico conciso de los siguientes datos de análisis:
        
        {json.dumps(data, indent=2)}
        
        El resumen debe incluir:
        1. Tipo de secuencia y características principales
        2. Resultados más relevantes
        3. Función predicha (si aplica)
        4. Nivel de confianza
        
        Mantén el resumen en 2-3 párrafos máximo.
        """
        
        result = await self.analyze_sequence_data(prompt, max_tokens=500)
        return result.get("analysis", "No se pudo generar resumen")

    async def health_check(self) -> bool:
        """Verifica el estado del servicio LLM."""
        try:
            if self.api_key == "sk-placeholder-openai-key":
                return True  # Modo simulado siempre healthy
                
            # Test simple con OpenAI
            response = await self.http_client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Test"}],
                    "max_tokens": 10
                }
            )
            return response.status_code == 200
            
        except Exception:
            return False

    async def _simulate_llm_analysis(self, prompt: str) -> Dict[str, Any]:
        """Simula análisis LLM para desarrollo."""
        await asyncio.sleep(1)  # Simula tiempo de procesamiento
        
        # Extrae información del prompt para generar respuesta realista
        sequence_mentioned = "secuencia" in prompt.lower() or "sequence" in prompt.lower()
        blast_mentioned = "blast" in prompt.lower()
        uniprot_mentioned = "uniprot" in prompt.lower()
        
        return {
            "function": "Proteína hipotética con actividad enzimática" if sequence_mentioned else "Función desconocida",
            "confidence": 0.78 if blast_mentioned and uniprot_mentioned else 0.45,
            "findings": [
                "Homología significativa encontrada" if blast_mentioned else "Análisis limitado disponible",
                "Dominios funcionales identificados" if uniprot_mentioned else "Dominios no caracterizados",
                "Estructura secundaria predicha",
                "Conservación evolutiva moderada"
            ],
            "recommendations": [
                "Validación experimental recomendada",
                "Análisis de expresión adicional",
                "Estudios de función in vitro"
            ],
            "analysis": f"[SIMULADO] Análisis completo basado en: {prompt[:100]}...",
            "metabolic_pathways": ["Metabolismo de aminoácidos", "Biosíntesis de proteínas"],
            "organism_specificity": "Conservada en procariotas",
            "structural_features": {
                "domains": 2,
                "transmembrane_regions": 0,
                "signal_peptide": False
            }
        }

    # ========================================================================
    # IMPLEMENTACIÓN MEJORADA DE IDriverIA
    # ========================================================================

    async def execute_protocol(self, protocol: PromptProtocol, context: AnalysisContext) -> None:
        """Ejecuta un Prompt Protocol con logging mejorado."""
        self.logger.info(f"Ejecutando protocolo: {protocol.name} para contexto: {context.context_id}")
        
        try:
            await self.event_store.store_event(EventStoreEntry(
                context_id=context.context_id,
                event_type="protocol_started",
                data={
                    "protocol_name": protocol.name,
                    "protocol_type": protocol.protocol_type,
                    "nodes_count": len(protocol.nodes),
                    "estimated_duration": len(protocol.nodes) * 30  # 30s por nodo estimado
                },
                agent="driver_ia"
            ))
            
            await self.context_manager.update_progress(context.context_id, 0, "Iniciando protocolo")
            
            # Ejecuta nodos con mejor manejo de errores
            results = {}
            for i, node in enumerate(protocol.nodes):
                progress = int((i / len(protocol.nodes)) * 100)
                await self.context_manager.update_progress(
                    context.context_id, 
                    progress, 
                    f"Ejecutando: {node.name}"
                )
                
                node_result = await self._execute_node_with_retry(node, context, results)
                results[node.node_id] = node_result
                
                # Pausa adaptativa entre nodos
                await asyncio.sleep(0.5 if node_result.get("success") else 1.0)
            
            # Análisis final con LLM
            final_analysis = await self.analyze_results(context.context_id, results)
            results["final_analysis"] = final_analysis
            
            await self.context_manager.set_results(context.context_id, results)
            await self.context_manager.update_progress(context.context_id, 100, "Protocolo completado")
            await self.context_manager.mark_completed(context.context_id)
            
            await self.event_store.store_event(EventStoreEntry(
                context_id=context.context_id,
                event_type="protocol_completed",
                data={"protocol_name": protocol.name, "results_count": len(results)},
                agent="driver_ia"
            ))
            
        except Exception as e:
            self.logger.error(f"Error ejecutando protocolo: {e}")
            await self.context_manager.mark_failed(context.context_id, str(e))
            
            await self.event_store.store_event(EventStoreEntry(
                context_id=context.context_id,
                event_type="protocol_failed",
                data={"protocol_name": protocol.name, "error": str(e)},
                agent="driver_ia"
            ))
            
            raise DriverIAException(f"Fallo en ejecución del protocolo: {e}")

    async def _execute_node_with_retry(self, node: PromptNode, context: AnalysisContext, previous_results: Dict) -> Dict[str, Any]:
        """Ejecuta un nodo con lógica de reintento."""
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                return await self._execute_single_node(node, context, previous_results)
                
            except Exception as e:
                if attempt == max_retries:
                    self.logger.error(f"Node {node.name} failed after {max_retries} retries: {e}")
                    return {
                        "success": False,
                        "error": str(e),
                        "attempts": attempt + 1,
                        "node_name": node.name
                    }
                
                self.logger.warning(f"Node {node.name} attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(1.0 * (attempt + 1))  # Backoff exponencial

    async def _execute_single_node(self, node: PromptNode, context: AnalysisContext, previous_results: Dict) -> Dict[str, Any]:
        """Ejecuta un nodo individual con contexto mejorado."""
        start_time = time.time()
        
        try:
            # Prepara parámetros con contexto de resultados previos
            enhanced_parameters = node.parameters.copy()
            
            # Sustituye referencias a resultados previos
            for key, value in enhanced_parameters.items():
                if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                    ref_key = value[1:-1]  # Remove {}
                    if ref_key in previous_results:
                        enhanced_parameters[key] = previous_results[ref_key]
            
            # Invoca herramienta si es necesario
            if node.tool_name:
                tool_result = await self.tool_gateway.invoke_tool(node.tool_name, enhanced_parameters)
                
                # Almacena resultado detallado
                result_data = {
                    "node_name": node.name,
                    "tool_name": node.tool_name,
                    "success": tool_result.success,
                    "execution_time": tool_result.execution_time,
                    "result": tool_result.result,
                    "parameters_used": enhanced_parameters
                }
                
                if not tool_result.success:
                    result_data["error"] = tool_result.error_message
                
            else:
                # Nodo de procesamiento sin herramienta
                result_data = {
                    "node_name": node.name,
                    "success": True,
                    "execution_time": time.time() - start_time,
                    "result": {"message": f"Node {node.name} processed successfully"},
                    "parameters_used": enhanced_parameters
                }
            
            # Almacena evento del nodo
            await self.event_store.store_event(EventStoreEntry(
                context_id=context.context_id,
                event_type="node_completed" if result_data["success"] else "node_failed",
                data=result_data,
                agent="driver_ia"
            ))
            
            return result_data
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            await self.event_store.store_event(EventStoreEntry(
                context_id=context.context_id,
                event_type="node_error",
                data={
                    "node_name": node.name,
                    "error": str(e),
                    "execution_time": execution_time
                },
                agent="driver_ia"
            ))
            
            raise

    async def analyze_results(self, context_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Análisis final mejorado con LLM."""
        self.logger.info(f"Analizando resultados finales para contexto: {context_id}")
        
        try:
            # Prepara datos para análisis LLM
            analysis_data = {
                "context_id": context_id,
                "total_nodes": len([k for k in results.keys() if k != "final_analysis"]),
                "successful_nodes": len([r for r in results.values() if isinstance(r, dict) and r.get("success", False)]),
                "key_results": {}
            }
            
            # Extrae resultados clave
            for node_id, result in results.items():
                if isinstance(result, dict) and result.get("success") and result.get("result"):
                    analysis_data["key_results"][node_id] = result["result"]
            
            # Genera prompt para análisis integral
            prompt = f"""
            Analiza los siguientes resultados de un pipeline científico:
            
            Contexto: {context_id}
            Nodos ejecutados: {analysis_data['total_nodes']}
            Nodos exitosos: {analysis_data['successful_nodes']}
            
            Resultados clave:
            {json.dumps(analysis_data['key_results'], indent=2)}
            
            Proporciona un análisis integral que incluya:
            1. Resumen ejecutivo de los hallazgos
            2. Consistencia entre resultados
            3. Nivel de confianza general
            4. Recomendaciones científicas
            5. Próximos pasos sugeridos
            
            Responde en formato JSON estructurado.
            """
            
            llm_analysis = await self.analyze_sequence_data(prompt, max_tokens=1500)
            
            return {
                "pipeline_summary": analysis_data,
                "llm_insights": llm_analysis,
                "overall_confidence": llm_analysis.get("confidence", 0.5),
                "key_findings": llm_analysis.get("findings", []),
                "recommendations": llm_analysis.get("recommendations", []),
                "analysis_timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Error en análisis final: {e}")
            return {
                "pipeline_summary": {"error": str(e)},
                "overall_confidence": 0.0,
                "key_findings": ["Error en análisis final"],
                "recommendations": ["Revisar logs para detalles del error"]
            }

    async def close(self):
        """Cierra el cliente HTTP."""
        if self.http_client:
            await self.http_client.aclose()