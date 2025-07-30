# -*- coding: utf-8 -*-
"""
Test LLM Workers and SQS Service Integration
Phase 3: Testing plug-and-play LLM workers and circuit breakers
"""
import asyncio
import sys
import os
import uuid
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

async def test_llm_workers():
    """Test LLM worker registry and providers"""
    print("🤖 Testing LLM Workers...")
    
    try:
        from services.llm.workers import llm_worker_registry, LLMRequest, LLMProvider
        from mcp.protocol import CorrelationContext
        
        # Test worker initialization
        available_providers = llm_worker_registry.get_available_providers()
        print(f"✅ Available LLM providers: {[p.value for p in available_providers]}")
        
        default_provider = llm_worker_registry.get_default_provider()
        if default_provider:
            print(f"✅ Default provider: {default_provider.value}")
        
        # Test each available provider
        correlation_context = CorrelationContext(
            correlation_id=str(uuid.uuid4()),
            user_id="test_user"
        )
        
        for provider in available_providers:
            worker = llm_worker_registry.get_worker(provider)
            if worker:
                models = worker.get_supported_models()
                default_model = worker.get_default_model()
                print(f"  🔧 {provider.value}: {len(models)} models, default: {default_model}")
                
                # Test request
                request = LLMRequest(
                    request_id=str(uuid.uuid4()),
                    correlation_context=correlation_context,
                    provider=provider,
                    model=default_model,
                    messages=[
                        {"role": "user", "content": "Analyze the protein sequence MKQVFER and predict its function."}
                    ],
                    parameters={"max_tokens": 500, "temperature": 0.3}
                )
                
                response = await worker.execute_request(request)
                print(f"  ✅ {provider.value} execution: success={response.success}, time={response.execution_time_ms}ms")
                
                if response.success:
                    print(f"    📝 Response length: {len(response.response_text)} chars")
                    if response.tokens_used:
                        print(f"    🔢 Tokens used: {response.tokens_used.get('total', 0)}")
        
        # Test worker statistics
        stats = llm_worker_registry.get_all_statistics()
        print(f"✅ LLM Worker Statistics: {stats['total_providers']} providers, default: {stats.get('default_provider')}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM workers test failed: {e}")
        return False

async def test_prompt_templates():
    """Test prompt template system"""
    print("\n📝 Testing Prompt Templates...")
    
    try:
        from services.llm.templates import template_registry, TemplateType
        
        # List available templates
        templates = template_registry.list_templates()
        print(f"✅ Available templates: {templates}")
        
        # Test each template type
        for template_type in TemplateType:
            type_templates = template_registry.list_templates(template_type)
            if type_templates:
                print(f"  📋 {template_type.value}: {type_templates}")
        
        # Test sequence analysis template
        seq_template = template_registry.get_template("sequence_analysis")
        if seq_template:
            messages = template_registry.render_template(
                "sequence_analysis",
                {
                    "sequence": "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPD",
                    "sequence_type": "protein",
                    "context": "Unknown protein from bacterial genome"
                }
            )
            print(f"✅ Sequence analysis template rendered: {len(messages)} messages")
            print(f"  📏 System prompt length: {len(messages[0]['content'])} chars")
            print(f"  📏 User prompt length: {len(messages[1]['content'])} chars")
        
        # Test function prediction template
        func_template = template_registry.get_template("function_prediction")
        if func_template:
            template_info = template_registry.get_template_info("function_prediction")
            print(f"✅ Function prediction template: {len(template_info['variables'])} variables required")
            print(f"  🔧 Variables: {template_info['variables']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Prompt templates test failed: {e}")
        return False

async def test_sqs_service():
    """Test SQS service with circuit breaker"""
    print("\n📨 Testing SQS Service...")
    
    try:
        from services.llm.sqs_service import SQSService, CircuitBreaker, CircuitBreakerConfig
        from services.llm.workers import LLMRequest, LLMProvider
        from mcp.protocol import CorrelationContext
        
        # Test circuit breaker
        circuit_breaker = CircuitBreaker(
            "test_circuit",
            CircuitBreakerConfig(failure_threshold=2, recovery_timeout=5, success_threshold=1)
        )
        
        # Test successful call
        async def success_func():
            return "success"
        
        result = await circuit_breaker.call(success_func)
        print(f"✅ Circuit breaker success test: {result}")
        
        # Test circuit breaker status
        status = circuit_breaker.get_status()
        print(f"✅ Circuit breaker status: state={status['state']}, failures={status['failure_count']}")
        
        # Test SQS service
        sqs_service = SQSService()  # Will use mock mode
        
        # Create test LLM request
        correlation_context = CorrelationContext(
            correlation_id=str(uuid.uuid4()),
            user_id="test_user"
        )
        
        llm_request = LLMRequest(
            request_id=str(uuid.uuid4()),
            correlation_context=correlation_context,
            provider=LLMProvider.OPENAI,
            model="gpt-4o",
            messages=[{"role": "user", "content": "Test message"}],
            parameters={"max_tokens": 100}
        )
        
        # Send message to queue
        sent = await sqs_service.send_message(llm_request)
        print(f"✅ SQS message sent: {sent}")
        
        # Receive messages
        messages = await sqs_service.receive_messages(max_messages=5)
        print(f"✅ SQS messages received: {len(messages)}")
        
        if messages:
            # Process first message
            message = messages[0]
            response = await sqs_service.process_message(message)
            print(f"✅ Message processed: success={response.success}, time={response.execution_time_ms}ms")
            
            # Delete message
            deleted = await sqs_service.delete_message(message.receipt_handle)
            print(f"✅ Message deleted: {deleted}")
        
        # Get SQS statistics
        stats = sqs_service.get_statistics()
        print(f"✅ SQS Statistics: processed={stats['messages_processed']}, failed={stats['messages_failed']}")
        print(f"  🔄 Success rate: {stats['success_rate']:.2f}")
        print(f"  🕒 Avg processing time: {stats['average_processing_time_seconds']:.3f}s")
        print(f"  🚦 Circuit breaker state: {stats['circuit_breaker_status']['state']}")
        
        return True
        
    except Exception as e:
        print(f"❌ SQS service test failed: {e}")
        return False

