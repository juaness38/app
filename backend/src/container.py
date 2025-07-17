# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - CONTENEDOR DE DEPENDENCIAS
LUIS: El corazón del sistema. Instancia y conecta todos los servicios.
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as aioredis
from src.config.settings import settings
from src.services.interfaces import *
from src.services.observability.metrics_service import PrometheusMetricsService
from src.services.resilience.capacity_manager import RedisCapacityManager
from src.services.resilience.circuit_breaker import RedisCircuitBreaker
from src.services.execution.sqs_dispatcher import SQSDispatcher
from src.services.ai.driver_ia import OpenAIDriverIA
from src.services.ai.tool_gateway import BioinformaticsToolGateway
from src.services.data.context_manager import MongoContextManager
from src.services.data.event_store import MongoEventStore
from src.services.execution.analysis_worker import AnalysisWorker
from src.core.orchestrator import IntelligentOrchestrator

class AppContainer:
    """
    LUIS: Contenedor de Inyección de Dependencias.
    Instancia todos los servicios y sus dependencias en un solo lugar.
    """
    
    def __init__(self, settings_obj):
        self.settings = settings_obj
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando AppContainer 'Antares'...")
        
        # Inicializa clientes de base
        self._init_clients()
        
        # Inicializa servicios de observabilidad
        self._init_observability_services()
        
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
        
        # Inicializa el worker de análisis
        self._init_analysis_worker()
        
        self.logger.info("AppContainer 'Antares' inicializado exitosamente")

    def _init_clients(self):
        """LUIS: Inicializa clientes de base (Redis, MongoDB)."""
        # Cliente Redis
        self.redis_client = aioredis.from_url(
            self.settings.REDIS_URL, 
            decode_responses=True
        )
        
        # Cliente MongoDB
        self.mongo_client = AsyncIOMotorClient(self.settings.MONGO_URL)
        
        self.logger.info("Clientes de base inicializados")

    def _init_observability_services(self):
        """LUIS: Inicializa servicios de observabilidad."""
        self.metrics: IMetricsService = PrometheusMetricsService()
        
        self.logger.info("Servicios de observabilidad inicializados")

    def _init_data_services(self):
        """LUIS: Inicializa servicios de datos."""
        self.context_manager: IContextManager = MongoContextManager(self.mongo_client)
        self.event_store: IEventStore = MongoEventStore(self.mongo_client)
        
        self.logger.info("Servicios de datos inicializados")

    def _init_resilience_services(self):
        """LUIS: Inicializa servicios de resiliencia."""
        self.capacity_manager: ICapacityManager = RedisCapacityManager(
            self.redis_client, 
            self.metrics
        )
        
        # Fábrica de Circuit Breakers
        self.circuit_breaker_factory = lambda name: RedisCircuitBreaker(
            name, 
            self.redis_client, 
            self.metrics
        )
        
        self.logger.info("Servicios de resiliencia inicializados")

    def _init_execution_services(self):
        """LUIS: Inicializa servicios de ejecución."""
        self.sqs_dispatcher: ISQSDispatcher = SQSDispatcher(self.metrics)
        
        self.logger.info("Servicios de ejecución inicializados")

    def _init_ai_services(self):
        """LUIS: Inicializa servicios de IA."""
        # Tool Gateway
        self.tool_gateway: IToolGateway = BioinformaticsToolGateway(
            self.circuit_breaker_factory
        )
        
        # Driver IA
        self.driver_ia: IDriverIA = OpenAIDriverIA(
            self.tool_gateway,
            self.context_manager,
            self.event_store
        )
        
        self.logger.info("Servicios de IA inicializados")

    def _init_orchestrator(self):
        """LUIS: Inicializa el orquestador principal."""
        self.orchestrator: IOrchestrator = IntelligentOrchestrator(
            self.context_manager,
            self.capacity_manager,
            self.sqs_dispatcher,
            self.event_store,
            self.metrics
        )
        
        self.logger.info("Orquestador inicializado")

    def _init_analysis_worker(self):
        """LUIS: Inicializa el worker de análisis."""
        self.analysis_worker: IAnalysisWorker = AnalysisWorker(
            self.driver_ia,
            self.context_manager,
            self.capacity_manager,
            self.event_store
        )
        
        self.logger.info("Analysis Worker inicializado")

    async def health_check(self) -> dict:
        """LUIS: Verifica la salud de todos los servicios."""
        try:
            health_status = {
                "container": "healthy",
                "services": {}
            }
            
            # Verifica Redis
            try:
                await self.redis_client.ping()
                health_status["services"]["redis"] = "healthy"
            except Exception as e:
                health_status["services"]["redis"] = f"unhealthy: {e}"
            
            # Verifica MongoDB
            try:
                await self.mongo_client.admin.command("ping")
                health_status["services"]["mongodb"] = "healthy"
            except Exception as e:
                health_status["services"]["mongodb"] = f"unhealthy: {e}"
            
            # Verifica Orchestrator
            orchestrator_health = await self.orchestrator.health_check()
            health_status["services"]["orchestrator"] = orchestrator_health
            
            # Verifica Analysis Worker
            worker_healthy = await self.analysis_worker.health_check()
            health_status["services"]["analysis_worker"] = "healthy" if worker_healthy else "unhealthy"
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error en health check del contenedor: {e}")
            return {"container": "unhealthy", "error": str(e)}

    async def get_system_info(self) -> dict:
        """LUIS: Obtiene información del sistema."""
        try:
            # Estadísticas del sistema
            system_stats = await self.orchestrator.get_system_stats()
            
            # Estadísticas del worker
            worker_stats = await self.analysis_worker.get_worker_stats()
            
            return {
                "system": system_stats,
                "worker": worker_stats,
                "version": self.settings.PROJECT_VERSION,
                "environment": self.settings.ENVIRONMENT
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo información del sistema: {e}")
            return {"error": str(e)}

    async def initialize_resources(self) -> None:
        """LUIS: Inicializa recursos necesarios (colas, índices, etc.)."""
        try:
            # Crea cola SQS si no existe
            await self.sqs_dispatcher.create_queue_if_not_exists()
            
            # Aquí podrían ir índices de MongoDB, etc.
            
            self.logger.info("Recursos inicializados")
            
        except Exception as e:
            self.logger.error(f"Error inicializando recursos: {e}")
            raise

    async def cleanup_resources(self) -> None:
        """LUIS: Limpia recursos antiguos."""
        try:
            # Limpia contextos antiguos
            contexts_cleaned = await self.context_manager.cleanup_old_contexts()
            
            # Limpia eventos antiguos
            events_cleaned = await self.event_store.cleanup_old_events()
            
            self.logger.info(f"Recursos limpiados: {contexts_cleaned} contextos, {events_cleaned} eventos")
            
        except Exception as e:
            self.logger.error(f"Error limpiando recursos: {e}")

    async def shutdown(self):
        """LUIS: Cierra conexiones y recursos al apagar la app."""
        try:
            self.logger.info("Cerrando recursos del contenedor...")
            
            # Cierra Analysis Worker
            await self.analysis_worker.shutdown()
            
            # Cierra Driver IA
            await self.driver_ia.close()
            
            # Cierra Tool Gateway
            await self.tool_gateway.close()
            
            # Cierra cliente Redis
            await self.redis_client.close()
            
            # Cierra cliente MongoDB
            self.mongo_client.close()
            
            self.logger.info("Recursos del contenedor liberados")
            
        except Exception as e:
            self.logger.error(f"Error cerrando recursos: {e}")