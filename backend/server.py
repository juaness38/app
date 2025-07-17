# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - SERVIDOR PRINCIPAL
LUIS: Servidor de desarrollo rápido para pruebas.
"""
import os
import sys

# Añadir src al path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.main import app

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
