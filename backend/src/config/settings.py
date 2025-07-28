# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - CONFIGURACIÓN MEJORADA
LUIS: Settings con validación avanzada y configuración robusta.
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Settings(BaseSettings):
    """Configuración centralizada con validaciones."""
    
    # === BÁSICO ===
    PROJECT_NAME: str = Field(default="Astroflora Antares Core")
    PROJECT_VERSION: str = Field(default="5.0.0")
    ENVIRONMENT: str = Field(default="dev", pattern="^(dev|staging|prod)$")
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    
    # === BASE DE DATOS ===
    MONGO_URL: str = Field(default="mongodb://localhost:27017")
    DB_NAME: str = Field(default="astroflora_antares")
    
    # === SEGURIDAD ===
    ASTROFLORA_API_KEY: str = Field(default="antares-super-secret-key-2024")
    JWT_SECRET_KEY: str = Field(default="antares-jwt-secret-key-very-secure")
    JWT_ALGORITHM: str = Field(default="HS256")
    
    # === IA CONFIGURATION ===
    OPENAI_API_KEY: str = Field(default="sk-placeholder-openai-key")
    GEMINI_API_KEY: str = Field(default="placeholder-gemini-key")
    ANTHROPIC_API_KEY: str = Field(default="placeholder-anthropic-key")
    
    @validator('OPENAI_API_KEY')
    def validate_openai_key(cls, v):
        """Valida formato de clave OpenAI."""
        if v != "sk-placeholder-openai-key" and not v.startswith('sk-'):
            raise ValueError('Invalid OpenAI API key format')
        return v
    
    @validator('ANTHROPIC_API_KEY')
    def validate_anthropic_key(cls, v):
        """Valida formato de clave Anthropic."""
        if v != "placeholder-anthropic-key" and not v.startswith('sk-ant-'):
            raise ValueError('Invalid Anthropic API key format')
        return v
    
    # === SERVICIOS EXTERNOS ===
    REDIS_URL: str = Field(default="redis://localhost:6379/5")
    SQS_ANALYSIS_QUEUE_URL: str = Field(default="http://localhost:4566/000000000000/astroflora-analysis-queue")
    SQS_DLQ_URL: str = Field(default="http://localhost:4566/000000000000/astroflora-analysis-dlq")
    AWS_REGION: str = Field(default="us-east-1")
    
    # === SERVICIOS BIOINFORMÁTICOS ===
    BLAST_SERVICE_URL: str = Field(default="https://blast.ncbi.nlm.nih.gov/Blast.cgi")
    ALPHAFOLD_SERVICE_URL: str = Field(default="https://alphafold.ebi.ac.uk/api")
    SWISS_MODEL_URL: str = Field(default="https://swissmodel.expasy.org/repository")
    SWISS_DOCK_URL: str = Field(default="http://www.swissdock.ch")
    MAFFT_SERVICE_URL: str = Field(default="https://mafft.cbrc.jp/alignment/server")
    MUSCLE_SERVICE_URL: str = Field(default="https://www.ebi.ac.uk/Tools/msa/muscle")
    
    # === PARÁMETROS DE RESILIENCIA ===
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(default=5, ge=1, le=20)
    CIRCUIT_BREAKER_OPEN_SECONDS: int = Field(default=60, ge=10, le=300)
    RETRY_MAX_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    RETRY_WAIT_MULTIPLIER: int = Field(default=1, ge=1, le=5)
    
    # === GESTIÓN DE CAPACIDAD ===
    MAX_CONCURRENT_JOBS: int = Field(default=10, ge=1, le=100)
    MAX_ANALYSIS_DURATION: int = Field(default=3600, ge=300, le=7200)
    
    # === RATE LIMITING ===
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=60, ge=10, le=1000)
    RATE_LIMIT_ANALYSIS_PER_MINUTE: int = Field(default=10, ge=1, le=50)
    
    # === CACHE SETTINGS ===
    CACHE_TTL_SECONDS: int = Field(default=3600, ge=300, le=86400)
    BLAST_CACHE_TTL: int = Field(default=7200, ge=600, le=86400)
    UNIPROT_CACHE_TTL: int = Field(default=14400, ge=600, le=86400)
    
    # === MONITORING ===
    PROMETHEUS_PORT: int = Field(default=9090, ge=1024, le=65535)
    HEALTH_CHECK_TIMEOUT: int = Field(default=30, ge=5, le=120)
    
    @validator('ENVIRONMENT')
    def validate_environment(cls, v):
        """Valida entorno."""
        valid_envs = ["dev", "staging", "prod"]
        if v not in valid_envs:
            raise ValueError(f'Environment must be one of: {valid_envs}')
        return v
    
    def is_production(self) -> bool:
        """Verifica si está en producción."""
        return self.ENVIRONMENT == "prod"
    
    def has_real_ai_keys(self) -> bool:
        """Verifica si tiene claves de IA reales."""
        return (
            not self.OPENAI_API_KEY.startswith("sk-placeholder") or
            not self.GEMINI_API_KEY.startswith("placeholder") or
            not self.ANTHROPIC_API_KEY.startswith("placeholder")
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Instancia global de configuración
settings = Settings()