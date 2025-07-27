# -*- coding: utf-8 -*-
"""
ASTROFLORA - CONTENEDOR DE DEPENDENCIAS REFINADO
Combina arquitectura de sensores IoT + análisis científico
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import redis.asyncio as aioredis
from src.config.settings import settings
from src.config.database import AsyncSessionLocal
from src.services.interfaces import *
from src.services.observability.metrics_service import PrometheusMetricsService
from src.services.resilience.capacity_manager import RedisCapacityManager
from src.services.resilience.circuit_breaker import RedisCircuitBreaker
from src.services.execution.sqs_dispatcher import SQSDispatcher
from src.services.ai.driver_ia import OpenAIDriverIA
from src.services.ai.tool_gateway import BioinformaticsToolGateway
from src.services.data.context_manager import PostgreSQLContextManager
from src.services.data.event_store import PostgreSQLEventStore
from src.core.orchestrator import IntelligentOrchestrator
from src.services.observability.sensor_service import SensorService

class AstrofloraContainer:
    """
    Contenedor de dependencias híbrido para:
    - Sensores IoT (temperatura, humedad, CO2, presión)
    - Análisis científico bioinformático
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("🚀 Inicializando Astroflora Container...")
        
        # Inicializa clientes de base
        self._init_clients()
        
        # Servicios de observabilidad
        self._init_observability_services()
        
        # Servicios de datos (PostgreSQL + Redis)
        self._init_data_services()
        
        # Servicios de resiliencia
        self._init_resilience_services()
        
        # Servicios de ejecución
        self._init_execution_services()
        
        # Servicios de IA para análisis científico
        self._init_ai_services()
        
        # Orquestador principal
        self._init_orchestrator()
        
        # Servicios de sensores IoT
        self._init_sensor_services()
        
        self.logger.info("✅ Astroflora Container inicializado exitosamente")

    def _init_clients(self):
        """Inicializa clientes Redis y PostgreSQL."""
        # Cliente Redis
        self.redis_client = aioredis.from_url(
            "redis://localhost:6379", 
            decode_responses=True
        )
        
        # PostgreSQL Session
        self.db_session = AsyncSessionLocal
        
        self.logger.info("✅ Clientes PostgreSQL + Redis inicializados")

    def _init_observability_services(self):
        """Servicios de métricas y monitoreo."""
        self.metrics: IMetricsService = PrometheusMetricsService()
        self.logger.info("✅ Métricas Prometheus inicializadas")

    def _init_data_services(self):
        """Servicios de datos con PostgreSQL."""
        self.context_manager: IContextManager = PostgreSQLContextManager(self.db_session)
        self.event_store: IEventStore = PostgreSQLEventStore(self.db_session)
        self.logger.info("✅ Context Manager y Event Store (PostgreSQL) inicializados")

    def _init_resilience_services(self):
        """Circuit Breakers y gestión de capacidad."""
        self.capacity_manager: ICapacityManager = RedisCapacityManager(
            self.redis_client, 
            self.metrics
        )
        
        # Factory de Circuit Breakers
        self.circuit_breaker_factory = lambda name: RedisCircuitBreaker(
            name, 
            self.redis_client, 
            self.metrics
        )
        
        self.logger.info("✅ Servicios de resiliencia inicializados")

    def _init_execution_services(self):
        """Servicios de ejecución y cola."""
        self.sqs_dispatcher: ISQSDispatcher = SQSDispatcher(self.metrics)
        self.logger.info("✅ Dispatcher SQS inicializado")

    def _init_ai_services(self):
        """Servicios de IA para análisis científico."""
        # Tool Gateway para herramientas bioinformáticas
        self.tool_gateway: IToolGateway = BioinformaticsToolGateway(
            self.circuit_breaker_factory
        )
        
        # Driver IA con OpenAI
        self.driver_ia: IDriverIA = OpenAIDriverIA(
            self.tool_gateway,
            self.context_manager,
            self.event_store
        )
        
        self.logger.info("✅ Driver IA y Tool Gateway inicializados")

    def _init_orchestrator(self):
        """Orquestador principal para análisis científicos."""
        self.orchestrator: IOrchestrator = IntelligentOrchestrator(
            self.context_manager,
            self.capacity_manager,
            self.sqs_dispatcher,
            self.event_store,
            self.metrics
        )
        
        self.logger.info("✅ Intelligent Orchestrator inicializado")

    def _init_sensor_services(self):
        """Servicios específicos para sensores IoT."""
        # Placeholder para el service manager de sensores existente
        # Se integra con tu SensorService actual
        self.logger.info("✅ Servicios de sensores IoT preparados")

    async def health_check(self) -> dict:
        """Health check completo del sistema."""
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
            
            # Verifica PostgreSQL
            try:
                async with self.db_session() as session:
                    await session.execute("SELECT 1")
                health_status["services"]["postgresql"] = "healthy"
            except Exception as e:
                health_status["services"]["postgresql"] = f"unhealthy: {e}"
            
            # Verifica Orchestrator
            orchestrator_health = await self.orchestrator.health_check()
            health_status["services"]["orchestrator"] = orchestrator_health
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error en health check: {e}")
            return {"container": "unhealthy", "error": str(e)}

    async def shutdown(self):
        """Cierra recursos al apagar."""
        try:
            self.logger.info("🔄 Cerrando recursos...")
            
            # Cierra Driver IA
            if hasattr(self.driver_ia, 'close'):
                await self.driver_ia.close()
            
            # Cierra Tool Gateway
            if hasattr(self.tool_gateway, 'close'):
                await self.tool_gateway.close()
            
            # Cierra Redis
            await self.redis_client.close()
            
            self.logger.info("✅ Recursos cerrados correctamente")
            
        except Exception as e:
            self.logger.error(f"Error cerrando recursos: {e}")

# Instancia global del contenedor
container = AstrofloraContainer()