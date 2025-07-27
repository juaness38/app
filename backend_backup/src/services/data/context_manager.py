# -*- coding: utf-8 -*-
"""
ASTROFLORA BACKEND - CONTEXT MANAGER
LUIS: Gestor del contexto de análisis. El cuaderno de laboratorio.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from src.services.interfaces import IContextManager
from src.models.analysis import AnalysisRequest, AnalysisContext, AnalysisStatus
from src.config.settings import settings

class MongoContextManager(IContextManager):
    """
    LUIS: Gestor de contexto usando MongoDB.
    Mantiene el estado de los análisis en curso.
    """
    
    def __init__(self, db_client: AsyncIOMotorClient):
        self.db_client = db_client
        self.db = db_client[settings.DB_NAME]
        self.collection = self.db.analysis_contexts
        self.logger = logging.getLogger(__name__)
        self.logger.info("Context Manager (MongoDB) inicializado")

    async def create_context(self, request: AnalysisRequest, user_id: str) -> AnalysisContext:
        """LUIS: Crea un nuevo contexto de análisis."""
        context = AnalysisContext(
            workspace_id=request.workspace_id,
            user_id=user_id,
            protocol_type=request.protocol_type,
            status=AnalysisStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        try:
            await self.collection.insert_one(context.model_dump())
            self.logger.info(f"Contexto creado: {context.context_id}")
            return context
            
        except Exception as e:
            self.logger.error(f"Error creando contexto: {e}")
            raise

    async def get_context(self, context_id: str) -> Optional[AnalysisContext]:
        """LUIS: Obtiene un contexto por su ID."""
        try:
            doc = await self.collection.find_one({"context_id": context_id})
            if doc:
                return AnalysisContext(**doc)
            return None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo contexto {context_id}: {e}")
            return None

    async def update_context(self, context: AnalysisContext) -> None:
        """LUIS: Actualiza un contexto completo."""
        try:
            context.updated_at = datetime.utcnow()
            await self.collection.replace_one(
                {"context_id": context.context_id},
                context.model_dump()
            )
            self.logger.debug(f"Contexto actualizado: {context.context_id}")
            
        except Exception as e:
            self.logger.error(f"Error actualizando contexto {context.context_id}: {e}")
            raise

    async def update_progress(self, context_id: str, progress: int, step: str) -> None:
        """LUIS: Actualiza el progreso de un análisis."""
        try:
            await self.collection.update_one(
                {"context_id": context_id},
                {
                    "$set": {
                        "progress": progress,
                        "current_step": step,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            self.logger.debug(f"Progreso actualizado {context_id}: {progress}% - {step}")
            
        except Exception as e:
            self.logger.error(f"Error actualizando progreso {context_id}: {e}")
            raise

    async def set_results(self, context_id: str, results: Dict[str, Any]) -> None:
        """LUIS: Establece los resultados de un análisis."""
        try:
            await self.collection.update_one(
                {"context_id": context_id},
                {
                    "$set": {
                        "results": results,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            self.logger.debug(f"Resultados establecidos para {context_id}")
            
        except Exception as e:
            self.logger.error(f"Error estableciendo resultados {context_id}: {e}")
            raise

    async def mark_failed(self, context_id: str, error_message: str) -> None:
        """LUIS: Marca un análisis como fallido."""
        try:
            await self.collection.update_one(
                {"context_id": context_id},
                {
                    "$set": {
                        "status": AnalysisStatus.FAILED,
                        "error_message": error_message,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            self.logger.error(f"Análisis marcado como fallido {context_id}: {error_message}")
            
        except Exception as e:
            self.logger.error(f"Error marcando como fallido {context_id}: {e}")
            raise

    async def mark_completed(self, context_id: str) -> None:
        """LUIS: Marca un análisis como completado."""
        try:
            await self.collection.update_one(
                {"context_id": context_id},
                {
                    "$set": {
                        "status": AnalysisStatus.COMPLETED,
                        "progress": 100,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            self.logger.info(f"Análisis completado: {context_id}")
            
        except Exception as e:
            self.logger.error(f"Error marcando como completado {context_id}: {e}")
            raise

    async def get_contexts_by_user(self, user_id: str, limit: int = 50) -> list:
        """LUIS: Obtiene los contextos de un usuario."""
        try:
            cursor = self.collection.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
            contexts = []
            async for doc in cursor:
                contexts.append(AnalysisContext(**doc))
            return contexts
            
        except Exception as e:
            self.logger.error(f"Error obteniendo contextos del usuario {user_id}: {e}")
            return []

    async def get_contexts_by_status(self, status: AnalysisStatus, limit: int = 100) -> list:
        """LUIS: Obtiene contextos por estado."""
        try:
            cursor = self.collection.find({"status": status}).sort("created_at", -1).limit(limit)
            contexts = []
            async for doc in cursor:
                contexts.append(AnalysisContext(**doc))
            return contexts
            
        except Exception as e:
            self.logger.error(f"Error obteniendo contextos con estado {status}: {e}")
            return []

    async def cleanup_old_contexts(self, days_old: int = 30) -> int:
        """LUIS: Limpia contextos antiguos."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            result = await self.collection.delete_many({
                "created_at": {"$lt": cutoff_date},
                "status": {"$in": [AnalysisStatus.COMPLETED, AnalysisStatus.FAILED]}
            })
            
            count = result.deleted_count
            self.logger.info(f"Contextos antiguos limpiados: {count}")
            return count
            
        except Exception as e:
            self.logger.error(f"Error limpiando contextos antiguos: {e}")
            return 0