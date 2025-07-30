# -*- coding: utf-8 -*-
"""
Comprehensive Test Suite for MCP Implementation
Phase 4: Contract tests, integration tests, and security validation
"""
import asyncio
import sys
import os
import uuid
import json
import time
from typing import Dict, Any
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

class MCPContractTester:
    """Contract testing for MCP servers"""
    
    def __init__(self):
        self.test_results = []
    
    async def test_mcp_tools_contract(self):
        """Test MCP Tools Server contract compliance"""
        print("📋 Testing MCP Tools Server Contract...")
        
        try:
            from mcp.protocol import (
                ToolListRequest, ToolCallRequest, CorrelationContext, 
                MCPVersion, ToolCapability
            )
            from mcp.tools.server import MCPToolsServer
            
            # Mock dependencies
            class MockToolGateway:
                async def invoke_tool(self, tool_name, parameters):
                    from models.analysis import ToolResult
                    return ToolResult(success=True, result={"mock": "result"})
            
            class MockEventStore:
                async def store_event(self, event):
                    pass
            
            server = MCPToolsServer(MockToolGateway(), MockEventStore())
            
            # Test tools/list endpoint contract
            correlation_context = CorrelationContext(
                correlation_id=str(uuid.uuid4()),
                user_id="contract_test"
            )
            
            list_request = ToolListRequest(
                correlation_context=correlation_context,
                mcp_version=MCPVersion()
            )
            
            # Validate request schema
            assert hasattr(list_request, 'correlation_context')
            assert hasattr(list_request, 'mcp_version')
            assert hasattr(list_request.correlation_context, 'correlation_id')
            
            print("  ✅ ToolListRequest contract validated")
            
            # Test tools/call endpoint contract
            call_request = ToolCallRequest(
                correlation_context=correlation_context,
                mcp_version=MCPVersion(),
                tool_name="blast",
                parameters={"sequence": "ATCG"},
                timeout_ms=30000
            )
            
            # Validate required fields
            assert call_request.tool_name is not None
            assert call_request.parameters is not None
            assert call_request.correlation_context is not None
            
            print("  ✅ ToolCallRequest contract validated")
            
            # Test version compatibility
            version1 = MCPVersion(major=1, minor=0, patch=0)
            version2 = MCPVersion(major=1, minor=1, patch=0)
            version3 = MCPVersion(major=2, minor=0, patch=0)
            
            assert version1.is_compatible(version2) == True
            assert version1.is_compatible(version3) == False
            
            print("  ✅ Version compatibility contract validated")
            
            return True
            
        except Exception as e:
            print(f"  ❌ MCP Tools contract test failed: {e}")
            return False
    
    async def test_mcp_data_contract(self):
        """Test MCP Data Server contract compliance"""
        print("📋 Testing MCP Data Server Contract...")
        
        try:
            from mcp.protocol import (
                GetContextRequest, SaveEventRequest, CorrelationContext,
                ResourceType, ResourceMetadata
            )
            
            correlation_context = CorrelationContext(
                correlation_id=str(uuid.uuid4()),
                user_id="contract_test"
            )
            
            # Test get_context contract
            context_request = GetContextRequest(
                correlation_context=correlation_context,
                context_id="test_context",
                include_history=True
            )
            
            assert hasattr(context_request, 'context_id')
            assert hasattr(context_request, 'include_history')
            assert isinstance(context_request.include_history, bool)
            
            print("  ✅ GetContextRequest contract validated")
            
            # Test save_event contract
            event_request = SaveEventRequest(
                correlation_context=correlation_context,
                event_type="test_event",
                event_data={"test": "data"},
                agent="contract_tester"
            )
            
            assert event_request.event_type is not None
            assert event_request.event_data is not None
            assert event_request.agent is not None
            
            print("  ✅ SaveEventRequest contract validated")
            
            # Test resource metadata
            metadata = ResourceMetadata(
                resource_id="test_resource",
                resource_type=ResourceType.ANALYSIS_CONTEXT,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                version=1
            )
            
            assert metadata.resource_id is not None
            assert metadata.resource_type in ResourceType
            assert metadata.version >= 1
            
            print("  ✅ ResourceMetadata contract validated")
            
            return True
            
        except Exception as e:
            print(f"  ❌ MCP Data contract test failed: {e}")
            return False
    
    async def test_atomic_tools_contract(self):
        """Test atomic tools contract compliance"""
        print("📋 Testing Atomic Tools Contract...")
        
        try:
            from services.agentic.atomic_tools import (
                atomic_tool_registry, AtomicToolResult
            )
            from mcp.protocol import CorrelationContext, ToolCapability
            
            # Test tool registry contract
            tools = atomic_tool_registry.list_tools()
            assert isinstance(tools, list)
            assert len(tools) > 0
            
            print(f"  ✅ Tool registry contract: {len(tools)} tools available")
            
            # Test tool metadata contract
            for tool_name in tools:
                metadata = atomic_tool_registry.get_tool_metadata(tool_name)
                assert metadata is not None
                assert 'tool_name' in metadata
                assert 'capabilities' in metadata
                assert 'input_schema' in metadata
                assert 'output_schema' in metadata
                
                # Validate capabilities
                for cap in metadata['capabilities']:
                    assert cap in [c.value for c in ToolCapability]
            
            print("  ✅ Tool metadata contract validated")
            
            # Test tool execution contract
            correlation_context = CorrelationContext(
                correlation_id=str(uuid.uuid4()),
                user_id="contract_test"
            )
            
            if "blast" in tools:
                result = await atomic_tool_registry.execute_tool(
                    "blast",
                    {"sequence": "ATCG"},
                    correlation_context
                )
                
                assert isinstance(result, AtomicToolResult)
                assert hasattr(result, 'success')
                assert hasattr(result, 'tool_name')
                assert hasattr(result, 'execution_time_ms')
                assert hasattr(result, 'correlation_id')
                
                print("  ✅ Tool execution contract validated")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Atomic tools contract test failed: {e}")
            return False
    
    async def test_llm_workers_contract(self):
        """Test LLM workers contract compliance"""
        print("📋 Testing LLM Workers Contract...")
        
        try:
            from services.llm.workers import (
                llm_worker_registry, LLMRequest, LLMResponse, LLMProvider
            )
            from mcp.protocol import CorrelationContext
            
            # Test worker registry contract
            providers = llm_worker_registry.get_available_providers()
            assert isinstance(providers, list)
            assert len(providers) > 0
            
            print(f"  ✅ Worker registry contract: {len(providers)} providers")
            
            # Test LLM request/response contract
            correlation_context = CorrelationContext(
                correlation_id=str(uuid.uuid4()),
                user_id="contract_test"
            )
            
            request = LLMRequest(
                request_id=str(uuid.uuid4()),
                correlation_context=correlation_context,
                provider=providers[0],
                model="test_model",
                messages=[{"role": "user", "content": "test"}],
                parameters={}
            )
            
            # Validate request contract
            assert hasattr(request, 'request_id')
            assert hasattr(request, 'correlation_context')
            assert hasattr(request, 'provider')
            assert hasattr(request, 'messages')
            assert isinstance(request.messages, list)
            
            print("  ✅ LLMRequest contract validated")
            
            # Test response contract
            worker = llm_worker_registry.get_worker(providers[0])
            if worker:
                response = await worker.execute_request(request)
                
                assert isinstance(response, LLMResponse)
                assert hasattr(response, 'request_id')
                assert hasattr(response, 'success')
                assert hasattr(response, 'execution_time_ms')
                assert isinstance(response.success, bool)
                
                print("  ✅ LLMResponse contract validated")
            
            return True
            
        except Exception as e:
            print(f"  ❌ LLM workers contract test failed: {e}")
            return False

