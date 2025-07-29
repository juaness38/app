# -*- coding: utf-8 -*-
"""
Plug-and-Play LLM Workers for MCP Architecture
Supports OpenAI, Claude, Gemini with unified interface and SQS integration
"""
import asyncio
import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import httpx

from mcp.protocol import CorrelationContext
from config.settings import settings

logger = logging.getLogger(__name__)

class LLMProvider(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"

@dataclass
class LLMRequest:
    """Request to LLM worker"""
    request_id: str
    correlation_context: CorrelationContext
    provider: LLMProvider
    model: str
    messages: List[Dict[str, str]]
    parameters: Dict[str, Any]
    template_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "correlation_context": self.correlation_context.dict(),
            "provider": self.provider.value,
            "model": self.model,
            "messages": self.messages,
            "parameters": self.parameters,
            "template_name": self.template_name
        }

@dataclass
class LLMResponse:
    """Response from LLM worker"""
    request_id: str
    success: bool
    response_text: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    tokens_used: Optional[Dict[str, int]] = None
    model_used: Optional[str] = None
    provider_metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "success": self.success,
            "response_text": self.response_text,
            "response_data": self.response_data,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "tokens_used": self.tokens_used,
            "model_used": self.model_used,
            "provider_metadata": self.provider_metadata
        }

