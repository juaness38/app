# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - DEPENDENCIAS DE LA API
LUIS: Dependencias de FastAPI para inyección de servicios.
"""
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from src.container import AppContainer
from src.config.settings import settings

# Instancia global del contenedor
container: AppContainer = None

def get_container() -> AppContainer:
    """LUIS: Dependencia de FastAPI para obtener el contenedor."""
    global container
    if container is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Contenedor no inicializado"
        )
    return container

def set_container(app_container: AppContainer) -> None:
    """LUIS: Establece el contenedor global."""
    global container
    container = app_container

# Esquema de seguridad
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)) -> str:
    """LUIS: Verifica la clave API."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave API requerida"
        )
    
    if api_key != settings.ASTROFLORA_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave API inválida"
        )
    
    return api_key

def get_current_user(api_key: str = Depends(verify_api_key)) -> str:
    """LUIS: Obtiene el usuario actual (placeholder)."""
    # Por ahora, devolvemos un usuario dummy
    return "user_001"