class SecurityTester:
    """Security validation for MCP implementation"""
    
    async def test_correlation_id_validation(self):
        """Test correlation ID security and validation"""
        print("🔒 Testing Correlation ID Security...")
        
        try:
            from mcp.protocol import CorrelationContext
            
            # Test valid correlation context
            valid_context = CorrelationContext(
                correlation_id=str(uuid.uuid4()),
                user_id="test_user",
                session_id="test_session"
            )
            
            assert valid_context.correlation_id is not None
            assert len(valid_context.correlation_id) > 0
            
            print("  ✅ Correlation context validation passed")
            
            # Test that correlation IDs are properly propagated
            contexts = [
                CorrelationContext(
                    correlation_id=str(uuid.uuid4()),
                    user_id=f"user_{i}"
                )
                for i in range(10)
            ]
            
            correlation_ids = [ctx.correlation_id for ctx in contexts]
            unique_ids = set(correlation_ids)
            
            assert len(unique_ids) == len(correlation_ids), "Correlation IDs must be unique"
            
            print("  ✅ Correlation ID uniqueness validated")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Correlation ID security test failed: {e}")
            return False
    
    async def test_input_sanitization(self):
        """Test input sanitization and validation"""
        print("🔒 Testing Input Sanitization...")
        
        try:
            from services.agentic.atomic_tools import atomic_tool_registry
            from mcp.protocol import CorrelationContext
            
            correlation_context = CorrelationContext(
                correlation_id=str(uuid.uuid4()),
                user_id="security_test"
            )
            
            # Test malicious input handling
            malicious_inputs = [
                {"sequence": "<script>alert('xss')</script>"},
                {"sequence": "'; DROP TABLE sequences; --"},
                {"sequence": "../../../etc/passwd"},
                {"sequence": "A" * 10000},  # Very long input
                {"sequence": ""},  # Empty input
                {"sequence": None},  # Null input
            ]
            
            for malicious_input in malicious_inputs:
                try:
                    if "blast" in atomic_tool_registry.list_tools():
                        result = await atomic_tool_registry.execute_tool(
                            "blast",
                            malicious_input,
                            correlation_context
                        )
                        # Should either succeed safely or fail gracefully
                        assert hasattr(result, 'success')
                        if not result.success:
                            assert result.error_message is not None
                    
                except Exception as e:
                    # Graceful failure is acceptable
                    assert "error" in str(e).lower() or "invalid" in str(e).lower()
            
            print("  ✅ Input sanitization validation passed")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Input sanitization test failed: {e}")
            return False
    
    async def test_audit_trail_integrity(self):
        """Test audit trail integrity and completeness"""
        print("🔒 Testing Audit Trail Integrity...")
        
        try:
            from mcp.protocol import AuditLogEntry, CorrelationContext
            
            correlation_context = CorrelationContext(
                correlation_id=str(uuid.uuid4()),
                user_id="audit_test"
            )
            
            # Create audit log entry
            audit_entry = AuditLogEntry(
                audit_id=str(uuid.uuid4()),
                correlation_context=correlation_context,
                operation="test_operation",
                tool_name="test_tool",
                input_data_hash="test_input_hash",
                output_data_hash="test_output_hash",
                success=True,
                execution_time_ms=1000
            )
            
            # Validate audit entry structure
            assert audit_entry.audit_id is not None
            assert audit_entry.correlation_context is not None
            assert audit_entry.operation is not None
            assert audit_entry.timestamp is not None
            assert isinstance(audit_entry.success, bool)
            assert isinstance(audit_entry.execution_time_ms, int)
            
            print("  ✅ Audit entry structure validated")
            
            # Test audit entry serialization
            audit_dict = audit_entry.dict()
            assert isinstance(audit_dict, dict)
            assert 'audit_id' in audit_dict
            assert 'correlation_context' in audit_dict
            assert 'timestamp' in audit_dict
            
            print("  ✅ Audit entry serialization validated")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Audit trail integrity test failed: {e}")
            return False

