# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - GESTOR DE CAPACIDAD
LUIS: Gestiona la carga del sistema usando Redis para prevenir sobrecarga.
"""
import logging
from typing import Optional, Dict
import redis.asyncio as aioredis
from src.services.interfaces import ICapacityManager, IMetricsService
from src.config.settings import settings

class RedisCapacityManager(ICapacityManager):
    """
    LUIS: Gestiona la carga del sistema usando Redis.
    Es el guardián que previene sobrecargar el sistema.
    """
    
    def __init__(self, redis_client: aioredis.Redis, metrics: IMetricsService):
        self.redis = redis_client
        self.metrics = metrics
        self.concurrent_jobs_key = "astroflora:concurrent_jobs"
        self.waitlist_key = "astroflora:waitlist"
        self.logger = logging.getLogger(__name__)
        self.logger.info("Gestor de Capacidad (Redis) inicializado.")

    async def can_process_request(self) -> bool:
        """LUIS: Verifica si hay capacidad para un nuevo trabajo."""
        try:
            # Si Redis no está disponible, siempre permitir procesamiento
            if not self.redis:
                return True
                
            current_jobs = await self.redis.get(self.concurrent_jobs_key)
            current_count = int(current_jobs or 0)
            can_process = current_count < settings.MAX_CONCURRENT_JOBS
            
            # Actualiza métrica de capacidad
            self.metrics.set_current_capacity(current_count)
            
            self.logger.debug(f"Capacidad actual: {current_count}/{settings.MAX_CONCURRENT_JOBS}")
            return can_process
            
        except Exception as e:
            self.logger.error(f"Error verificando capacidad: {e}")
            # En caso de error, permitimos el procesamiento
            return True

    async def add_to_waitlist(self, context_id: str) -> int:
        """LUIS: Añade un trabajo a la lista de espera."""
        try:
            position = await self.redis.rpush(self.waitlist_key, context_id)
            self.metrics.record_job_queued()
            self.logger.info(f"Trabajo {context_id} añadido a lista de espera, posición: {position}")
            return position
            
        except Exception as e:
            self.logger.error(f"Error añadiendo a lista de espera: {e}")
            raise

    async def get_next_from_waitlist(self) -> Optional[str]:
        """LUIS: Obtiene el siguiente trabajo de la lista de espera."""
        try:
            context_id = await self.redis.lpop(self.waitlist_key)
            if context_id:
                self.logger.info(f"Trabajo {context_id} sacado de lista de espera")
                return context_id.decode() if isinstance(context_id, bytes) else context_id
            return None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo de lista de espera: {e}")
            return None

    async def record_job_started(self) -> None:
        """LUIS: Incrementa el contador de trabajos en ejecución."""
        try:
            current_count = await self.redis.incr(self.concurrent_jobs_key)
            self.metrics.set_current_capacity(current_count)
            self.logger.debug(f"Trabajo iniciado. Capacidad: {current_count}/{settings.MAX_CONCURRENT_JOBS}")
            
        except Exception as e:
            self.logger.error(f"Error registrando inicio de trabajo: {e}")

    async def record_job_finished(self) -> None:
        """LUIS: Decrementa el contador de trabajos en ejecución."""
        try:
            current_count = await self.redis.decr(self.concurrent_jobs_key)
            # Aseguramos que no sea negativo
            if current_count < 0:
                await self.redis.set(self.concurrent_jobs_key, 0)
                current_count = 0
                
            self.metrics.set_current_capacity(current_count)
            self.logger.debug(f"Trabajo terminado. Capacidad: {current_count}/{settings.MAX_CONCURRENT_JOBS}")
            
        except Exception as e:
            self.logger.error(f"Error registrando fin de trabajo: {e}")

    async def get_current_capacity(self) -> Dict[str, int]:
        """LUIS: Obtiene información actual de capacidad."""
        try:
            current_jobs = await self.redis.get(self.concurrent_jobs_key)
            waitlist_size = await self.redis.llen(self.waitlist_key)
            
            current_count = int(current_jobs or 0)
            waitlist_count = int(waitlist_size or 0)
            
            return {
                "current_jobs": current_count,
                "max_jobs": settings.MAX_CONCURRENT_JOBS,
                "available_slots": settings.MAX_CONCURRENT_JOBS - current_count,
                "waitlist_size": waitlist_count,
                "utilization_percent": (current_count / settings.MAX_CONCURRENT_JOBS) * 100
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo capacidad actual: {e}")
            return {
                "current_jobs": 0,
                "max_jobs": settings.MAX_CONCURRENT_JOBS,
                "available_slots": settings.MAX_CONCURRENT_JOBS,
                "waitlist_size": 0,
                "utilization_percent": 0.0
            }

    async def reset_capacity(self) -> None:
        """LUIS: Reinicia los contadores de capacidad (útil para debugging)."""
        try:
            await self.redis.set(self.concurrent_jobs_key, 0)
            await self.redis.delete(self.waitlist_key)
            self.logger.info("Capacidad reiniciada")
            
        except Exception as e:
            self.logger.error(f"Error reiniciando capacidad: {e}")