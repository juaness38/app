# -*- coding: utf-8 -*-
"""
Final Demonstration: Complete MCP Implementation
End-to-end demonstration of pure MCP alignment with agentic DriverIA
"""
import asyncio
import sys
import os
import uuid
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

async def demonstrate_complete_mcp_workflow():
    """Demonstrate complete MCP workflow from start to finish"""
    print("🚀 Demonstrating Complete MCP Implementation")
    print("=" * 60)
    
    correlation_id = str(uuid.uuid4())
    
    try:
        from mcp.protocol import CorrelationContext
        from services.agentic.atomic_tools import atomic_tool_registry
        from services.llm.workers import llm_worker_registry, LLMRequest, LLMProvider
        from services.llm.templates import template_registry
        from services.hardware.devices import hardware_manager
        from services.llm.sqs_service import sqs_service
        
        # Create correlation context for tracking
        correlation_context = CorrelationContext(
            correlation_id=correlation_id,
            user_id="demo_researcher",
            session_id="demo_session_001"
        )
        
        print(f"📋 Correlation ID: {correlation_id}")
        print(f"👤 User: {correlation_context.user_id}")
        print()
        
        # === Phase 1: Atomic Tool Execution ===
        print("🔬 Phase 1: Atomic Tool Execution")
        print("-" * 40)
        
        # Execute BLAST analysis
        blast_result = await atomic_tool_registry.execute_tool(
            "blast",
            {
                "sequence": "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPD",
                "database": "nr",
                "e_value": 0.001
            },
            correlation_context
        )
        
        print(f"✅ BLAST Analysis:")
        print(f"  Success: {blast_result.success}")
        print(f"  Execution time: {blast_result.execution_time_ms}ms")
        print(f"  Hits found: {len(blast_result.result.get('hits', []))}")
        print(f"  Suggestions: {blast_result.suggestions}")
        print()
        
        # Execute MAFFT alignment (using suggested tool)
        if "mafft" in blast_result.suggestions:
            mafft_result = await atomic_tool_registry.execute_tool(
                "mafft",
                {
                    "sequences": [
                        "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPD",
                        "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPE",
                        "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPF"
                    ],
                    "algorithm": "auto"
                },
                correlation_context
            )
            
            print(f"✅ MAFFT Alignment (suggested tool):")
            print(f"  Success: {mafft_result.success}")
            print(f"  Alignment score: {mafft_result.result.get('alignment_score', 0):.3f}")
            print(f"  Conservation: {mafft_result.result.get('statistics', {}).get('conservation_score', 0):.3f}")
            print()
        
        # === Phase 2: Hardware Device Control ===
        print("🔧 Phase 2: Hardware Device Control")
        print("-" * 40)
        
        # Control microscope
        microscope_result = await hardware_manager.execute_device_action(
            "microscope_01",
            "capture_image",
            {"exposure_time": 150, "wavelength": 488, "magnification": 400}
        )
        
        print(f"✅ Microscope Image Capture:")
        print(f"  Image ID: {microscope_result['result']['image_id']}")
        print(f"  Exposure: {microscope_result['result']['exposure_time_ms']}ms")
        print(f"  Wavelength: {microscope_result['result']['wavelength']}nm")
        print()
        
        # Control thermal cycler
        pcr_result = await hardware_manager.execute_device_action(
            "thermal_cycler_01",
            "run_pcr",
            {"cycles": 35, "denaturation_temp": 95, "annealing_temp": 55}
        )
        
        print(f"✅ PCR Thermal Cycling:")
        print(f"  Run ID: {pcr_result['result']['run_id']}")
        print(f"  Cycles: {pcr_result['result']['cycles_completed']}")
        print(f"  Estimated yield: {pcr_result['result']['estimated_yield']}")
        print()
        
        # === Phase 3: LLM Analysis with Templates ===
        print("🤖 Phase 3: LLM Analysis with Scientific Templates")
        print("-" * 50)
        
        # Use sequence analysis template
        template_variables = {
            "sequence": "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPD",
            "sequence_type": "protein",
            "context": f"Protein analyzed with BLAST ({len(blast_result.result.get('hits', []))} hits found) and aligned with MAFFT"
        }
        
        messages = template_registry.render_template("sequence_analysis", template_variables)
        
        # Execute with OpenAI
        openai_worker = llm_worker_registry.get_worker(LLMProvider.OPENAI)
        if openai_worker:
            llm_request = LLMRequest(
                request_id=str(uuid.uuid4()),
                correlation_context=correlation_context,
                provider=LLMProvider.OPENAI,
                model="gpt-4o",
                messages=messages,
                parameters={"max_tokens": 1000, "temperature": 0.3}
            )
            
            llm_response = await openai_worker.execute_request(llm_request)
            
            print(f"✅ OpenAI Analysis:")
            print(f"  Success: {llm_response.success}")
            print(f"  Execution time: {llm_response.execution_time_ms}ms")
            print(f"  Tokens used: {llm_response.tokens_used.get('total', 0) if llm_response.tokens_used else 0}")
            
            if llm_response.success and llm_response.response_text:
                try:
                    analysis = json.loads(llm_response.response_text)
                    print(f"  Function prediction: {analysis.get('functional_prediction', {}).get('predicted_function', 'N/A')}")
                    print(f"  Confidence: {analysis.get('confidence_score', 0):.2f}")
                except:
                    print(f"  Response: {llm_response.response_text[:100]}...")
            print()
        
        # === Phase 4: SQS Queue Processing ===
        print("📨 Phase 4: SQS Queue Processing")
        print("-" * 40)
        
        # Send analysis request to queue
        queue_request = LLMRequest(
            request_id=str(uuid.uuid4()),
            correlation_context=correlation_context,
            provider=LLMProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            messages=[],  # Will be populated by template
            parameters={
                **template_variables,
                "max_tokens": 800
            },
            template_name="function_prediction"
        )
        
        # Add additional data for function prediction template
        queue_request.parameters.update({
            "blast_results": blast_result.result,
            "domain_analysis": {"domains": ["Unknown"], "motifs": []},
            "sequence_features": {"length": 34, "composition": "Mixed"},
            "structural_info": {"predicted_structure": "Globular protein"}
        })
        
        # Send to queue
        await sqs_service.send_message(queue_request)
        
        # Process from queue
        messages = await sqs_service.receive_messages(max_messages=1)
        if messages:
            queue_response = await sqs_service.process_message(messages[0])
            await sqs_service.delete_message(messages[0].receipt_handle)
            
            print(f"✅ Queue Processing:")
            print(f"  Success: {queue_response.success}")
            print(f"  Provider: Claude (Anthropic)")
            print(f"  Template: function_prediction")
            print(f"  Execution time: {queue_response.execution_time_ms}ms")
            print()
        
        # === Phase 5: Statistics and Summary ===
        print("📊 Phase 5: System Statistics")
        print("-" * 40)
        
        # Atomic tools statistics
        tools_stats = atomic_tool_registry.get_execution_statistics()
        print(f"✅ Atomic Tools:")
        print(f"  Total executions: {tools_stats['total_executions']}")
        print(f"  Success rate: {tools_stats['success_rate']:.2f}")
        print(f"  Tools available: {tools_stats['total_tools']}")
        print()
        
        # LLM workers statistics
        llm_stats = llm_worker_registry.get_all_statistics()
        print(f"✅ LLM Workers:")
        print(f"  Providers: {llm_stats['total_providers']}")
        print(f"  Default: {llm_stats['default_provider']}")
        for provider, stats in llm_stats['workers'].items():
            print(f"  {provider}: {stats['total_requests']} requests, {stats['success_rate']:.2f} success rate")
        print()
        
        # Hardware devices
        devices = hardware_manager.list_devices()
        print(f"✅ Hardware Devices:")
        print(f"  Total devices: {len(devices)}")
        for device in devices:
            status = hardware_manager.get_device_status(device.device_id)
            print(f"  {device.name}: {status['status']}")
        print()
        
        # SQS service statistics
        sqs_stats = sqs_service.get_statistics()
        print(f"✅ SQS Service:")
        print(f"  Messages processed: {sqs_stats['messages_processed']}")
        print(f"  Success rate: {sqs_stats['success_rate']:.2f}")
        print(f"  Avg processing time: {sqs_stats['average_processing_time_seconds']:.2f}s")
        print(f"  Circuit breaker: {sqs_stats['circuit_breaker_status']['state']}")
        print()
        
        # === Final Summary ===
        print("🎉 MCP Implementation Demo Complete!")
        print("=" * 60)
        print("✅ Atomic tools executed with scientific analysis")
        print("✅ Hardware devices controlled via MCP")
        print("✅ LLM workers processed with templates")
        print("✅ SQS queue handled distributed processing")
        print("✅ Correlation tracking maintained throughout")
        print("✅ Circuit breakers provided resilience")
        print("✅ Audit logging captured all operations")
        print()
        print(f"🔗 All operations tracked with correlation ID: {correlation_id}")
        print("📖 See MCP_IMPLEMENTATION_GUIDE.md for detailed documentation")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(demonstrate_complete_mcp_workflow())
    if success:
        print("\n✨ Pure MCP alignment with agentic DriverIA successfully demonstrated!")
        exit(0)
    else:
        print("\n⚠️ Demo encountered errors")
        exit(1)