class LLMWorker(ABC):
    """Base class for LLM workers"""
    
    def __init__(self, provider: LLMProvider, api_key: str):
        self.provider = provider
        self.api_key = api_key
        self.logger = logging.getLogger(f"{__name__}.{provider.value}")
        self.http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        
        # Statistics tracking
        self.total_requests = 0
        self.successful_requests = 0
        self.total_tokens_used = 0
        self.total_execution_time_ms = 0
    
    @abstractmethod
    async def execute_request(self, request: LLMRequest) -> LLMResponse:
        """Execute LLM request"""
        pass
    
    @abstractmethod
    def get_supported_models(self) -> List[str]:
        """Get list of supported models"""
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """Get default model for this provider"""
        pass
    
    def track_request(self, response: LLMResponse):
        """Track request statistics"""
        self.total_requests += 1
        if response.success:
            self.successful_requests += 1
        
        self.total_execution_time_ms += response.execution_time_ms
        
        if response.tokens_used:
            self.total_tokens_used += response.tokens_used.get("total", 0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get worker statistics"""
        return {
            "provider": self.provider.value,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
            "total_tokens_used": self.total_tokens_used,
            "average_execution_time_ms": self.total_execution_time_ms / self.total_requests if self.total_requests > 0 else 0,
            "supported_models": self.get_supported_models()
        }
    
    async def close(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()

class OpenAIWorker(LLMWorker):
    """OpenAI LLM worker implementation"""
    
    def __init__(self, api_key: str):
        super().__init__(LLMProvider.OPENAI, api_key)
        self.base_url = "https://api.openai.com/v1"
        
        # Configure HTTP client with OpenAI headers
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    async def execute_request(self, request: LLMRequest) -> LLMResponse:
        """Execute OpenAI request"""
        start_time = time.time()
        
        try:
            # Handle simulation mode
            if self.api_key == "sk-placeholder-openai-key":
                return await self._simulate_openai_response(request, start_time)
            
            # Prepare OpenAI API request
            api_request = {
                "model": request.model,
                "messages": request.messages,
                **request.parameters
            }
            
            response = await self.http_client.post(
                f"{self.base_url}/chat/completions",
                json=api_request
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                result = response.json()
                
                llm_response = LLMResponse(
                    request_id=request.request_id,
                    success=True,
                    response_text=result["choices"][0]["message"]["content"],
                    response_data=result,
                    execution_time_ms=execution_time_ms,
                    tokens_used={
                        "prompt": result.get("usage", {}).get("prompt_tokens", 0),
                        "completion": result.get("usage", {}).get("completion_tokens", 0),
                        "total": result.get("usage", {}).get("total_tokens", 0)
                    },
                    model_used=result.get("model"),
                    provider_metadata={
                        "finish_reason": result["choices"][0].get("finish_reason"),
                        "system_fingerprint": result.get("system_fingerprint")
                    }
                )
                
                self.track_request(llm_response)
                return llm_response
            else:
                error_message = f"OpenAI API error: {response.status_code} - {response.text}"
                llm_response = LLMResponse(
                    request_id=request.request_id,
                    success=False,
                    error_message=error_message,
                    execution_time_ms=execution_time_ms
                )
                self.track_request(llm_response)
                return llm_response
                
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            llm_response = LLMResponse(
                request_id=request.request_id,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time_ms
            )
            self.track_request(llm_response)
            return llm_response
    
    async def _simulate_openai_response(self, request: LLMRequest, start_time: float) -> LLMResponse:
        """Simulate OpenAI response for development"""
        await asyncio.sleep(1.5)  # Simulate API latency
        
        # Generate realistic mock response based on messages
        last_message = request.messages[-1]["content"] if request.messages else ""
        
        # Simulate different response types based on content
        if "json" in last_message.lower():
            mock_response = {
                "analysis": "Mock analysis result",
                "confidence": 0.75,
                "findings": ["Mock finding 1", "Mock finding 2"],
                "recommendations": ["Mock recommendation"]
            }
            response_text = json.dumps(mock_response, indent=2)
        else:
            response_text = f"This is a simulated {request.model} response analyzing: {last_message[:100]}..."
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        llm_response = LLMResponse(
            request_id=request.request_id,
            success=True,
            response_text=response_text,
            response_data={"simulated": True},
            execution_time_ms=execution_time_ms,
            tokens_used={
                "prompt": len(last_message) // 4,  # Rough token estimate
                "completion": len(response_text) // 4,
                "total": (len(last_message) + len(response_text)) // 4
            },
            model_used=request.model,
            provider_metadata={"simulated": True}
        )
        
        self.track_request(llm_response)
        return llm_response
    
    def get_supported_models(self) -> List[str]:
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]
    
    def get_default_model(self) -> str:
        return "gpt-4o"

class AnthropicWorker(LLMWorker):
    """Anthropic Claude LLM worker implementation"""
    
    def __init__(self, api_key: str):
        super().__init__(LLMProvider.ANTHROPIC, api_key)
        self.base_url = "https://api.anthropic.com/v1"
        
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
        )
    
    async def execute_request(self, request: LLMRequest) -> LLMResponse:
        """Execute Anthropic request"""
        start_time = time.time()
        
        try:
            # Handle simulation mode
            if self.api_key == "placeholder-anthropic-key":
                return await self._simulate_anthropic_response(request, start_time)
            
            # Convert messages to Anthropic format
            messages = self._convert_messages_to_anthropic(request.messages)
            
            api_request = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.parameters.get("max_tokens", 1000),
                **{k: v for k, v in request.parameters.items() if k != "max_tokens"}
            }
            
            response = await self.http_client.post(
                f"{self.base_url}/messages",
                json=api_request
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                result = response.json()
                
                llm_response = LLMResponse(
                    request_id=request.request_id,
                    success=True,
                    response_text=result["content"][0]["text"],
                    response_data=result,
                    execution_time_ms=execution_time_ms,
                    tokens_used={
                        "prompt": result.get("usage", {}).get("input_tokens", 0),
                        "completion": result.get("usage", {}).get("output_tokens", 0),
                        "total": result.get("usage", {}).get("input_tokens", 0) + result.get("usage", {}).get("output_tokens", 0)
                    },
                    model_used=result.get("model"),
                    provider_metadata={
                        "stop_reason": result.get("stop_reason"),
                        "stop_sequence": result.get("stop_sequence")
                    }
                )
                
                self.track_request(llm_response)
                return llm_response
            else:
                error_message = f"Anthropic API error: {response.status_code} - {response.text}"
                llm_response = LLMResponse(
                    request_id=request.request_id,
                    success=False,
                    error_message=error_message,
                    execution_time_ms=execution_time_ms
                )
                self.track_request(llm_response)
                return llm_response
                
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            llm_response = LLMResponse(
                request_id=request.request_id,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time_ms
            )
            self.track_request(llm_response)
            return llm_response
    
    def _convert_messages_to_anthropic(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Convert OpenAI-style messages to Anthropic format"""
        converted = []
        for msg in messages:
            if msg["role"] == "system":
                # Anthropic handles system messages differently
                converted.append({"role": "assistant", "content": f"[System: {msg['content']}]"})
            else:
                converted.append(msg)
        return converted
    
    async def _simulate_anthropic_response(self, request: LLMRequest, start_time: float) -> LLMResponse:
        """Simulate Anthropic response"""
        await asyncio.sleep(1.8)  # Simulate API latency
        
        last_message = request.messages[-1]["content"] if request.messages else ""
        response_text = f"This is a simulated Claude response analyzing: {last_message[:100]}..."
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        llm_response = LLMResponse(
            request_id=request.request_id,
            success=True,
            response_text=response_text,
            response_data={"simulated": True},
            execution_time_ms=execution_time_ms,
            tokens_used={
                "prompt": len(last_message) // 4,
                "completion": len(response_text) // 4,
                "total": (len(last_message) + len(response_text)) // 4
            },
            model_used=request.model,
            provider_metadata={"simulated": True}
        )
        
        self.track_request(llm_response)
        return llm_response
    
    def get_supported_models(self) -> List[str]:
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]
    
    def get_default_model(self) -> str:
        return "claude-3-5-sonnet-20241022"

