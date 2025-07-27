# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - CONFIGURACIÓN CENTRALIZADA
LUIS: Toda la configuración vive aquí. Un solo lugar para gobernar todo.
"""
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    """
    LUIS: Define todas las variables de configuración de la aplicación.
    Carga valores desde el entorno o un archivo .env. No hardcodees nada.
    """
    # LUIS: Configuración del proyecto.
    PROJECT_NAME: str = "Astroflora Antares Core"
    PROJECT_VERSION: str = "5.0.0"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "dev"  # 'dev' o 'prod'

    # LUIS: Configuración de seguridad.
    ASTROFLORA_API_KEY: str = "your-super-secret-astroflora-api-key"
    JWT_SECRET_KEY: str = "a_very_secret_key_for_antares"
    JWT_ALGORITHM: str = "HS256"

    # LUIS: Claves de API para LLMs (placeholders por ahora)
    OPENAI_API_KEY: str = "sk-placeholder-openai-key"
    GEMINI_API_KEY: str = "placeholder-gemini-key"
    ANTHROPIC_API_KEY: str = "placeholder-anthropic-key"

    # LUIS: URLs de servicios externos y dependencias.
    MONGO_URL: str = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME: str = os.environ.get('DB_NAME', 'astroflora_antares')
    REDIS_URL: str = "redis://localhost:6379/5"
    SQS_ANALYSIS_QUEUE_URL: str = "http://localhost:4566/000000000000/astroflora-analysis-queue"
    AWS_REGION: str = "us-east-1"

    # LUIS: Configuración de servicios bioinformáticos
    BLAST_SERVICE_URL: str = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"
    ALPHAFOLD_SERVICE_URL: str = "https://alphafold.ebi.ac.uk/api"
    SWISS_MODEL_URL: str = "https://swissmodel.expasy.org/repository"
    SWISS_DOCK_URL: str = "http://www.swissdock.ch"
    MAFFT_SERVICE_URL: str = "https://mafft.cbrc.jp/alignment/server"
    MUSCLE_SERVICE_URL: str = "https://www.ebi.ac.uk/Tools/msa/muscle"

    # LUIS: Parámetros de resiliencia.
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_OPEN_SECONDS: int = 60
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_WAIT_MULTIPLIER: int = 1

    # LUIS: Parámetros de gestión de capacidad.
    MAX_CONCURRENT_JOBS: int = 10
    MAX_ANALYSIS_DURATION: int = 3600  # 1 hora en segundos

    class Config:
        env_file = ".env"
        extra = "ignore"

# LUIS: Crea una instancia única de la configuración para ser usada en toda la app.
settings = Settings()