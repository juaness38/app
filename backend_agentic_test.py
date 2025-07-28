#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASTROFLORA ANTARES - COMPREHENSIVE AGENTIC BACKEND TESTING
Testing the Phase 1 Agentic capabilities: Coexistence and Stabilization
"""
import asyncio
import json
import os
import sys
import time
from typing import Dict, Any, List
import httpx
import pytest
from datetime import datetime

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'src'))

class AstrofloraAgenticTester:
    """Comprehensive tester for Astroflora Antares Agentic capabilities - Phase 1"""
    
    def __init__(self):
        # Get backend URL from frontend env
        self.frontend_env_path = "/app/frontend/.env"
        self.backend_url = self._get_backend_url()
        self.api_key = "antares-super-secret-key-2024"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.test_results = {
            "agentic_endpoints": {"passed": 0, "failed": 0, "details": []},
            "atomic_tools": {"passed": 0, "failed": 0, "details": []},
            "tool_gateway": {"passed": 0, "failed": 0, "details": []},
            "templates": {"passed": 0, "failed": 0, "details": []},
            "pipeline_enhanced": {"passed": 0, "failed": 0, "details": []},
            "compatibility": {"passed": 0, "failed": 0, "details": []},
            "metrics": {"passed": 0, "failed": 0, "details": []}
        }
        
    def _get_backend_url(self) -> str:
        """Get backend URL from frontend .env file"""
        try:
            with open(self.frontend_env_path, 'r') as f:
                for line in f:
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        return line.split('=', 1)[1].strip()
            return "http://localhost:8001"
        except Exception as e:
            print(f"Warning: Could not read frontend .env: {e}")
            return "http://localhost:8001"
    
    def log_test(self, category: str, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        if passed:
            self.test_results[category]["passed"] += 1
            status = "✅ PASSED"
        else:
            self.test_results[category]["failed"] += 1
            status = "❌ FAILED"
        
        self.test_results[category]["details"].append({
            "test": test_name,
            "status": status,
            "details": details
        })
        print(f"{status}: {test_name} - {details}")

    # ============================================================================
    # AGENTIC ENDPOINTS TESTING
    # ============================================================================

    async def test_agentic_tools_available(self) -> bool:
        """Test GET /api/agentic/tools/available"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.backend_url}/api/agentic/tools/available")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and "data" in data:
                        tools = data["data"].get("atomic_tools", [])
                        expected_tools = ["blast_search", "uniprot_annotations", "sequence_features", "llm_analysis"]
                        
                        found_tools = [tool for tool in expected_tools if tool in tools]
                        if len(found_tools) == len(expected_tools):
                            self.log_test("agentic_endpoints", "Tools Available", True, 
                                        f"Found all {len(expected_tools)} atomic tools")
                            return True
                        else:
                            self.log_test("agentic_endpoints", "Tools Available", False, 
                                        f"Missing tools: {set(expected_tools) - set(found_tools)}")
                            return False
                    else:
                        self.log_test("agentic_endpoints", "Tools Available", False, 
                                    "Invalid response structure")
                        return False
                else:
                    self.log_test("agentic_endpoints", "Tools Available", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("agentic_endpoints", "Tools Available", False, str(e))
            return False

    async def test_agentic_tools_schemas(self) -> bool:
        """Test GET /api/agentic/tools/schemas/all"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.backend_url}/api/agentic/tools/schemas/all")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and "data" in data:
                        schemas = data["data"].get("tools_schemas", {})
                        expected_tools = ["blast_search", "uniprot_annotations", "sequence_features", "llm_analysis"]
                        
                        for tool in expected_tools:
                            if tool not in schemas:
                                self.log_test("agentic_endpoints", "Tools Schemas", False, 
                                            f"Missing schema for {tool}")
                                return False
                            
                            schema = schemas[tool]
                            required_fields = ["name", "description", "scientific_purpose", "parameters"]
                            for field in required_fields:
                                if field not in schema:
                                    self.log_test("agentic_endpoints", "Tools Schemas", False, 
                                                f"Missing {field} in {tool} schema")
                                    return False
                        
                        self.log_test("agentic_endpoints", "Tools Schemas", True, 
                                    f"All {len(expected_tools)} tool schemas valid")
                        return True
                    else:
                        self.log_test("agentic_endpoints", "Tools Schemas", False, 
                                    "Invalid response structure")
                        return False
                else:
                    self.log_test("agentic_endpoints", "Tools Schemas", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("agentic_endpoints", "Tools Schemas", False, str(e))
            return False

    async def test_agentic_tool_invocation(self) -> bool:
        """Test POST /api/agentic/tools/invoke"""
        test_cases = [
            {
                "tool_name": "blast_search",
                "parameters": {"sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"},
                "description": "BLAST search with protein sequence"
            },
            {
                "tool_name": "uniprot_annotations", 
                "parameters": {"protein_ids": ["P12345", "Q9Y6R7"]},
                "description": "UniProt annotations for protein IDs"
            },
            {
                "tool_name": "sequence_features",
                "parameters": {"sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG"},
                "description": "Sequence features calculation"
            },
            {
                "tool_name": "llm_analysis",
                "parameters": {"data": {"sequence": "test", "blast_results": {"hits": []}}},
                "description": "LLM analysis with test data"
            }
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.backend_url}/api/agentic/tools/invoke",
                        json=test_case
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "data" in data:
                            tool_result = data["data"]
                            if "tool_name" in tool_result and "success" in tool_result:
                                self.log_test("atomic_tools", f"Tool Invoke - {test_case['tool_name']}", True, 
                                            test_case["description"])
                            else:
                                self.log_test("atomic_tools", f"Tool Invoke - {test_case['tool_name']}", False, 
                                            "Invalid tool result structure")
                                all_passed = False
                        else:
                            self.log_test("atomic_tools", f"Tool Invoke - {test_case['tool_name']}", False, 
                                        "Missing data in response")
                            all_passed = False
                    else:
                        self.log_test("atomic_tools", f"Tool Invoke - {test_case['tool_name']}", False, 
                                    f"HTTP {response.status_code}")
                        all_passed = False
                        
            except Exception as e:
                self.log_test("atomic_tools", f"Tool Invoke - {test_case['tool_name']}", False, str(e))
                all_passed = False
        
        return all_passed

    async def test_agentic_tool_recommendation(self) -> bool:
        """Test POST /api/agentic/tools/recommend"""
        test_contexts = [
            {
                "context": {
                    "sequence_info": {"type": "protein", "length": 150},
                    "analysis_goal": "function_prediction"
                },
                "min_score": 0.5,
                "description": "Protein function prediction context"
            },
            {
                "context": {
                    "sequence_info": {"type": "dna", "length": 500},
                    "blast_results": {"hits": [{"identity": 85}]}
                },
                "min_score": 0.3,
                "description": "DNA sequence with BLAST results"
            }
        ]
        
        all_passed = True
        
        for test_context in test_contexts:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.backend_url}/api/agentic/tools/recommend",
                        json=test_context
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success") and "data" in data:
                            recommendations = data["data"].get("recommendations", [])
                            if isinstance(recommendations, list):
                                self.log_test("tool_gateway", f"Tool Recommendation - {test_context['description']}", True, 
                                            f"Got {len(recommendations)} recommendations")
                            else:
                                self.log_test("tool_gateway", f"Tool Recommendation - {test_context['description']}", False, 
                                            "Invalid recommendations format")
                                all_passed = False
                        else:
                            self.log_test("tool_gateway", f"Tool Recommendation - {test_context['description']}", False, 
                                        "Invalid response structure")
                            all_passed = False
                    else:
                        self.log_test("tool_gateway", f"Tool Recommendation - {test_context['description']}", False, 
                                    f"HTTP {response.status_code}")
                        all_passed = False
                        
            except Exception as e:
                self.log_test("tool_gateway", f"Tool Recommendation - {test_context['description']}", False, str(e))
                all_passed = False
        
        return all_passed

    async def test_agentic_templates(self) -> bool:
        """Test GET /api/agentic/templates/available"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.backend_url}/api/agentic/templates/available")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and "data" in data:
                        templates = data["data"].get("templates", {})
                        if len(templates) > 0:
                            # Check for expected template structure
                            for template_id, template in templates.items():
                                required_fields = ["name", "description", "protocol_type", "analysis_depth"]
                                for field in required_fields:
                                    if field not in template:
                                        self.log_test("templates", "Templates Available", False, 
                                                    f"Missing {field} in template {template_id}")
                                        return False
                            
                            self.log_test("templates", "Templates Available", True, 
                                        f"Found {len(templates)} valid templates")
                            return True
                        else:
                            self.log_test("templates", "Templates Available", False, 
                                        "No templates found")
                            return False
                    else:
                        self.log_test("templates", "Templates Available", False, 
                                    "Invalid response structure")
                        return False
                else:
                    self.log_test("templates", "Templates Available", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("templates", "Templates Available", False, str(e))
            return False

    async def test_agentic_capabilities(self) -> bool:
        """Test GET /api/agentic/capabilities"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.backend_url}/api/agentic/capabilities")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and "data" in data:
                        capabilities = data["data"]
                        required_sections = ["system_info", "tool_gateway", "pipeline_status"]
                        
                        for section in required_sections:
                            if section not in capabilities:
                                self.log_test("agentic_endpoints", "Capabilities", False, 
                                            f"Missing {section} in capabilities")
                                return False
                        
                        # Check system info
                        system_info = capabilities["system_info"]
                        if system_info.get("phase") != "Fase 1: Coexistencia y Estabilización":
                            self.log_test("agentic_endpoints", "Capabilities", False, 
                                        "Incorrect phase information")
                            return False
                        
                        self.log_test("agentic_endpoints", "Capabilities", True, 
                                    f"Phase: {system_info.get('phase')}")
                        return True
                    else:
                        self.log_test("agentic_endpoints", "Capabilities", False, 
                                    "Invalid response structure")
                        return False
                else:
                    self.log_test("agentic_endpoints", "Capabilities", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("agentic_endpoints", "Capabilities", False, str(e))
            return False

    async def test_agentic_gateway_metrics(self) -> bool:
        """Test GET /api/agentic/metrics/gateway"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.backend_url}/api/agentic/metrics/gateway")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and "data" in data:
                        metrics = data["data"]
                        required_sections = ["gateway_info", "usage_metrics", "tool_performance"]
                        
                        for section in required_sections:
                            if section not in metrics:
                                self.log_test("metrics", "Gateway Metrics", False, 
                                            f"Missing {section} in metrics")
                                return False
                        
                        # Check gateway info
                        gateway_info = metrics["gateway_info"]
                        if gateway_info.get("phase") != "Fase 1: Coexistencia y Estabilización":
                            self.log_test("metrics", "Gateway Metrics", False, 
                                        "Incorrect phase in gateway info")
                            return False
                        
                        self.log_test("metrics", "Gateway Metrics", True, 
                                    f"Gateway has {gateway_info.get('total_atomic_tools', 0)} atomic tools")
                        return True
                    else:
                        self.log_test("metrics", "Gateway Metrics", False, 
                                    "Invalid response structure")
                        return False
                else:
                    self.log_test("metrics", "Gateway Metrics", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("metrics", "Gateway Metrics", False, str(e))
            return False

    async def test_pipeline_config_validation(self) -> bool:
        """Test POST /api/agentic/config/validate"""
        test_config = {
            "blast_database": "nr",
            "evalue_threshold": 1e-10,
            "max_target_seqs": 100,
            "uniprot_fields": ["function", "pathway", "domain"],
            "llm_analysis_depth": "detailed",
            "llm_max_tokens": 1500,
            "llm_temperature": 0.3,
            "max_concurrent_sequences": 5,
            "enable_caching": True
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.backend_url}/api/agentic/config/validate",
                    json=test_config
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and "data" in data:
                        validation_data = data["data"]
                        required_fields = ["config", "validation_status", "estimated_cost_tier"]
                        
                        for field in required_fields:
                            if field not in validation_data:
                                self.log_test("pipeline_enhanced", "Config Validation", False, 
                                            f"Missing {field} in validation response")
                                return False
                        
                        if validation_data["validation_status"] == "valid":
                            self.log_test("pipeline_enhanced", "Config Validation", True, 
                                        f"Config valid, cost tier: {validation_data['estimated_cost_tier']}")
                            return True
                        else:
                            self.log_test("pipeline_enhanced", "Config Validation", False, 
                                        "Config validation failed")
                            return False
                    else:
                        self.log_test("pipeline_enhanced", "Config Validation", False, 
                                    "Invalid response structure")
                        return False
                else:
                    self.log_test("pipeline_enhanced", "Config Validation", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("pipeline_enhanced", "Config Validation", False, str(e))
            return False

    # ============================================================================
    # COMPATIBILITY TESTING
    # ============================================================================

    async def test_existing_analysis_endpoints(self) -> bool:
        """Test that existing analysis endpoints still work"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test existing analysis endpoint
                response = await client.get(
                    f"{self.backend_url}/api/analysis/",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    self.log_test("compatibility", "Existing Analysis Endpoints", True, 
                                "Analysis endpoint still functional")
                    return True
                else:
                    self.log_test("compatibility", "Existing Analysis Endpoints", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("compatibility", "Existing Analysis Endpoints", False, str(e))
            return False

    async def test_health_endpoints_compatibility(self) -> bool:
        """Test that health endpoints still work"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.backend_url}/api/health/")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        self.log_test("compatibility", "Health Endpoints", True, 
                                    "Health endpoints still functional")
                        return True
                    else:
                        self.log_test("compatibility", "Health Endpoints", False, 
                                    "Health endpoint response invalid")
                        return False
                else:
                    self.log_test("compatibility", "Health Endpoints", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("compatibility", "Health Endpoints", False, str(e))
            return False

    # ============================================================================
    # TEST RUNNER
    # ============================================================================

    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🤖 ASTROFLORA ANTARES - AGENTIC CAPABILITIES TEST RESULTS (PHASE 1)")
        print("="*80)
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.test_results.items():
            passed = results["passed"]
            failed = results["failed"]
            total_passed += passed
            total_failed += failed
            
            status_icon = "✅" if failed == 0 else "❌"
            print(f"\n{status_icon} {category.upper().replace('_', ' ')}: {passed} passed, {failed} failed")
            
            for detail in results["details"]:
                print(f"  {detail['status']}: {detail['test']}")
                if detail['details']:
                    print(f"    └─ {detail['details']}")
        
        print("\n" + "="*80)
        overall_status = "✅ ALL AGENTIC TESTS PASSED" if total_failed == 0 else f"❌ {total_failed} AGENTIC TESTS FAILED"
        print(f"OVERALL RESULT: {overall_status} ({total_passed} passed, {total_failed} failed)")
        print("🚀 PHASE 1: Coexistencia y Estabilización - Testing Complete")
        print("="*80)
        
        return total_failed == 0

    async def run_agentic_tests(self):
        """Run all agentic capability tests"""
        print("🤖 Starting Astroflora Antares Agentic Capabilities Testing...")
        print("🚀 PHASE 1: Coexistencia y Estabilización")
        print(f"Backend URL: {self.backend_url}")
        print(f"API Key: {self.api_key[:20]}...")
        print("-" * 80)
        
        # Test 1: Agentic Endpoints
        print("\n🔧 Testing Agentic Endpoints...")
        await self.test_agentic_tools_available()
        await self.test_agentic_tools_schemas()
        await self.test_agentic_templates()
        await self.test_agentic_capabilities()
        
        # Test 2: Atomic Tools
        print("\n⚛️  Testing Atomic Tools...")
        await self.test_agentic_tool_invocation()
        
        # Test 3: Tool Gateway
        print("\n🌐 Testing Tool Gateway...")
        await self.test_agentic_tool_recommendation()
        await self.test_agentic_gateway_metrics()
        
        # Test 4: Enhanced Pipeline
        print("\n🔬 Testing Enhanced Pipeline...")
        await self.test_pipeline_config_validation()
        
        # Test 5: Compatibility
        print("\n🔄 Testing Backward Compatibility...")
        await self.test_existing_analysis_endpoints()
        await self.test_health_endpoints_compatibility()
        
        # Print final summary
        return self.print_summary()

async def main():
    """Main test runner"""
    tester = AstrofloraAgenticTester()
    success = await tester.run_agentic_tests()
    
    if success:
        print("\n🎉 All agentic tests passed! Phase 1 implementation is working correctly.")
        return 0
    else:
        print("\n⚠️  Some agentic tests failed. Please check the details above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)