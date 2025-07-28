# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - CIRCUIT BREAKER
LUIS: Protege el sistema de fallos en cascada de servicios externos.
"""
import logging
import time
from typing import Any, Callable
import redis.asyncio as aioredis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from src.services.interfaces import ICircuitBreaker, IMetricsService
from src.config.settings import settings
from src.core.exceptions import CircuitBreakerOpenException

class RedisCircuitBreaker(ICircuitBreaker):
    """
    LUIS: Implementación del Circuit Breaker persistente en Redis.
    Protege al sistema de fallos en cascada de servicios externos.
    """
    
    def __init__(self, service_name: str, redis_client: aioredis.Redis, metrics: IMetricsService):
        self.name = service_name
        self.redis = redis_client
        self.metrics = metrics
        self.failure_key = f"astroflora:cb:{self.name}:failures"
        self.state_key = f"astroflora:cb:{self.name}:state"  # "CLOSED", "OPEN", "HALF_OPEN"
        self.last_failure_key = f"astroflora:cb:{self.name}:last_failure"
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Circuit Breaker para '{self.name}' inicializado")

    async def is_open(self) -> bool:
        """LUIS: Comprueba si el circuito está abierto."""
        try:
            state = await self.redis.get(self.state_key)
            if not state:
                # Si no hay estado, asumimos que está cerrado
                await self.redis.set(self.state_key, "CLOSED")
                return False
                
            state = state.decode() if isinstance(state, bytes) else state
            
            if state == "OPEN":
                # Verificamos si ha pasado el tiempo de espera
                last_failure = await self.redis.get(self.last_failure_key)
                if last_failure:
                    last_failure_time = float(last_failure.decode() if isinstance(last_failure, bytes) else last_failure)
                    if time.time() - last_failure_time > settings.CIRCUIT_BREAKER_OPEN_SECONDS:
                        # Pasa a semi-abierto para permitir una prueba
                        await self.redis.set(self.state_key, "HALF_OPEN")
                        self.logger.info(f"Circuit Breaker para '{self.name}' cambió a HALF_OPEN")
                        return False
                return True
                
            elif state == "HALF_OPEN":
                # En semi-abierto, permitimos una llamada de prueba
                return False
                
            return False  # CLOSED
            
        except Exception as e:
            self.logger.error(f"Error verificando estado del circuit breaker: {e}")
            return False

    async def record_failure(self) -> None:
        """LUIS: Registra un fallo. Si se supera el umbral, abre el circuito."""
        try:
            self.metrics.record_external_call_failure(self.name)
            
            # Incrementa el contador de fallos
            failures = await self.redis.incr(self.failure_key)
            await self.redis.expire(self.failure_key, settings.CIRCUIT_BREAKER_OPEN_SECONDS)
            
            # Registra el tiempo del último fallo
            await self.redis.set(self.last_failure_key, str(time.time()))
            
            self.logger.warning(f"Fallo registrado para '{self.name}': {failures}/{settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD}")
            
            if failures >= settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD:
                # Abre el circuito
                await self.redis.set(self.state_key, "OPEN")
                await self.redis.expire(self.state_key, settings.CIRCUIT_BREAKER_OPEN_SECONDS)
                self.logger.error(f"Circuit Breaker para '{self.name}' está ahora ABIERTO")
                
        except Exception as e:
            self.logger.error(f"Error registrando fallo: {e}")

    async def record_success(self) -> None:
        """LUIS: Registra un éxito y cierra el circuito."""
        try:
            # Limpia los fallos y cierra el circuito
            await self.redis.delete(self.failure_key)
            await self.redis.set(self.state_key, "CLOSED")
            await self.redis.delete(self.last_failure_key)
            
            self.logger.debug(f"Éxito registrado para '{self.name}' - Circuit Breaker CERRADO")
            
        except Exception as e:
            self.logger.error(f"Error registrando éxito: {e}")

    async def reset(self) -> None:
        """LUIS: Reinicia manualmente el circuit breaker."""
        try:
            await self.redis.delete(self.failure_key)
            await self.redis.delete(self.last_failure_key)
            await self.redis.set(self.state_key, "CLOSED")
            self.logger.info(f"Circuit Breaker para '{self.name}' reiniciado manualmente")
            
        except Exception as e:
            self.logger.error(f"Error reiniciando circuit breaker: {e}")

    @retry(
        stop=stop_after_attempt(settings.RETRY_MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=settings.RETRY_WAIT_MULTIPLIER, min=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
    )
    async def call(self, async_func: Callable, *args, **kwargs) -> Any:
        """LUIS: Ejecuta la llamada protegida por el circuito y los reintentos."""
        if await self.is_open():
            raise CircuitBreakerOpenException(f"Servicio '{self.name}' no disponible (Circuit Breaker abierto)")

        start_time = time.time()
        try:
            result = await async_func(*args, **kwargs)
            await self.record_success()
            
            duration = time.time() - start_time
            self.metrics.record_external_call(self.name, duration)
            
            return result
            
        except Exception as e:
            await self.record_failure()
            self.logger.error(f"Fallo en llamada a '{self.name}': {e}")
            raise e

    async def get_status(self) -> dict:
        """LUIS: Obtiene el estado actual del circuit breaker."""
        try:
            state = await self.redis.get(self.state_key)
            failures = await self.redis.get(self.failure_key)
            last_failure = await self.redis.get(self.last_failure_key)
            
            state = state.decode() if isinstance(state, bytes) else state or "CLOSED"
            failures = int(failures.decode() if isinstance(failures, bytes) else failures or 0)
            last_failure_time = None
            
            if last_failure:
                last_failure_time = float(last_failure.decode() if isinstance(last_failure, bytes) else last_failure)
            
            return {
                "service": self.name,
                "state": state,
                "failures": failures,
                "threshold": settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                "last_failure": last_failure_time,
                "is_open": state == "OPEN"
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estado: {e}")
            return {
                "service": self.name,
                "state": "UNKNOWN",
                "failures": 0,
                "threshold": settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
                "last_failure": None,
                "is_open": False
            }
class CircuitBreakerFactory:
    """
    LUIS: Factory para crear Circuit Breakers configurados.
    Implementa el patrón Factory para generar instancias de CircuitBreaker.
    """
    
    def __init__(self, redis_client: aioredis.Redis, failure_threshold: int, open_seconds: int):
        """
        Inicializa la factory con configuración compartida.
        
        Args:
            redis_client: Cliente Redis para persistencia
            failure_threshold: Número de fallos antes de abrir el circuito
            open_seconds: Segundos que permanece abierto el circuito
        """
        self.redis_client = redis_client
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds
        self.logger = logging.getLogger(__name__)
        self._metrics = None  # Se inicializa luego
    
    def set_metrics(self, metrics: IMetricsService):
        """Establece el servicio de métricas."""
        self._metrics = metrics
    
    def __call__(self, service_name: str) -> RedisCircuitBreaker:
        """
        Permite usar la factory como una función.
        
        Args:
            service_name: Nombre del servicio a proteger
            
        Returns:
            Instancia configurada de RedisCircuitBreaker
        """
        return self.create_circuit_breaker(service_name)
    
    def create_circuit_breaker(self, service_name: str) -> RedisCircuitBreaker:
        """
        Crea una nueva instancia de CircuitBreaker para un servicio.
        
        Args:
            service_name: Nombre del servicio a proteger
            
        Returns:
            Instancia configurada de RedisCircuitBreaker
        """
        self.logger.info(f"Creando Circuit Breaker para servicio: {service_name}")
        
        # Si no tenemos métricas, creamos un mock simple
        if not self._metrics:
            from src.services.observability.metrics_service import PrometheusMetricsService
            self._metrics = PrometheusMetricsService()
        
        circuit_breaker = RedisCircuitBreaker(
            service_name=service_name,
            redis_client=self.redis_client,
            metrics=self._metrics
        )
        
        return circuit_breaker