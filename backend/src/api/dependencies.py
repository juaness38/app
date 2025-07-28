# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - DEPENDENCIAS MEJORADAS
LUIS: Dependencias con autenticación robusta y container management.
"""
import logging
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.container import AppContainer

# Contenedor global
_container: Optional[AppContainer] = None
logger = logging.getLogger(__name__)

def set_container(container: AppContainer) -> None:
    """LUIS: Establece el contenedor global."""
    global _container
    _container = container

def get_container() -> AppContainer:
    """LUIS: Obtiene el contenedor de dependencias."""
    if _container is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application not properly initialized"
        )
    return _container

def get_container_sync() -> AppContainer:
    """LUIS: Versión síncrona para WebSockets."""
    return get_container()

# Security scheme
security = HTTPBearer(auto_error=False)

async def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """LUIS: Verifica la API key en el header Authorization."""
    # Primero intenta obtener de Authorization Bearer
    if credentials and credentials.credentials:
        api_key = credentials.credentials
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required in Authorization header"
        )
    
    # Obtiene container para verificar configuración
    container = get_container()
    expected_key = container.settings.ASTROFLORA_API_KEY
    
    if api_key != expected_key:
        logger.warning(f"Invalid API key attempt: {api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return api_key

async def verify_api_key_header(x_api_key: Optional[str] = None) -> str:
    """LUIS: Verifica API key en header X-API-Key (alternativo)."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave API requerida"
        )
    
    container = get_container()
    expected_key = container.settings.ASTROFLORA_API_KEY
    
    if x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave API inválida"
        )
    
    return x_api_key