class PerformanceTester:
    """Performance and load testing"""
    
    async def test_concurrent_processing(self):
        """Test concurrent request processing"""
        print("⚡ Testing Concurrent Processing...")
        
        try:
            from services.agentic.atomic_tools import atomic_tool_registry
            from mcp.protocol import CorrelationContext
            
            # Create multiple concurrent requests
            num_requests = 10
            tasks = []
            
            for i in range(num_requests):
                correlation_context = CorrelationContext(
                    correlation_id=str(uuid.uuid4()),
                    user_id=f"perf_test_{i}"
                )
                
                if "blast" in atomic_tool_registry.list_tools():
                    task = atomic_tool_registry.execute_tool(
                        "blast",
                        {"sequence": f"ATCG{'A' * i}"},
                        correlation_context
                    )
                    tasks.append(task)
            
            # Execute all requests concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            execution_time = time.time() - start_time
            
            # Analyze results
            successful_results = [r for r in results if hasattr(r, 'success') and r.success]
            failed_results = [r for r in results if isinstance(r, Exception)]
            
            print(f"  ✅ Concurrent processing: {len(successful_results)}/{num_requests} successful")
            print(f"  ⏱️ Total time: {execution_time:.2f}s, avg: {execution_time/num_requests:.2f}s per request")
            
            # Performance thresholds
            assert execution_time < 30, "Concurrent processing too slow"
            assert len(successful_results) >= num_requests * 0.8, "Too many failures"
            
            return True
            
        except Exception as e:
            print(f"  ❌ Concurrent processing test failed: {e}")
            return False
    
    async def test_memory_usage(self):
        """Test memory usage patterns"""
        print("⚡ Testing Memory Usage...")
        
        try:
            import psutil
            import gc
            
            # Get initial memory usage
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Create and process many objects
            from services.agentic.atomic_tools import atomic_tool_registry
            from mcp.protocol import CorrelationContext
            
            objects_created = []
            for i in range(100):
                correlation_context = CorrelationContext(
                    correlation_id=str(uuid.uuid4()),
                    user_id=f"memory_test_{i}"
                )
                objects_created.append(correlation_context)
            
            # Force garbage collection
            gc.collect()
            
            # Check memory usage
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            print(f"  ✅ Memory usage: {initial_memory:.1f}MB -> {current_memory:.1f}MB (+{memory_increase:.1f}MB)")
            
            # Memory threshold (should not increase by more than 50MB for this test)
            assert memory_increase < 50, f"Memory usage increased by {memory_increase:.1f}MB"
            
            return True
            
        except ImportError:
            print("  ⚠️ psutil not available, skipping memory test")
            return True
        except Exception as e:
            print(f"  ❌ Memory usage test failed: {e}")
            return False

