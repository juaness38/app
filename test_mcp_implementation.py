# -*- coding: utf-8 -*-
"""
Basic MCP Servers Test - Verify MCP implementation functionality
"""
import asyncio
import sys
import os
import uuid
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

async def test_mcp_protocol():
    """Test basic MCP protocol functionality"""
    print("🧪 Testing MCP Protocol Models...")
    
    from mcp.protocol import (
        ToolListRequest, ToolCallRequest, GetContextRequest,
        CorrelationContext, MCPVersion, ToolCapability
    )
    
    # Test correlation context
    correlation_context = CorrelationContext(
        correlation_id=str(uuid.uuid4()),
        user_id="test_user",
        session_id="test_session"
    )
    print(f"✅ CorrelationContext created: {correlation_context.correlation_id}")
    
    # Test tool list request
    tool_list_request = ToolListRequest(
        correlation_context=correlation_context,
        filter_capabilities=[ToolCapability.BIOINFORMATICS]
    )
    print(f"✅ ToolListRequest created with filter: {tool_list_request.filter_capabilities}")
    
    # Test tool call request
    tool_call_request = ToolCallRequest(
        correlation_context=correlation_context,
        tool_name="blast",
        parameters={"sequence": "ATCGATCGATCG", "database": "nr"}
    )
    print(f"✅ ToolCallRequest created for tool: {tool_call_request.tool_name}")
    
    # Test MCP version compatibility
    version1 = MCPVersion(major=1, minor=0, patch=0)
    version2 = MCPVersion(major=1, minor=1, patch=0)
    
    print(f"✅ Version compatibility: {version1.is_compatible(version2)}")
    
    return True

async def test_hardware_devices():
    """Test hardware device mocks"""
    print("\n🔧 Testing Hardware Device Mocks...")
    
    from services.hardware.devices import hardware_manager
    
    # List devices
    devices = hardware_manager.list_devices()
    print(f"✅ Found {len(devices)} hardware devices")
    
    for device in devices:
        print(f"  - {device.name} ({device.device_type})")
    
    # Test microscope operation
    try:
        result = await hardware_manager.execute_device_action(
            "microscope_01",
            "capture_image",
            {"exposure_time": 100, "wavelength": 488}
        )
        print(f"✅ Microscope capture test: {result['result']['image_id']}")
    except Exception as e:
        print(f"❌ Microscope test failed: {e}")
        return False
    
    # Test thermal cycler operation
    try:
        result = await hardware_manager.execute_device_action(
            "thermal_cycler_01",
            "get_temperature",
            {"target_temp": 95}
        )
        print(f"✅ Thermal cycler test: {result['result']['current_temp']:.1f}°C")
    except Exception as e:
        print(f"❌ Thermal cycler test failed: {e}")
        return False
    
    return True

async def test_agentic_driver():
    """Test agentic driver basic functionality"""
    print("\n🤖 Testing Agentic DriverIA...")
    
    try:
        from services.ai.agentic_driver_ia import AgenticDriverIA
        from mcp.protocol import CorrelationContext
        
        # Create a mock context manager and event store
        class MockContextManager:
            async def update_progress(self, context_id, progress, message):
                print(f"Progress: {progress}% - {message}")
            
            async def set_results(self, context_id, results):
                print(f"Results set for {context_id}")
            
            async def mark_completed(self, context_id):
                print(f"Context {context_id} marked as completed")
            
            async def mark_failed(self, context_id, error):
                print(f"Context {context_id} marked as failed: {error}")
        
        class MockEventStore:
            async def store_event(self, event):
                print(f"Event stored: {event.get('event_type', 'unknown')}")
        
        # Initialize agentic driver
        driver = AgenticDriverIA(
            context_manager=MockContextManager(),
            event_store=MockEventStore()
        )
        
        print("✅ AgenticDriverIA initialized successfully")
        
        # Test correlation context creation
        correlation_context = CorrelationContext(
            correlation_id=str(uuid.uuid4()),
            user_id="test_user"
        )
        
        # Test enhanced parameter enrichment
        from models.analysis import PromptNode
        
        test_node = PromptNode(
            node_id="test_node",
            name="Test Node",
            tool_name="blast",
            parameters={"sequence": "ATCG", "previous_result": "{blast_result}"}
        )
        
        previous_results = {
            "blast_result": {"hits": ["hit1", "hit2"], "score": 0.95}
        }
        
        enhanced_params = await driver._enhance_node_parameters(
            test_node, 
            previous_results, 
            correlation_context
        )
        
        print(f"✅ Parameter enhancement test: {len(enhanced_params)} parameters")
        print(f"  Enhanced with agentic context: {'_agentic_context' in enhanced_params}")
        
        # Close the driver
        await driver.close()
        
        return True
        
    except Exception as e:
        print(f"❌ AgenticDriverIA test failed: {e}")
        return False

async def main():
    """Run all MCP tests"""
    print("🚀 Starting MCP Implementation Tests\n")
    
    tests = [
        ("MCP Protocol", test_mcp_protocol),
        ("Hardware Devices", test_hardware_devices),
        ("Agentic DriverIA", test_agentic_driver)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    print("\n📊 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All MCP implementation tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed - check implementation")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)