import asyncio
from src.config.database import get_async_session
from src.models.orm import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_user():
    async with get_async_session() as session:
        user = User(
            username="tester",
            hashed_password=pwd_context.hash("tester123")
        )
        session.add(user)
        await session.commit()
        print("Usuario creado: tester / tester123")

asyncio.run(create_user())
