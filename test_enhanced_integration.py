# -*- coding: utf-8 -*-
"""
Test Enhanced Atomic Tools Integration with MCP
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

async def test_atomic_tools_integration():
    """Test atomic tools integration with MCP"""
    print("🔬 Testing Enhanced Atomic Tools Integration...")
    
    try:
        from services.agentic.atomic_tools import atomic_tool_registry
        from mcp.protocol import CorrelationContext
        
        # Test tool listing
        tools = atomic_tool_registry.list_tools()
        print(f"✅ Found {len(tools)} atomic tools: {tools}")
        
        # Test tool metadata
        for tool_name in tools:
            metadata = atomic_tool_registry.get_tool_metadata(tool_name)
            if metadata:
                print(f"  📋 {tool_name}: {metadata['capabilities']}")
        
        # Test BLAST tool execution
        correlation_context = CorrelationContext(
            correlation_id=str(uuid.uuid4()),
            user_id="test_user"
        )
        
        blast_result = await atomic_tool_registry.execute_tool(
            "blast",
            {"sequence": "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPDDTSRGQSRALQKAKEASLMKMQ"},
            correlation_context
        )
        
        print(f"✅ BLAST execution: success={blast_result.success}")
        if blast_result.success:
            print(f"  🎯 Found {len(blast_result.result.get('hits', []))} hits")
            print(f"  🕒 Execution time: {blast_result.execution_time_ms}ms")
            print(f"  💡 Suggestions: {blast_result.suggestions}")
        
        # Test MAFFT tool execution
        mafft_result = await atomic_tool_registry.execute_tool(
            "mafft",
            {
                "sequences": [
                    "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPD",
                    "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPE",
                    "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPF"
                ]
            },
            correlation_context
        )
        
        print(f"✅ MAFFT execution: success={mafft_result.success}")
        if mafft_result.success:
            alignment_score = mafft_result.result.get('alignment_score', 0)
            print(f"  📊 Alignment score: {alignment_score:.3f}")
            print(f"  🕒 Execution time: {mafft_result.execution_time_ms}ms")
        
        # Test execution statistics
        stats = atomic_tool_registry.get_execution_statistics()
        print(f"✅ Execution stats: {stats['total_executions']} total, {stats['success_rate']:.2f} success rate")
        
        return True
        
    except Exception as e:
        print(f"❌ Atomic tools integration test failed: {e}")
        return False

async def test_hardware_manager():
    """Test hardware manager integration"""
    print("\n🔧 Testing Hardware Manager Integration...")
    
    try:
        from services.hardware.devices import hardware_manager
        
        # List devices
        devices = hardware_manager.list_devices()
        print(f"✅ Found {len(devices)} hardware devices")
        
        for device in devices:
            print(f"  🔬 {device.name} ({device.device_type.value})")
            
            # Test device status
            status = hardware_manager.get_device_status(device.device_id)
            print(f"    Status: {status['status']}")
            
            # Test device execution (first available action)
            if device.mock_responses:
                first_action = list(device.mock_responses.keys())[0]
                result = await hardware_manager.execute_device_action(
                    device.device_id,
                    first_action,
                    {"test_param": "test_value"}
                )
                print(f"    ✅ {first_action}: {result['result'].get('status', 'completed')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Hardware manager test failed: {e}")
        return False

async def test_mcp_tools_server_integration():
    """Test MCP Tools Server with enhanced integration"""
    print("\n🛠️ Testing MCP Tools Server Integration...")
    
    try:
        from mcp.tools.server import MCPToolsServer
        from mcp.protocol import ToolListRequest, ToolCallRequest, CorrelationContext, MCPVersion
        
        # Mock dependencies
        class MockToolGateway:
            async def invoke_tool(self, tool_name, parameters):
                from models.analysis import ToolResult
                return ToolResult(success=True, result={"mock": "result"})
        
        class MockEventStore:
            async def store_event(self, event):
                pass
        
        # Initialize server
        server = MCPToolsServer(MockToolGateway(), MockEventStore())
        
        # Test tool listing
        correlation_context = CorrelationContext(
            correlation_id=str(uuid.uuid4()),
            user_id="test_user"
        )
        
        print(f"✅ Available tools: {len(server.available_tools)}")
        
        # List atomic tools
        from services.agentic.atomic_tools import atomic_tool_registry
        from services.hardware.devices import hardware_manager
        
        atomic_count = len(atomic_tool_registry.list_tools())
        hardware_count = len(hardware_manager.list_devices())
        
        print(f"  🔬 Atomic tools: {atomic_count}")
        print(f"  🔧 Hardware devices: {hardware_count}")
        print(f"  📋 Legacy tools: {len(server.available_tools) - atomic_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP Tools Server integration test failed: {e}")
        return False

async def main():
    """Run all enhanced integration tests"""
    print("🚀 Starting Enhanced MCP Integration Tests\n")
    
    tests = [
        ("Atomic Tools Integration", test_atomic_tools_integration),
        ("Hardware Manager", test_hardware_manager),
        ("MCP Tools Server Integration", test_mcp_tools_server_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n📊 Enhanced Integration Test Results:")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<35} {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All enhanced integration tests passed!")
        print("🔥 Phase 2 atomic tools migration completed successfully!")
        return 0
    else:
        print("⚠️  Some tests failed - check implementation")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)