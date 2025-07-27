from fastapi import APIRouter, Depends, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
from src.models.orm import SensorEvent
from src.models.dto import SensorData
from src.services.observability.sensor_service import SensorService
from src.api.dependencies import get_db, get_connection_manager, get_async_session
from src.services.observability.connection import ConnectionManager
from src.config.redis_client import get_redis_client
import redis.asyncio as aioredis
import os

router = APIRouter()
manager = ConnectionManager()

# POST /ingest - Guarda en Redis y luego migra a PostgreSQL (Neon)
@router.post("/ingest", status_code=status.HTTP_204_NO_CONTENT)
async def ingest_sensor_payload(
    data: SensorData,
    db: AsyncSession = Depends(get_db),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
):
    service = SensorService(db, connection_manager)
    await service.ingest_full_sensor_data(data)

# WEBSOCKET /ws/sensors/live - Consulta Redis primero, luego Neon
@router.websocket("/ws/sensors/live/{sensor_id}")
async def websocket_sensor_data(websocket: WebSocket, sensor_id: str):
    await manager.connect(websocket)

    redis = await get_redis_client()

    try:
        while True:
            redis_key = f"sensor:{sensor_id}:latest"
            redis_data = await asyncio.to_thread(redis.hgetall, redis_key)
            
            if isinstance(redis_data, dict):
                await websocket.send_json({
                    "sensor_id": sensor_id,
                    "timestamp": redis_data.get("timestamp"),
                    "temperatura": float(redis_data["temperatura"]) if "temperatura" in redis_data else None,
                    "humedad": float(redis_data["humedad"]) if "humedad" in redis_data else None,
                    "co2": float(redis_data["co2"]) if "co2" in redis_data else None,
                    "presion": float(redis_data["presion"]) if "presion" in redis_data else None,
                })
            else:
                # Consulta PostgreSQL si no hay datos en Redis
                async with get_async_session() as session:
                    result = await session.execute(
                        select(SensorEvent)
                        .where(SensorEvent.sensor_id == sensor_id)
                        .order_by(SensorEvent.timestamp.desc())
                        .limit(1)
                    )
                    event = result.scalars().first()
                    if event:
                        data = {
                            "id": str(event.id),
                            "sensor_id": event.sensor_id,
                            "timestamp": event.timestamp.isoformat(),
                        }
                        if event.temperatura is not None:
                            data["temperatura"] = event.temperatura
                        if event.humedad is not None:
                            data["humedad"] = event.humedad
                        if event.co2 is not None:
                            data["co2"] = event.co2
                        if event.presion is not None:
                            data["presion"] = event.presion
                        await websocket.send_json(data)

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        await redis.close()