async def test_llm_worker_service():
    """Test LLM worker service with queue processing"""
    print("\n⚙️ Testing LLM Worker Service...")
    
    try:
        from services.llm.sqs_service import SQSService, LLMWorkerService
        from services.llm.workers import LLMRequest, LLMProvider
        from mcp.protocol import CorrelationContext
        
        # Create services
        sqs_service = SQSService()
        worker_service = LLMWorkerService(sqs_service)
        
        # Add some test messages to the queue
        correlation_context = CorrelationContext(
            correlation_id=str(uuid.uuid4()),
            user_id="test_user"
        )
        
        test_requests = [
            LLMRequest(
                request_id=str(uuid.uuid4()),
                correlation_context=correlation_context,
                provider=LLMProvider.OPENAI,
                model="gpt-4o",
                messages=[{"role": "user", "content": f"Test message {i}"}],
                parameters={"max_tokens": 50},
                template_name="sequence_analysis" if i % 2 == 0 else None
            )
            for i in range(3)
        ]
        
        # Send test messages
        for request in test_requests:
            if request.template_name:
                # Add template variables for template-based requests
                request.parameters.update({
                    "sequence": "MKQVFER",
                    "sequence_type": "protein",
                    "context": "test protein"
                })
            
            await sqs_service.send_message(request)
        
        print(f"✅ Sent {len(test_requests)} test messages to queue")
        
        # Start worker service briefly
        await worker_service.start_workers(num_workers=2)
        print("✅ Started LLM worker service")
        
        # Let workers process for a short time
        await asyncio.sleep(3)
        
        # Stop workers
        await worker_service.stop_workers()
        print("✅ Stopped LLM worker service")
        
        # Check final statistics
        final_stats = sqs_service.get_statistics()
        print(f"✅ Final processing stats: {final_stats['messages_processed']} processed")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM worker service test failed: {e}")
        return False

async def test_template_integration():
    """Test template integration with LLM workers"""
    print("\n🔄 Testing Template Integration...")
    
    try:
        from services.llm.templates import template_registry
        from services.llm.workers import llm_worker_registry, LLMRequest, LLMProvider
        from mcp.protocol import CorrelationContext
        
        # Test template rendering with LLM execution
        correlation_context = CorrelationContext(
            correlation_id=str(uuid.uuid4()),
            user_id="test_user"
        )
        
        # Render sequence analysis template
        messages = template_registry.render_template(
            "sequence_analysis",
            {
                "sequence": "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPD",
                "sequence_type": "protein", 
                "context": "Hypothetical protein from E. coli genome annotation"
            }
        )
        
        print(f"✅ Template rendered: {len(messages)} messages")
        
        # Execute with LLM
        default_provider = llm_worker_registry.get_default_provider()
        if default_provider:
            worker = llm_worker_registry.get_worker(default_provider)
            if worker:
                request = LLMRequest(
                    request_id=str(uuid.uuid4()),
                    correlation_context=correlation_context,
                    provider=default_provider,
                    model=worker.get_default_model(),
                    messages=messages,
                    parameters={"max_tokens": 1000, "temperature": 0.3}
                )
                
                response = await worker.execute_request(request)
                print(f"✅ Template-based LLM execution: success={response.success}")
                
                if response.success and response.response_text:
                    # Try to parse as JSON
                    try:
                        import json
                        parsed = json.loads(response.response_text)
                        print(f"  📊 JSON response keys: {list(parsed.keys())}")
                    except:
                        print(f"  📝 Text response length: {len(response.response_text)} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ Template integration test failed: {e}")
        return False

async def main():
    """Run all LLM worker and SQS integration tests"""
    print("🚀 Starting LLM Workers & SQS Integration Tests (Phase 3)\n")
    
    tests = [
        ("LLM Workers", test_llm_workers),
        ("Prompt Templates", test_prompt_templates),
        ("SQS Service", test_sqs_service),
        ("LLM Worker Service", test_llm_worker_service),
        ("Template Integration", test_template_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n📊 Phase 3 Test Results:")
    print("=" * 70)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All Phase 3 tests passed!")
        print("🔥 LLM workers and SQS integration completed successfully!")
        return 0
    else:
        print("⚠️  Some tests failed - check implementation")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)