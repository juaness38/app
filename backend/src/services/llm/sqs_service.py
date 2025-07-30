# -*- coding: utf-8 -*-
"""
SQS Service with Circuit Breaker Pattern
Resilient queue processing for LLM workers
"""
import asyncio
import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from mcp.protocol import CorrelationContext
from services.llm.workers import LLMRequest, LLMResponse, LLMProvider, llm_worker_registry
from services.llm.templates import template_registry

logger = logging.getLogger(__name__)

class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5       # Failures before opening
    recovery_timeout: int = 60       # Seconds before trying half-open
    success_threshold: int = 3       # Successes to close from half-open
    timeout_seconds: int = 30        # Request timeout

class CircuitBreaker:
    """Circuit breaker implementation for resilience"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                self.logger.info(f"Circuit breaker {self.name} entering HALF_OPEN state")
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN")
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout_seconds
            )
            
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful call"""
        self.last_success_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.logger.info(f"Circuit breaker {self.name} CLOSED")
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(f"Circuit breaker {self.name} failed in HALF_OPEN, returning to OPEN")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.logger.error(f"Circuit breaker {self.name} OPENED after {self.failure_count} failures")
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "last_success_time": self.last_success_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout_seconds": self.config.timeout_seconds
            }
        }

class SQSMessage:
    """SQS message wrapper"""
    
    def __init__(self, body: Dict[str, Any], receipt_handle: str):
        self.body = body
        self.receipt_handle = receipt_handle
        self.timestamp = datetime.utcnow()
    
    def get_llm_request(self) -> LLMRequest:
        """Convert SQS message to LLM request"""
        return LLMRequest(
            request_id=self.body["request_id"],
            correlation_context=CorrelationContext(**self.body["correlation_context"]),
            provider=LLMProvider(self.body["provider"]),
            model=self.body["model"],
            messages=self.body["messages"],
            parameters=self.body["parameters"],
            template_name=self.body.get("template_name")
        )

