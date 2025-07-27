from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SensorData(BaseModel):
    sensor_id: str
    timestamp: Optional[datetime] = None
    temperatura: Optional[float] = None
    humedad: Optional[float] = None
    co2: Optional[float] = None
    presion: Optional[float] = None
