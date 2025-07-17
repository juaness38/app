# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - DRIVER IA
LUIS: El cerebro cognitivo del sistema. Orquesta la investigación científica.
"""
import logging
import asyncio
import time
from typing import Dict, Any, List
import httpx
from src.services.interfaces import IDriverIA, IToolGateway, IContextManager, IEventStore
from src.models.analysis import (
    AnalysisRequest, AnalysisContext, PromptProtocol, PromptNode, 
    PromptProtocolType, ToolResult, EventStoreEntry
)
from src.config.settings import settings
from src.core.exceptions import DriverIAException

class OpenAIDriverIA(IDriverIA):
    """
    LUIS: Driver IA implementado con OpenAI.
    El cerebro que interpreta Prompt Protocols y orquesta herramientas.
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
        self.model = "gpt-4o"  # Modelo más avanzado disponible
        
        # Cliente HTTP para llamadas a OpenAI
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        
        self.logger.info("Driver IA (OpenAI) inicializado")

    async def execute_protocol(self, protocol: PromptProtocol, context: AnalysisContext) -> None:
        """
        LUIS: Ejecuta un Prompt Protocol completo.
        Es el bucle principal del científico cognitivo.
        """
        self.logger.info(f"Iniciando ejecución del protocolo: {protocol.name}")
        
        try:
            # Almacena evento de inicio
            await self.event_store.store_event(EventStoreEntry(
                context_id=context.context_id,
                event_type="protocol_started",
                data={"protocol_name": protocol.name, "protocol_type": protocol.protocol_type},
                agent="driver_ia"
            ))
            
            # Actualiza contexto
            await self.context_manager.update_progress(context.context_id, 0, "Iniciando protocolo")
            
            # Ejecuta nodos secuencialmente
            for i, node in enumerate(protocol.nodes):
                progress = int((i / len(protocol.nodes)) * 100)
                await self.context_manager.update_progress(
                    context.context_id, 
                    progress, 
                    f"Ejecutando: {node.name}"
                )
                
                # Ejecuta el nodo
                await self._execute_node(node, context)
                
                # Pausa entre nodos para evitar sobrecarga
                await asyncio.sleep(0.5)
            
            # Protocolo completado
            await self.context_manager.update_progress(context.context_id, 100, "Protocolo completado")
            await self.context_manager.mark_completed(context.context_id)
            
            # Almacena evento de finalización
            await self.event_store.store_event(EventStoreEntry(
                context_id=context.context_id,
                event_type="protocol_completed",
                data={"protocol_name": protocol.name},
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

    async def _execute_node(self, node: PromptNode, context: AnalysisContext) -> None:
        """LUIS: Ejecuta un nodo individual del protocolo."""
        self.logger.info(f"Ejecutando nodo: {node.name}")
        
        try:
            # Almacena evento de inicio del nodo
            await self.event_store.store_event(EventStoreEntry(
                context_id=context.context_id,
                event_type="node_started",
                data={"node_name": node.name, "node_id": node.node_id},
                agent="driver_ia"
            ))
            
            # Si el nodo requiere una herramienta
            if node.tool_name:
                result = await self.tool_gateway.invoke_tool(node.tool_name, node.parameters)
                
                # Almacena el resultado
                await self.event_store.store_event(EventStoreEntry(
                    context_id=context.context_id,
                    event_type="tool_result",
                    data={
                        "node_name": node.name,
                        "tool_name": node.tool_name,
                        "success": result.success,
                        "result": result.result,
                        "execution_time": result.execution_time
                    },
                    agent="driver_ia"
                ))
                
                # Analiza el resultado con IA
                analysis = await self._analyze_tool_result(result, context)
                
                # Actualiza contexto con análisis
                current_context = await self.context_manager.get_context(context.context_id)
                if current_context:
                    results = current_context.results.copy()
                    results[node.node_id] = {
                        "tool_result": result.model_dump(),
                        "ai_analysis": analysis
                    }
                    await self.context_manager.set_results(context.context_id, results)
            
            # Almacena evento de finalización del nodo
            await self.event_store.store_event(EventStoreEntry(
                context_id=context.context_id,
                event_type="node_completed",
                data={"node_name": node.name, "node_id": node.node_id},
                agent="driver_ia"
            ))
            
        except Exception as e:
            self.logger.error(f"Error ejecutando nodo {node.name}: {e}")
            
            await self.event_store.store_event(EventStoreEntry(
                context_id=context.context_id,
                event_type="node_failed",
                data={"node_name": node.name, "node_id": node.node_id, "error": str(e)},
                agent="driver_ia"
            ))
            
            raise

    async def _analyze_tool_result(self, result: ToolResult, context: AnalysisContext) -> Dict[str, Any]:
        """LUIS: Analiza el resultado de una herramienta usando IA."""
        if not result.success:
            return {"analysis": "Tool execution failed", "confidence": 0.0}
        
        # Placeholder para análisis con IA
        # Aquí iría la llamada real a OpenAI
        if self.api_key == "sk-placeholder-openai-key":
            return {
                "analysis": f"[SIMULADO] Análisis de resultado de {result.tool_name}",
                "confidence": 0.85,
                "key_findings": ["Resultado procesado exitosamente"],
                "next_steps": ["Continuar con siguiente nodo"]
            }
        
        # Llamada real a OpenAI (cuando se tenga la clave)
        try:
            prompt = f"""
            Analiza el siguiente resultado de la herramienta {result.tool_name}:
            
            Resultado: {result.result}
            
            Contexto del análisis: {context.protocol_type}
            
            Proporciona:
            1. Análisis del resultado
            2. Nivel de confianza (0-1)
            3. Hallazgos clave
            4. Próximos pasos recomendados
            
            Responde en formato JSON.
            """
            
            response = await self.http_client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 1000
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json()
                content = ai_response['choices'][0]['message']['content']
                
                # Intenta parsear como JSON
                try:
                    import json
                    return json.loads(content)
                except:
                    return {"analysis": content, "confidence": 0.7}
            
        except Exception as e:
            self.logger.error(f"Error en análisis IA: {e}")
        
        return {"analysis": "Error en análisis IA", "confidence": 0.0}

    async def generate_protocol(self, request: AnalysisRequest) -> PromptProtocol:
        """
        LUIS: Genera un Prompt Protocol basado en el tipo de análisis solicitado.
        """
        self.logger.info(f"Generando protocolo para: {request.protocol_type}")
        
        # Protocolos predefinidos por tipo
        if request.protocol_type == PromptProtocolType.PROTEIN_FUNCTION_ANALYSIS:
            return self._generate_protein_function_protocol(request)
        elif request.protocol_type == PromptProtocolType.SEQUENCE_ALIGNMENT:
            return self._generate_sequence_alignment_protocol(request)
        elif request.protocol_type == PromptProtocolType.STRUCTURE_PREDICTION:
            return self._generate_structure_prediction_protocol(request)
        elif request.protocol_type == PromptProtocolType.DRUG_DESIGN:
            return self._generate_drug_design_protocol(request)
        elif request.protocol_type == PromptProtocolType.BIOREACTOR_OPTIMIZATION:
            return self._generate_bioreactor_optimization_protocol(request)
        else:
            raise DriverIAException(f"Protocolo no soportado: {request.protocol_type}")

    def _generate_protein_function_protocol(self, request: AnalysisRequest) -> PromptProtocol:
        """LUIS: Genera protocolo para análisis de función de proteína."""
        nodes = [
            PromptNode(
                name="Búsqueda de Homología",
                description="Buscar secuencias similares usando BLAST",
                tool_name="blast",
                parameters={"sequence": request.sequence, "database": "nr"}
            ),
            PromptNode(
                name="Análisis de Dominios",
                description="Identificar dominios funcionales",
                tool_name="interpro",
                parameters={"sequence": request.sequence}
            ),
            PromptNode(
                name="Predicción de Estructura",
                description="Predecir estructura 3D",
                tool_name="alphafold",
                parameters={"sequence": request.sequence}
            ),
            PromptNode(
                name="Análisis Funcional",
                description="Integrar resultados para determinar función",
                tool_name="function_predictor",
                parameters={"blast_results": "{blast.result}", "domains": "{interpro.result}"}
            )
        ]
        
        return PromptProtocol(
            name="Análisis de Función de Proteína",
            description="Protocolo para determinar la función de una proteína desconocida",
            protocol_type=request.protocol_type,
            nodes=nodes
        )

    def _generate_sequence_alignment_protocol(self, request: AnalysisRequest) -> PromptProtocol:
        """LUIS: Genera protocolo para alineamiento de secuencias."""
        nodes = [
            PromptNode(
                name="Alineamiento MAFFT",
                description="Alineamiento múltiple usando MAFFT",
                tool_name="mafft",
                parameters={"sequences": request.parameters.get("sequences", [])}
            ),
            PromptNode(
                name="Análisis de Conservación",
                description="Analizar regiones conservadas",
                tool_name="conservation_analyzer",
                parameters={"alignment": "{mafft.result}"}
            )
        ]
        
        return PromptProtocol(
            name="Alineamiento de Secuencias",
            description="Protocolo para alineamiento múltiple y análisis de conservación",
            protocol_type=request.protocol_type,
            nodes=nodes
        )

    def _generate_structure_prediction_protocol(self, request: AnalysisRequest) -> PromptProtocol:
        """LUIS: Genera protocolo para predicción de estructura."""
        nodes = [
            PromptNode(
                name="Predicción AlphaFold",
                description="Predicción de estructura con AlphaFold",
                tool_name="alphafold",
                parameters={"sequence": request.sequence}
            ),
            PromptNode(
                name="Validación Estructural",
                description="Validar estructura predicha",
                tool_name="structure_validator",
                parameters={"structure": "{alphafold.result}"}
            )
        ]
        
        return PromptProtocol(
            name="Predicción de Estructura",
            description="Protocolo para predicción y validación de estructura proteica",
            protocol_type=request.protocol_type,
            nodes=nodes
        )

    def _generate_drug_design_protocol(self, request: AnalysisRequest) -> PromptProtocol:
        """LUIS: Genera protocolo para diseño de fármacos."""
        nodes = [
            PromptNode(
                name="Análisis de Diana",
                description="Analizar proteína diana",
                tool_name="target_analyzer",
                parameters={"target": request.target_protein}
            ),
            PromptNode(
                name="Docking Molecular",
                description="Realizar docking molecular",
                tool_name="swiss_dock",
                parameters={"target": request.target_protein, "ligands": request.parameters.get("ligands", [])}
            )
        ]
        
        return PromptProtocol(
            name="Diseño de Fármacos",
            description="Protocolo para diseño y evaluación de candidatos a fármacos",
            protocol_type=request.protocol_type,
            nodes=nodes
        )

    def _generate_bioreactor_optimization_protocol(self, request: AnalysisRequest) -> PromptProtocol:
        """LUIS: Genera protocolo para optimización de bioreactor."""
        nodes = [
            PromptNode(
                name="Análisis de Parámetros",
                description="Analizar parámetros actuales del bioreactor",
                tool_name="bioreactor_analyzer",
                parameters=request.parameters
            ),
            PromptNode(
                name="Optimización",
                description="Optimizar condiciones de cultivo",
                tool_name="optimization_engine",
                parameters={"current_params": "{bioreactor_analyzer.result}"}
            )
        ]
        
        return PromptProtocol(
            name="Optimización de Bioreactor",
            description="Protocolo para optimización de condiciones de cultivo",
            protocol_type=request.protocol_type,
            nodes=nodes
        )

    async def analyze_results(self, context_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """LUIS: Analiza los resultados finales del protocolo."""
        self.logger.info(f"Analizando resultados finales para contexto: {context_id}")
        
        # Placeholder para análisis con IA
        if self.api_key == "sk-placeholder-openai-key":
            return {
                "summary": "[SIMULADO] Análisis completo de resultados",
                "confidence": 0.90,
                "key_findings": ["Análisis completado exitosamente"],
                "recommendations": ["Revisar resultados detallados"]
            }
        
        # Análisis real con IA (cuando se tenga la clave)
        # Aquí iría la lógica de análisis integral
        
        return {
            "summary": "Análisis de resultados completado",
            "confidence": 0.85,
            "results_count": len(results),
            "timestamp": time.time()
        }

    async def close(self):
        """LUIS: Cierra el cliente HTTP."""
        if self.http_client:
            await self.http_client.aclose()