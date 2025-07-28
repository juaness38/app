# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - CONTENEDOR DE DEPENDENCIAS MEJORADO
LUIS: Fábrica central mejorada con health checks comprehensivos.
"""
import asyncio
import logging
import time
from typing import Optional, Dict, Any
import redis
from motor.motor_asyncio import AsyncIOMotorClient

from src.config.settings import Settings
from src.services.interfaces import (
    IOrchestrator, IContextManager, IEventStore, 
    ICapacityManager, ISQSDispatcher, IToolGateway, 
    IDriverIA, IAnalysisWorker, ICircuitBreakerFactory, 
    IMetricsService, IPipelineService
)

# Importaciones específicas de servicios
from src.services.data.context_manager import MongoContextManager
from src.services.data.event_store import MongoEventStore
from src.services.resilience.capacity_manager import RedisCapacityManager
from src.services.resilience.circuit_breaker import CircuitBreakerFactory
from src.services.execution.sqs_dispatcher import SQSDispatcher
from src.services.execution.analysis_worker import AnalysisWorker
from src.services.ai.tool_gateway import BioinformaticsToolGateway
from src.services.ai.driver_ia import OpenAIDriverIA
from src.core.orchestrator import IntelligentOrchestrator
from src.services.observability.metrics_service import PrometheusMetricsService
from datetime import datetime

class AppContainer:
    """LUIS: Contenedor principal mejorado con health checks comprehensivos."""
    
    def __init__(self, settings: Settings):
        """LUIS: Inicializa el contenedor de dependencias."""
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Inicializando AppContainer para {settings.PROJECT_NAME}")
        
        # Inicializa clientes base
        self._init_clients()
        
        # Inicializa métricas
        self._init_metrics()
        
        # Inicializa servicios de datos
        self._init_data_services()
        
        # Inicializa servicios de resiliencia
        self._init_resilience_services()
        
        # Inicializa servicios de ejecución
        self._init_execution_services()
        
        # Inicializa servicios de IA
        self._init_ai_services()
        
        # Inicializa el orquestador principal
        self._init_orchestrator()
        
        # Inicializa servicios específicos del pipeline
        self._init_pipeline_services()
        
        # Inicializa el pipeline científico principal
        self._init_scientific_pipeline()
        
        # Inicializa el analysis worker
        self._init_analysis_worker()
        
        self.logger.info("AppContainer 'Antares' inicializado exitosamente")

    def _init_clients(self):
        """LUIS: Inicializa clientes de base mejorados (Redis, MongoDB)."""
        # Cliente Redis (redis-py sincrónico con wrapper async)
        self.redis_client = redis.from_url(self.settings.REDIS_URL, decode_responses=True)
        
        # Cliente MongoDB
        self.mongo_client = AsyncIOMotorClient(
            self.settings.MONGO_URL,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            heartbeatFrequencyMS=10000
        )
        
        self.logger.info("Clientes base inicializados")

    def _init_metrics(self):
        """LUIS: Inicializa sistema de métricas."""
        self.metrics: IMetricsService = PrometheusMetricsService()
        self.logger.info("Sistema de métricas inicializado")

    def _init_data_services(self):
        """LUIS: Inicializa servicios de persistencia mejorados."""
        self.context_manager: IContextManager = MongoContextManager(
            self.mongo_client
        )
        
        self.event_store: IEventStore = MongoEventStore(
            self.mongo_client
        )
        
        self.logger.info("Servicios de datos inicializados")

    def _init_resilience_services(self):
        """LUIS: Inicializa servicios de resiliencia mejorados."""
        # Fábrica de Circuit Breakers
        self.circuit_breaker_factory: ICircuitBreakerFactory = CircuitBreakerFactory(
            self.redis_client,
            failure_threshold=self.settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            open_seconds=self.settings.CIRCUIT_BREAKER_OPEN_SECONDS
        )
        
        # Inyectar métricas a la factory
        self.circuit_breaker_factory.set_metrics(self.metrics)
        
        # Gestión de capacidad
        self.capacity_manager: ICapacityManager = RedisCapacityManager(
            self.redis_client,
            self.metrics
        )
        
        self.logger.info("Servicios de resiliencia inicializados")

    def _init_execution_services(self):
        """LUIS: Inicializa servicios de ejecución mejorados."""
        self.sqs_dispatcher: ISQSDispatcher = SQSDispatcher(self.metrics)
        
        self.logger.info("Servicios de ejecución inicializados")

    def _init_ai_services(self):
        """LUIS: Inicializa servicios de IA mejorados con capacidades agénticas."""
        # Tool Gateway Agéntico - NUEVA CAPACIDAD FASE 1
        from src.services.agentic.agentic_gateway import AgenticToolGateway
        
        self.tool_gateway: IToolGateway = AgenticToolGateway(
            self.blast_service,
            self.uniprot_service,
            self.driver_ia,  # Se inicializa después, pero se pasa la referencia
            self.circuit_breaker_factory
        )
        
        # Driver IA
        self.driver_ia: IDriverIA = OpenAIDriverIA(
            self.tool_gateway,
            self.context_manager,
            self.event_store,
            api_key=self.settings.OPENAI_API_KEY
        )
        
        # Actualiza la referencia del LLM service en el tool gateway
        if hasattr(self.tool_gateway, 'atomic_tools') and 'llm_analysis' in self.tool_gateway.atomic_tools:
            self.tool_gateway.atomic_tools['llm_analysis'].llm_service = self.driver_ia
        
        self.logger.info("Servicios de IA con capacidades agénticas inicializados")

    def _init_orchestrator(self):
        """LUIS: Inicializa el orquestador principal mejorado."""
        self.orchestrator: IOrchestrator = IntelligentOrchestrator(
            self.context_manager,
            self.capacity_manager,
            self.sqs_dispatcher,
            self.event_store,
            self.metrics
        )
        
        self.logger.info("Orquestador inicializado")

    def _init_pipeline_services(self):
        """LUIS: Inicializa servicios específicos del pipeline."""
        from src.services.bioinformatics.blast_service import LocalBlastService
        from src.services.bioinformatics.uniprot_service import UniProtService
        
        # Servicios bioinformáticos
        self.blast_service = LocalBlastService(self.circuit_breaker_factory)
        self.uniprot_service = UniProtService(self.circuit_breaker_factory)
        
        self.logger.info("Servicios del pipeline inicializados")

    def _init_scientific_pipeline(self):
        """LUIS: Inicializa el pipeline científico principal con capacidades agénticas mejoradas."""
        from src.core.pipeline import EnhancedScientificPipeline
        from src.models.analysis import EnhancedPipelineConfig
        
        # Configuración mejorada del pipeline con valores por defecto agénticos
        enhanced_config = EnhancedPipelineConfig(
            blast_database="nr",
            evalue_threshold=1e-10,
            max_target_seqs=100,
            uniprot_fields=["function", "pathway", "domain", "subcellular_location"],
            llm_analysis_depth="detailed",
            llm_max_tokens=1500,
            llm_temperature=0.3,
            max_concurrent_sequences=5,
            enable_caching=True,
            blast_cache_ttl=3600,
            uniprot_cache_ttl=7200,
            features_cache_ttl=86400,
            uniprot_batch_size=10
        )
        
        self.pipeline_service: IPipelineService = EnhancedScientificPipeline(
            self.blast_service,
            self.uniprot_service,
            self.driver_ia,  # También funciona como ILLMService
            self.circuit_breaker_factory,
            config=enhanced_config
        )
        
        self.logger.info("Pipeline científico agéntico mejorado inicializado")

    def _init_analysis_worker(self):
        """LUIS: Inicializa el worker de análisis mejorado."""
        self.analysis_worker: IAnalysisWorker = AnalysisWorker(
            self.driver_ia,
            self.context_manager,
            self.capacity_manager,
            self.event_store
        )
        
        self.logger.info("Analysis Worker inicializado")

    async def initialize_resources(self):
        """LUIS: Inicialización asíncrona de recursos mejorada."""
        try:
            # Asegurar índices de MongoDB
            await self._ensure_mongodb_indexes()
            
            # Inicializar métricas
            await self.metrics.initialize()
            
            self.logger.info("Recursos inicializados correctamente")
            
        except Exception as e:
            self.logger.error(f"Error inicializando recursos: {e}")
            raise

    async def _ensure_mongodb_indexes(self):
        """LUIS: Asegura índices de MongoDB para performance."""
        try:
            db = self.mongo_client[self.settings.DB_NAME]
            
            # Índices para analysis contexts
            await db.analysis_contexts.create_index([("user_id", 1), ("created_at", -1)])
            await db.analysis_contexts.create_index([("status", 1), ("created_at", -1)])
            await db.analysis_contexts.create_index([("workspace_id", 1), ("protocol_type", 1)])
            await db.analysis_contexts.create_index([("context_id", 1)], unique=True)
            
            # Índices para eventos
            await db.analysis_events.create_index([("context_id", 1), ("timestamp", -1)])
            await db.analysis_events.create_index([("event_type", 1), ("timestamp", -1)])
            
            self.logger.info("Índices de MongoDB asegurados")
            
        except Exception as e:
            self.logger.warning(f"Error creando índices MongoDB: {e}")

    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """LUIS: Health check comprehensivo que prueba TODAS las dependencias."""
        health = {
            "timestamp": datetime.utcnow(),
            "overall_status": "healthy",
            "services": {}
        }
        
        # Test Redis
        try:
            start = time.time()
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.redis_client.ping)
            latency = (time.time() - start) * 1000
            health["services"]["redis"] = {
                "status": "healthy", 
                "latency_ms": round(latency, 2),
                "url": self.settings.REDIS_URL
            }
        except Exception as e:
            health["services"]["redis"] = {
                "status": "unhealthy", 
                "error": str(e),
                "url": self.settings.REDIS_URL
            }
            health["overall_status"] = "degraded"
        
        # Test MongoDB
        try:
            start = time.time()
            await self.mongo_client.admin.command("ping")
            latency = (time.time() - start) * 1000
            health["services"]["mongodb"] = {
                "status": "healthy", 
                "latency_ms": round(latency, 2),
                "database": self.settings.DB_NAME
            }
        except Exception as e:
            health["services"]["mongodb"] = {
                "status": "unhealthy", 
                "error": str(e),
                "database": self.settings.DB_NAME
            }
            health["overall_status"] = "degraded"
        
        # Test DriverIA
        try:
            driver_health = await self.driver_ia.health_check()
            health["services"]["driver_ia"] = {
                "status": "healthy" if driver_health else "unhealthy",
                "has_real_api_key": self.settings.has_real_ai_keys()
            }
        except Exception as e:
            health["services"]["driver_ia"] = {
                "status": "unhealthy", 
                "error": str(e)
            }
            health["overall_status"] = "degraded"
        
        # Test Tool Gateway
        try:
            available_tools = await self.tool_gateway.list_available_tools()
            health["services"]["tool_gateway"] = {
                "status": "healthy",
                "available_tools": len(available_tools),
                "tools": available_tools
            }
        except Exception as e:
            health["services"]["tool_gateway"] = {
                "status": "unhealthy", 
                "error": str(e)
            }
            health["overall_status"] = "degraded"
        
        # Test Capacity Manager
        try:
            capacity_info = await self.capacity_manager.get_capacity_info()
            health["services"]["capacity_manager"] = {
                "status": "healthy",
                "current_jobs": capacity_info.get("current_jobs", 0),
                "max_capacity": capacity_info.get("max_capacity", 0),
                "utilization_percent": capacity_info.get("utilization_percent", 0)
            }
        except Exception as e:
            health["services"]["capacity_manager"] = {
                "status": "unhealthy", 
                "error": str(e)
            }
            health["overall_status"] = "degraded"
        
        return health

    async def health_check(self) -> dict:
        """LUIS: Verifica la salud básica de todos los servicios."""
        try:
            health_status = {
                "container": "healthy",
                "services": {}
            }
            
            # Verifica servicios críticos
            try:
                # Redis
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.redis_client.ping)
                health_status["services"]["redis"] = "healthy"
            except Exception as e:
                health_status["services"]["redis"] = f"unhealthy: {str(e)}"
            
            # MongoDB
            try:
                await self.mongo_client.admin.command("ping")
                health_status["services"]["mongodb"] = "healthy"
            except Exception as e:
                health_status["services"]["mongodb"] = f"unhealthy: {str(e)}"
            
            # Orquestador
            try:
                orchestrator_health = await self.orchestrator.health_check()
                health_status["services"]["orchestrator"] = orchestrator_health
            except Exception as e:
                health_status["services"]["orchestrator"] = f"unhealthy: {str(e)}"
            
            # Analysis Worker
            try:
                worker_healthy = await self.analysis_worker.health_check()
                health_status["services"]["analysis_worker"] = "healthy" if worker_healthy else "unhealthy"
            except Exception as e:
                health_status["services"]["analysis_worker"] = f"unhealthy: {str(e)}"
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error en health check: {e}")
            return {
                "container": "unhealthy",
                "error": str(e)
            }

    async def get_metrics(self) -> dict:
        """LUIS: Obtiene métricas completas del sistema."""
        try:
            metrics = {
                "system": await self.metrics.get_all_metrics(),
                "capacity": {}
            }
            
            # Métricas de capacidad
            try:
                worker_stats = await self.analysis_worker.get_worker_stats()
                metrics["capacity"] = worker_stats
            except Exception as e:
                metrics["capacity"] = {"error": str(e)}
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error obteniendo métricas: {e}")
            return {"error": str(e)}

    async def shutdown(self):
        """LUIS: Cierra recursos de forma limpia y mejorada."""
        self.logger.info("Iniciando cierre limpio de recursos...")
        
        try:
            # Cierra workers
            if hasattr(self, 'analysis_worker'):
                await self.analysis_worker.shutdown()
            
            # Cierra orquestador
            if hasattr(self, 'orchestrator'):
                await self.orchestrator.shutdown()
            
            # Cierra clientes
            if hasattr(self, 'redis_client'):
                await self.redis_client.close()
            
            if hasattr(self, 'mongo_client'):
                self.mongo_client.close()
            
            # Cierra métricas
            if hasattr(self, 'metrics'):
                await self.metrics.shutdown()
            
            self.logger.info("Recursos cerrados exitosamente")
            
        except Exception as e:
            self.logger.error(f"Error cerrando recursos: {e}")