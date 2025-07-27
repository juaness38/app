from abc import ABC, abstractmethod
from src.models.dto import SensorData

class ISensorService(ABC):
    @abstractmethod
    async def ingest_sensor_data(self, data: SensorData) -> None:
        pass