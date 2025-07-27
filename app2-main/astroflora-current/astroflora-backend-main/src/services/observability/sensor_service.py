from src.config.redis_client import get_redis_client
from src.models.dto import SensorData
from src.models.orm import SensorEvent
from sqlalchemy.ext.asyncio import AsyncSession

class SensorService:
    def __init__(self, db: AsyncSession, connection_manager):
        self.db = db
        self.connection_manager = connection_manager

    async def ingest_full_sensor_data(self, data: SensorData):
        timestamp_str = data.timestamp.isoformat() if data.timestamp else None
        
        # --- Guardar en Redis ---
        redis_client = await get_redis_client()
        redis_key = f"sensor:{data.sensor_id}:latest"
        redis_data = {
            "timestamp": timestamp_str,
            "temperatura": str(data.temperatura),
            "humedad": str(data.humedad),
            "presion": str(data.presion),
            "co2": str(data.co2),
        }

        redis_client.hset(redis_key, mapping=redis_data)

        # --- Guardar en PostgreSQL (Neon) ---
        new_record = SensorEvent(
            sensor_id=data.sensor_id,
            timestamp=data.timestamp,
            temperatura=data.temperatura,
            humedad=data.humedad,
            presion=data.presion,
            co2=data.co2,
        )

        self.db.add(new_record)
        await self.db.commit()

        await self.connection_manager.broadcast({
            "type": "sensor_update",
            "data": redis_data | {"sensor_id": data.sensor_id}
        })
