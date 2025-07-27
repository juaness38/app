# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - EVENT STORE
LUIS: Almacén de eventos para auditoría y aprendizaje.
"""
import logging
from typing import List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from src.services.interfaces import IEventStore
from src.models.analysis import EventStoreEntry
from src.config.settings import settings

class MongoEventStore(IEventStore):
    """
    LUIS: Event Store usando MongoDB.
    Registra todos los eventos del sistema para auditoría y AFT.
    """
    
    def __init__(self, db_client: AsyncIOMotorClient):
        self.db_client = db_client
        self.db = db_client[settings.DB_NAME]
        self.collection = self.db.event_store
        self.logger = logging.getLogger(__name__)
        self.logger.info("Event Store (MongoDB) inicializado")

    async def store_event(self, event: EventStoreEntry) -> None:
        """LUIS: Almacena un evento en el store."""
        try:
            await self.collection.insert_one(event.model_dump())
            self.logger.debug(f"Evento almacenado: {event.event_type} - {event.context_id}")
            
        except Exception as e:
            self.logger.error(f"Error almacenando evento: {e}")
            raise

    async def get_events(self, context_id: str) -> List[EventStoreEntry]:
        """LUIS: Obtiene todos los eventos de un contexto."""
        try:
            cursor = self.collection.find({"context_id": context_id}).sort("timestamp", 1)
            events = []
            async for doc in cursor:
                events.append(EventStoreEntry(**doc))
            return events
            
        except Exception as e:
            self.logger.error(f"Error obteniendo eventos del contexto {context_id}: {e}")
            return []

    async def get_events_by_type(self, event_type: str) -> List[EventStoreEntry]:
        """LUIS: Obtiene eventos por tipo."""
        try:
            cursor = self.collection.find({"event_type": event_type}).sort("timestamp", -1).limit(1000)
            events = []
            async for doc in cursor:
                events.append(EventStoreEntry(**doc))
            return events
            
        except Exception as e:
            self.logger.error(f"Error obteniendo eventos del tipo {event_type}: {e}")
            return []

    async def get_events_by_agent(self, agent: str) -> List[EventStoreEntry]:
        """LUIS: Obtiene eventos por agente."""
        try:
            cursor = self.collection.find({"agent": agent}).sort("timestamp", -1).limit(1000)
            events = []
            async for doc in cursor:
                events.append(EventStoreEntry(**doc))
            return events
            
        except Exception as e:
            self.logger.error(f"Error obteniendo eventos del agente {agent}: {e}")
            return []

    async def get_events_in_timerange(self, start_time: datetime, end_time: datetime) -> List[EventStoreEntry]:
        """LUIS: Obtiene eventos en un rango de tiempo."""
        try:
            cursor = self.collection.find({
                "timestamp": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }).sort("timestamp", 1)
            
            events = []
            async for doc in cursor:
                events.append(EventStoreEntry(**doc))
            return events
            
        except Exception as e:
            self.logger.error(f"Error obteniendo eventos en rango de tiempo: {e}")
            return []

    async def get_error_events(self, limit: int = 100) -> List[EventStoreEntry]:
        """LUIS: Obtiene eventos de error recientes."""
        try:
            cursor = self.collection.find({
                "event_type": {"$in": ["protocol_failed", "node_failed", "tool_failed"]}
            }).sort("timestamp", -1).limit(limit)
            
            events = []
            async for doc in cursor:
                events.append(EventStoreEntry(**doc))
            return events
            
        except Exception as e:
            self.logger.error(f"Error obteniendo eventos de error: {e}")
            return []

    async def get_performance_metrics(self, context_id: str) -> dict:
        """LUIS: Obtiene métricas de rendimiento de un contexto."""
        try:
            # Busca eventos de inicio y fin
            start_event = await self.collection.find_one({
                "context_id": context_id,
                "event_type": "protocol_started"
            })
            
            end_event = await self.collection.find_one({
                "context_id": context_id,
                "event_type": {"$in": ["protocol_completed", "protocol_failed"]}
            })
            
            # Cuenta eventos de herramientas
            tool_count = await self.collection.count_documents({
                "context_id": context_id,
                "event_type": "tool_result"
            })
            
            # Cuenta errores
            error_count = await self.collection.count_documents({
                "context_id": context_id,
                "event_type": {"$in": ["node_failed", "tool_failed"]}
            })
            
            total_time = None
            if start_event and end_event:
                start_time = start_event["timestamp"]
                end_time = end_event["timestamp"]
                total_time = (end_time - start_time).total_seconds()
            
            return {
                "context_id": context_id,
                "total_execution_time": total_time,
                "tools_used": tool_count,
                "errors_encountered": error_count,
                "completed": end_event is not None,
                "success": end_event and end_event["event_type"] == "protocol_completed"
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo métricas de rendimiento: {e}")
            return {}

    async def cleanup_old_events(self, days_old: int = 90) -> int:
        """LUIS: Limpia eventos antiguos."""
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            result = await self.collection.delete_many({
                "timestamp": {"$lt": cutoff_date}
            })
            
            count = result.deleted_count
            self.logger.info(f"Eventos antiguos limpiados: {count}")
            return count
            
        except Exception as e:
            self.logger.error(f"Error limpiando eventos antiguos: {e}")
            return 0

    async def get_usage_statistics(self) -> dict:
        """LUIS: Obtiene estadísticas de uso del sistema."""
        try:
            # Análisis completados por tipo de protocolo
            pipeline = [
                {"$match": {"event_type": "protocol_completed"}},
                {"$group": {
                    "_id": "$data.protocol_type",
                    "count": {"$sum": 1}
                }}
            ]
            
            protocol_stats = {}
            async for doc in self.collection.aggregate(pipeline):
                protocol_stats[doc["_id"]] = doc["count"]
            
            # Herramientas más usadas
            pipeline = [
                {"$match": {"event_type": "tool_result"}},
                {"$group": {
                    "_id": "$data.tool_name",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            
            tool_stats = {}
            async for doc in self.collection.aggregate(pipeline):
                tool_stats[doc["_id"]] = doc["count"]
            
            # Tasa de éxito
            total_protocols = await self.collection.count_documents({
                "event_type": {"$in": ["protocol_completed", "protocol_failed"]}
            })
            
            completed_protocols = await self.collection.count_documents({
                "event_type": "protocol_completed"
            })
            
            success_rate = (completed_protocols / total_protocols) * 100 if total_protocols > 0 else 0
            
            return {
                "protocols_by_type": protocol_stats,
                "most_used_tools": tool_stats,
                "total_protocols": total_protocols,
                "completed_protocols": completed_protocols,
                "success_rate": success_rate
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas de uso: {e}")
            return {}