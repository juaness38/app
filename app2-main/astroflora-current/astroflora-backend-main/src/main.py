from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import sensors
from src.api.dependencies import connection_manager
from src.api.routers.auth.router import router as auth_router
from src.config.database import init_db, engine
#import dotenv
import logging


#dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Astroflora APP",
    description="APP para ingesta de datos de sensores desde dispositivos Arduino/ESP32",
    version="0.1.0"
)

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "ws://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sensors.router, prefix="/sensors", tags=["sensors"])
app.include_router(auth_router)

@app.on_event("startup")
async def on_startup():
    print("🚀 Iniciando servidor...")
    await init_db(engine)

@app.websocket("/ws/sensors")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        connection_manager.disconnect(websocket)