class SQSService:
    """SQS service with circuit breaker and resilience patterns"""
    
    def __init__(self, queue_url: Optional[str] = None):
        self.queue_url = queue_url or "mock://llm-processing-queue"
        self.circuit_breaker = CircuitBreaker(
            "sqs_service",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30,
                success_threshold=2,
                timeout_seconds=10
            )
        )
        
        # Initialize SQS client
        self._initialize_sqs_client()
        
        # Message processing statistics
        self.messages_processed = 0
        self.messages_failed = 0
        self.processing_times = []
        
    def _initialize_sqs_client(self):
        """Initialize SQS client with error handling"""
        try:
            if self.queue_url.startswith("mock://"):
                self.sqs_client = None  # Mock mode
                self.mock_queue: List[Dict[str, Any]] = []
                logger.info("SQS Service initialized in mock mode")
            else:
                self.sqs_client = boto3.client('sqs')
                logger.info("SQS Service initialized with AWS client")
        except (NoCredentialsError, Exception) as e:
            logger.warning(f"Failed to initialize AWS SQS client: {e}, using mock mode")
            self.sqs_client = None
            self.mock_queue = []
    
    async def send_message(self, llm_request: LLMRequest) -> bool:
        """Send LLM request to SQS queue"""
        try:
            message_body = llm_request.to_dict()
            
            if self.sqs_client is None:
                # Mock mode
                self.mock_queue.append({
                    "body": json.dumps(message_body),
                    "receipt_handle": str(uuid.uuid4())
                })
                logger.info(f"Message sent to mock queue: {llm_request.request_id}")
                return True
            else:
                # Real SQS
                await self.circuit_breaker.call(
                    self._send_sqs_message,
                    message_body
                )
                return True
                
        except Exception as e:
            logger.error(f"Failed to send message to SQS: {e}")
            return False
    
    async def _send_sqs_message(self, message_body: Dict[str, Any]):
        """Send message to real SQS"""
        response = self.sqs_client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps(message_body)
        )
        logger.info(f"Message sent to SQS: {response['MessageId']}")
    
    async def receive_messages(self, max_messages: int = 10) -> List[SQSMessage]:
        """Receive messages from SQS queue"""
        try:
            if self.sqs_client is None:
                # Mock mode
                messages = []
                for _ in range(min(max_messages, len(self.mock_queue))):
                    if self.mock_queue:
                        mock_msg = self.mock_queue.pop(0)
                        messages.append(SQSMessage(
                            body=json.loads(mock_msg["body"]),
                            receipt_handle=mock_msg["receipt_handle"]
                        ))
                return messages
            else:
                # Real SQS
                messages = await self.circuit_breaker.call(
                    self._receive_sqs_messages,
                    max_messages
                )
                return messages
                
        except Exception as e:
            logger.error(f"Failed to receive messages from SQS: {e}")
            return []
    
    async def _receive_sqs_messages(self, max_messages: int) -> List[SQSMessage]:
        """Receive messages from real SQS"""
        response = self.sqs_client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=5
        )
        
        messages = []
        for msg in response.get('Messages', []):
            messages.append(SQSMessage(
                body=json.loads(msg['Body']),
                receipt_handle=msg['ReceiptHandle']
            ))
        
        return messages
    
    async def delete_message(self, receipt_handle: str) -> bool:
        """Delete processed message from queue"""
        try:
            if self.sqs_client is None:
                # Mock mode - message already removed in receive_messages
                return True
            else:
                await self.circuit_breaker.call(
                    self._delete_sqs_message,
                    receipt_handle
                )
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete message from SQS: {e}")
            return False
    
    async def _delete_sqs_message(self, receipt_handle: str):
        """Delete message from real SQS"""
        self.sqs_client.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle
        )
    
    async def process_message(self, message: SQSMessage) -> LLMResponse:
        """Process a single SQS message"""
        start_time = time.time()
        
        try:
            llm_request = message.get_llm_request()
            
            # Apply template if specified
            if llm_request.template_name:
                template = template_registry.get_template(llm_request.template_name)
                if template:
                    # Extract variables from parameters
                    template_variables = {
                        key: value for key, value in llm_request.parameters.items()
                        if key in template.variables
                    }
                    
                    # Render template
                    llm_request.messages = template.render(template_variables)
                    logger.info(f"Applied template {llm_request.template_name} to request {llm_request.request_id}")
            
            # Execute LLM request
            response = await llm_worker_registry.execute_request(llm_request)
            
            # Track statistics
            execution_time = time.time() - start_time
            self.processing_times.append(execution_time)
            
            if response.success:
                self.messages_processed += 1
            else:
                self.messages_failed += 1
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.processing_times.append(execution_time)
            self.messages_failed += 1
            
            logger.error(f"Failed to process message: {e}")
            return LLMResponse(
                request_id=message.body.get("request_id", "unknown"),
                success=False,
                error_message=str(e),
                execution_time_ms=int(execution_time * 1000)
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get SQS service statistics"""
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        return {
            "queue_url": self.queue_url if not self.queue_url.startswith("mock://") else "mock_queue",
            "messages_processed": self.messages_processed,
            "messages_failed": self.messages_failed,
            "success_rate": self.messages_processed / (self.messages_processed + self.messages_failed) if (self.messages_processed + self.messages_failed) > 0 else 0,
            "average_processing_time_seconds": avg_processing_time,
            "circuit_breaker_status": self.circuit_breaker.get_status(),
            "mock_queue_size": len(getattr(self, 'mock_queue', [])),
            "is_mock_mode": self.sqs_client is None
        }

class LLMWorkerService:
    """Service for managing LLM workers with SQS integration"""
    
    def __init__(self, sqs_service: SQSService):
        self.sqs_service = sqs_service
        self.is_running = False
        self.worker_tasks: List[asyncio.Task] = []
        self.max_concurrent_workers = 5
        
    async def start_workers(self, num_workers: int = None):
        """Start LLM worker tasks"""
        if self.is_running:
            logger.warning("Workers already running")
            return
        
        num_workers = num_workers or self.max_concurrent_workers
        self.is_running = True
        
        for i in range(num_workers):
            task = asyncio.create_task(self._worker_loop(f"worker_{i}"))
            self.worker_tasks.append(task)
        
        logger.info(f"Started {num_workers} LLM workers")
    
    async def stop_workers(self):
        """Stop LLM worker tasks"""
        self.is_running = False
        
        for task in self.worker_tasks:
            task.cancel()
        
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        self.worker_tasks.clear()
        
        logger.info("Stopped all LLM workers")
    
    async def _worker_loop(self, worker_name: str):
        """Main worker loop"""
        logger.info(f"LLM worker {worker_name} started")
        
        while self.is_running:
            try:
                # Receive messages from queue
                messages = await self.sqs_service.receive_messages(max_messages=5)
                
                if not messages:
                    # No messages, wait briefly
                    await asyncio.sleep(1)
                    continue
                
                # Process messages concurrently
                tasks = []
                for message in messages:
                    task = asyncio.create_task(self._process_message_with_cleanup(message))
                    tasks.append(task)
                
                # Wait for all messages to be processed
                await asyncio.gather(*tasks, return_exceptions=True)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(5)  # Back off on error
        
        logger.info(f"LLM worker {worker_name} stopped")
    
    async def _process_message_with_cleanup(self, message: SQSMessage):
        """Process message and handle cleanup"""
        try:
            # Process the message
            response = await self.sqs_service.process_message(message)
            
            # Delete message from queue if processing succeeded
            if response.success:
                await self.sqs_service.delete_message(message.receipt_handle)
                logger.debug(f"Successfully processed and deleted message {response.request_id}")
            else:
                logger.warning(f"Message processing failed: {response.error_message}")
                # In production, you might want to implement retry logic or DLQ
                await self.sqs_service.delete_message(message.receipt_handle)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")

# Global services
sqs_service = SQSService()
llm_worker_service = LLMWorkerService(sqs_service)