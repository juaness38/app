from src.config.database import get_async_session
from src.services.observability.connection import manager as connection_manager

def get_connection_manager():
    return connection_manager

async def get_db():
    async with get_async_session() as session:
        yield session