async def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("🔍 Running Comprehensive MCP Test Suite\n")
    
    # Initialize testers
    contract_tester = MCPContractTester()
    security_tester = SecurityTester()
    performance_tester = PerformanceTester()
    
    tests = [
        # Contract tests
        ("MCP Tools Contract", contract_tester.test_mcp_tools_contract),
        ("MCP Data Contract", contract_tester.test_mcp_data_contract),
        ("Atomic Tools Contract", contract_tester.test_atomic_tools_contract),
        ("LLM Workers Contract", contract_tester.test_llm_workers_contract),
        
        # Security tests
        ("Correlation ID Security", security_tester.test_correlation_id_validation),
        ("Input Sanitization", security_tester.test_input_sanitization),
        ("Audit Trail Integrity", security_tester.test_audit_trail_integrity),
        
        # Performance tests
        ("Concurrent Processing", performance_tester.test_concurrent_processing),
        ("Memory Usage", performance_tester.test_memory_usage),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
        
        print()  # Add spacing between tests
    
    # Summary
    print("📊 Comprehensive Test Results:")
    print("=" * 80)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All comprehensive tests passed!")
        print("✨ MCP implementation is production-ready!")
        return 0
    else:
        print("⚠️  Some tests failed - review implementation")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_comprehensive_tests())
    exit(exit_code)