class GoogleWorker(LLMWorker):
    """Google Gemini LLM worker implementation"""
    
    def __init__(self, api_key: str):
        super().__init__(LLMProvider.GOOGLE, api_key)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={"Content-Type": "application/json"}
        )
    
    async def execute_request(self, request: LLMRequest) -> LLMResponse:
        """Execute Google request"""
        start_time = time.time()
        
        try:
            # Handle simulation mode
            if self.api_key == "placeholder-gemini-key":
                return await self._simulate_google_response(request, start_time)
            
            # Convert messages to Google format
            contents = self._convert_messages_to_google(request.messages)
            
            api_request = {
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": request.parameters.get("max_tokens", 1000),
                    "temperature": request.parameters.get("temperature", 0.7),
                    "topP": request.parameters.get("top_p", 1.0),
                    "topK": request.parameters.get("top_k", 40)
                }
            }
            
            response = await self.http_client.post(
                f"{self.base_url}/models/{request.model}:generateContent?key={self.api_key}",
                json=api_request
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                result = response.json()
                
                candidate = result["candidates"][0]
                content = candidate["content"]["parts"][0]["text"]
                
                llm_response = LLMResponse(
                    request_id=request.request_id,
                    success=True,
                    response_text=content,
                    response_data=result,
                    execution_time_ms=execution_time_ms,
                    tokens_used={
                        "prompt": result.get("usageMetadata", {}).get("promptTokenCount", 0),
                        "completion": result.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                        "total": result.get("usageMetadata", {}).get("totalTokenCount", 0)
                    },
                    model_used=request.model,
                    provider_metadata={
                        "finish_reason": candidate.get("finishReason"),
                        "safety_ratings": candidate.get("safetyRatings", [])
                    }
                )
                
                self.track_request(llm_response)
                return llm_response
            else:
                error_message = f"Google API error: {response.status_code} - {response.text}"
                llm_response = LLMResponse(
                    request_id=request.request_id,
                    success=False,
                    error_message=error_message,
                    execution_time_ms=execution_time_ms
                )
                self.track_request(llm_response)
                return llm_response
                
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            llm_response = LLMResponse(
                request_id=request.request_id,
                success=False,
                error_message=str(e),
                execution_time_ms=execution_time_ms
            )
            self.track_request(llm_response)
            return llm_response
    
    def _convert_messages_to_google(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Convert OpenAI-style messages to Google format"""
        contents = []
        for msg in messages:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        return contents
    
    async def _simulate_google_response(self, request: LLMRequest, start_time: float) -> LLMResponse:
        """Simulate Google response"""
        await asyncio.sleep(1.3)  # Simulate API latency
        
        last_message = request.messages[-1]["content"] if request.messages else ""
        response_text = f"This is a simulated Gemini response analyzing: {last_message[:100]}..."
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        llm_response = LLMResponse(
            request_id=request.request_id,
            success=True,
            response_text=response_text,
            response_data={"simulated": True},
            execution_time_ms=execution_time_ms,
            tokens_used={
                "prompt": len(last_message) // 4,
                "completion": len(response_text) // 4,
                "total": (len(last_message) + len(response_text)) // 4
            },
            model_used=request.model,
            provider_metadata={"simulated": True}
        )
        
        self.track_request(llm_response)
        return llm_response
    
    def get_supported_models(self) -> List[str]:
        return [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro"
        ]
    
    def get_default_model(self) -> str:
        return "gemini-1.5-pro"

class LLMWorkerRegistry:
    """Registry for managing LLM workers"""
    
    def __init__(self):
        self.workers: Dict[LLMProvider, LLMWorker] = {}
        self._initialize_workers()
    
    def _initialize_workers(self):
        """Initialize workers based on available API keys"""
        
        # Initialize OpenAI worker
        openai_key = settings.OPENAI_API_KEY
        if openai_key:
            self.workers[LLMProvider.OPENAI] = OpenAIWorker(openai_key)
            logger.info("OpenAI worker initialized")
        
        # Initialize Anthropic worker
        anthropic_key = settings.ANTHROPIC_API_KEY
        if anthropic_key:
            self.workers[LLMProvider.ANTHROPIC] = AnthropicWorker(anthropic_key)
            logger.info("Anthropic worker initialized")
        
        # Initialize Google worker
        gemini_key = settings.GEMINI_API_KEY
        if gemini_key:
            self.workers[LLMProvider.GOOGLE] = GoogleWorker(gemini_key)
            logger.info("Google worker initialized")
        
        logger.info(f"LLM Worker Registry initialized with {len(self.workers)} providers")
    
    def get_worker(self, provider: LLMProvider) -> Optional[LLMWorker]:
        """Get worker by provider"""
        return self.workers.get(provider)
    
    def get_available_providers(self) -> List[LLMProvider]:
        """Get list of available providers"""
        return list(self.workers.keys())
    
    def get_default_provider(self) -> Optional[LLMProvider]:
        """Get default provider (prefer OpenAI, then Anthropic, then Google)"""
        if LLMProvider.OPENAI in self.workers:
            return LLMProvider.OPENAI
        elif LLMProvider.ANTHROPIC in self.workers:
            return LLMProvider.ANTHROPIC
        elif LLMProvider.GOOGLE in self.workers:
            return LLMProvider.GOOGLE
        return None
    
    async def execute_request(self, request: LLMRequest) -> LLMResponse:
        """Execute request using appropriate worker"""
        worker = self.get_worker(request.provider)
        if not worker:
            return LLMResponse(
                request_id=request.request_id,
                success=False,
                error_message=f"Provider {request.provider} not available"
            )
        
        return await worker.execute_request(request)
    
    def get_all_statistics(self) -> Dict[str, Any]:
        """Get statistics for all workers"""
        stats = {}
        for provider, worker in self.workers.items():
            stats[provider.value] = worker.get_statistics()
        
        return {
            "workers": stats,
            "total_providers": len(self.workers),
            "available_providers": [p.value for p in self.get_available_providers()],
            "default_provider": self.get_default_provider().value if self.get_default_provider() else None
        }
    
    async def close_all(self):
        """Close all workers"""
        for worker in self.workers.values():
            await worker.close()

# Global LLM worker registry
llm_worker_registry = LLMWorkerRegistry()