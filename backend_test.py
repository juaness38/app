#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASTROFLORA ANTARES - COMPREHENSIVE BACKEND TESTING
Testing the complete Antares cognitive system implementation
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

class AntaresBackendTester:
    """Comprehensive tester for Astroflora Antares backend system"""
    
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
            "architecture": {"passed": 0, "failed": 0, "details": []},
            "api_endpoints": {"passed": 0, "failed": 0, "details": []},
            "driver_ia": {"passed": 0, "failed": 0, "details": []},
            "tools": {"passed": 0, "failed": 0, "details": []},
            "protocols": {"passed": 0, "failed": 0, "details": []},
            "resilience": {"passed": 0, "failed": 0, "details": []},
            "observability": {"passed": 0, "failed": 0, "details": []},
            "full_flow": {"passed": 0, "failed": 0, "details": []}
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
    
    async def test_basic_connectivity(self) -> bool:
        """Test basic connectivity to backend"""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                # Test the health endpoint instead of root since root returns frontend
                response = await client.get(f"{self.backend_url}/api/health/")
                
                if response.status_code == 200:
                    data = response.json()
                    self.log_test("architecture", "Basic Connectivity", True, 
                                f"Backend responding: {data.get('status', 'OK')}")
                    return True
                else:
                    self.log_test("architecture", "Basic Connectivity", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("architecture", "Basic Connectivity", False, str(e))
            return False
    
    async def test_system_info(self) -> bool:
        """Test system info endpoint"""
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                # Use the health detailed endpoint since /info is not available at API level
                response = await client.get(f"{self.backend_url}/api/health/detailed")
                
                if response.status_code == 200:
                    data = response.json()
                    required_fields = ["health", "system_info"]
                    
                    for field in required_fields:
                        if field not in data:
                            self.log_test("architecture", "System Info", False, 
                                        f"Missing field: {field}")
                            return False
                    
                    system_info = data.get("system_info", {})
                    version = system_info.get("version", "unknown")
                    environment = system_info.get("environment", "unknown")
                    
                    self.log_test("architecture", "System Info", True, 
                                f"Version: {version}, Env: {environment}")
                    return True
                else:
                    self.log_test("architecture", "System Info", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("architecture", "System Info", False, str(e))
            return False
    
    async def test_health_endpoints(self) -> bool:
        """Test health check endpoints"""
        health_endpoints = [
            ("/api/health", "Basic Health Check"),
            ("/api/health/detailed", "Detailed Health Check"),
            ("/api/health/metrics", "Prometheus Metrics"),
            ("/api/health/capacity", "System Capacity"),
            ("/api/health/queue", "Queue Status")
        ]
        
        all_passed = True
        
        for endpoint, test_name in health_endpoints:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(f"{self.backend_url}{endpoint}")
                    
                    if response.status_code == 200:
                        if endpoint == "/api/health/metrics":
                            # Metrics should return text/plain
                            self.log_test("observability", test_name, True, 
                                        "Prometheus metrics available")
                        else:
                            data = response.json()
                            self.log_test("observability", test_name, True, 
                                        f"Status: {data.get('status', 'OK')}")
                    else:
                        self.log_test("observability", test_name, False, 
                                    f"HTTP {response.status_code}")
                        all_passed = False
                        
            except Exception as e:
                self.log_test("observability", test_name, False, str(e))
                all_passed = False
        
        return all_passed
    
    async def test_protocol_types(self) -> bool:
        """Test protocol types endpoint"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.backend_url}/api/analysis/protocols/types",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    protocols = response.json()
                    expected_protocols = [
                        "PROTEIN_FUNCTION_ANALYSIS",
                        "SEQUENCE_ALIGNMENT", 
                        "STRUCTURE_PREDICTION",
                        "DRUG_DESIGN",
                        "BIOREACTOR_OPTIMIZATION"
                    ]
                    
                    for protocol in expected_protocols:
                        if protocol not in protocols:
                            self.log_test("protocols", "Protocol Types", False, 
                                        f"Missing protocol: {protocol}")
                            return False
                    
                    self.log_test("protocols", "Protocol Types", True, 
                                f"Found {len(protocols)} protocols")
                    return True
                else:
                    self.log_test("protocols", "Protocol Types", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("protocols", "Protocol Types", False, str(e))
            return False
    
    async def test_available_tools(self) -> bool:
        """Test available tools endpoint"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.backend_url}/api/analysis/tools/available",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    tools = response.json()
                    expected_tools = [
                        "blast", "alphafold", "mafft", "muscle", "swiss_model",
                        "swiss_dock", "pymol", "chimera", "rosetta", "gromacs",
                        "amber", "vmd", "bioreactor_sim"
                    ]
                    
                    found_tools = 0
                    for tool in expected_tools:
                        if tool in tools:
                            found_tools += 1
                    
                    if found_tools >= 10:  # At least 10 of 13 tools should be available
                        self.log_test("tools", "Available Tools", True, 
                                    f"Found {found_tools}/{len(expected_tools)} tools")
                        return True
                    else:
                        self.log_test("tools", "Available Tools", False, 
                                    f"Only found {found_tools}/{len(expected_tools)} tools")
                        return False
                else:
                    self.log_test("tools", "Available Tools", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("tools", "Available Tools", False, str(e))
            return False
    
    async def test_tool_health_checks(self) -> bool:
        """Test individual tool health checks"""
        test_tools = ["blast", "alphafold", "mafft"]
        all_passed = True
        
        for tool in test_tools:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{self.backend_url}/api/analysis/tools/{tool}/health",
                        headers=self.headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        tool_name = data.get("tool_name")
                        healthy = data.get("healthy")
                        
                        if tool_name == tool:
                            self.log_test("tools", f"Tool Health - {tool}", True, 
                                        f"Status: {'healthy' if healthy else 'unhealthy'}")
                        else:
                            self.log_test("tools", f"Tool Health - {tool}", False, 
                                        "Tool name mismatch")
                            all_passed = False
                    else:
                        self.log_test("tools", f"Tool Health - {tool}", False, 
                                    f"HTTP {response.status_code}")
                        all_passed = False
                        
            except Exception as e:
                self.log_test("tools", f"Tool Health - {tool}", False, str(e))
                all_passed = False
        
        return all_passed
    
    async def test_analysis_creation(self) -> Dict[str, Any]:
        """Test creating a new analysis"""
        analysis_request = {
            "workspace_id": "test_workspace_001",
            "protocol_type": "PROTEIN_FUNCTION_ANALYSIS",
            "sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
            "target_protein": "Unknown protein",
            "parameters": {
                "analysis_depth": "comprehensive",
                "include_structure": True
            },
            "priority": 1
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.backend_url}/api/analysis/",
                    headers=self.headers,
                    json=analysis_request
                )
                
                if response.status_code == 202:  # Accepted
                    data = response.json()
                    required_fields = ["context_id", "status", "workspace_id", "protocol_type"]
                    
                    for field in required_fields:
                        if field not in data:
                            self.log_test("full_flow", "Analysis Creation", False, 
                                        f"Missing field: {field}")
                            return None
                    
                    self.log_test("full_flow", "Analysis Creation", True, 
                                f"Analysis created: {data['context_id']}")
                    return data
                else:
                    self.log_test("full_flow", "Analysis Creation", False, 
                                f"HTTP {response.status_code}: {response.text}")
                    return None
                    
        except Exception as e:
            self.log_test("full_flow", "Analysis Creation", False, str(e))
            return None
    
    async def test_analysis_status(self, context_id: str) -> bool:
        """Test getting analysis status"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.backend_url}/api/analysis/{context_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    progress = data.get("progress", 0)
                    
                    self.log_test("full_flow", "Analysis Status", True, 
                                f"Status: {status}, Progress: {progress}%")
                    return True
                elif response.status_code == 404:
                    self.log_test("full_flow", "Analysis Status", False, 
                                "Analysis not found")
                    return False
                else:
                    self.log_test("full_flow", "Analysis Status", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("full_flow", "Analysis Status", False, str(e))
            return False
    
    async def test_user_analyses(self) -> bool:
        """Test getting user analyses"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.backend_url}/api/analysis/",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    analyses = response.json()
                    self.log_test("api_endpoints", "User Analyses", True, 
                                f"Found {len(analyses)} analyses")
                    return True
                else:
                    self.log_test("api_endpoints", "User Analyses", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("api_endpoints", "User Analyses", False, str(e))
            return False
    
    async def test_batch_analysis(self) -> bool:
        """Test batch analysis creation"""
        batch_requests = [
            {
                "workspace_id": "test_workspace_batch_1",
                "protocol_type": "SEQUENCE_ALIGNMENT",
                "sequence": "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLAGG",
                "priority": 2
            },
            {
                "workspace_id": "test_workspace_batch_2", 
                "protocol_type": "STRUCTURE_PREDICTION",
                "sequence": "ATGAAACGTCAAGAACGTCTGAAATCGATCGTCCGTATTCTGGAACGTGAATCGAAAGAACCG",
                "priority": 3
            }
        ]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.backend_url}/api/analysis/batch",
                    headers=self.headers,
                    json=batch_requests
                )
                
                if response.status_code == 202:
                    analyses = response.json()
                    if len(analyses) == 2:
                        self.log_test("api_endpoints", "Batch Analysis", True, 
                                    f"Created {len(analyses)} batch analyses")
                        return True
                    else:
                        self.log_test("api_endpoints", "Batch Analysis", False, 
                                    f"Expected 2 analyses, got {len(analyses)}")
                        return False
                else:
                    self.log_test("api_endpoints", "Batch Analysis", False, 
                                f"HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            self.log_test("api_endpoints", "Batch Analysis", False, str(e))
            return False
    
    async def test_maintenance_endpoints(self) -> bool:
        """Test maintenance endpoints"""
        maintenance_endpoints = [
            ("/api/health/maintenance/cleanup", "Resource Cleanup"),
            ("/api/health/maintenance/reset-capacity", "Capacity Reset")
        ]
        
        all_passed = True
        
        for endpoint, test_name in maintenance_endpoints:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(f"{self.backend_url}{endpoint}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.log_test("resilience", test_name, True, 
                                    data.get("message", "Success"))
                    else:
                        self.log_test("resilience", test_name, False, 
                                    f"HTTP {response.status_code}")
                        all_passed = False
                        
            except Exception as e:
                self.log_test("resilience", test_name, False, str(e))
                all_passed = False
        
        return all_passed
    
    async def test_authentication(self) -> bool:
        """Test API authentication"""
        # Test without API key
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.backend_url}/api/analysis/protocols/types")
                
                if response.status_code == 401:
                    self.log_test("api_endpoints", "Authentication - No Key", True, 
                                "Correctly rejected request without API key")
                else:
                    self.log_test("api_endpoints", "Authentication - No Key", False, 
                                f"Expected 401, got {response.status_code}")
                    return False
        except Exception as e:
            self.log_test("api_endpoints", "Authentication - No Key", False, str(e))
            return False
        
        # Test with wrong API key
        try:
            wrong_headers = {"X-API-Key": "wrong-key", "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.backend_url}/api/analysis/protocols/types",
                    headers=wrong_headers
                )
                
                if response.status_code == 401:
                    self.log_test("api_endpoints", "Authentication - Wrong Key", True, 
                                "Correctly rejected request with wrong API key")
                    return True
                else:
                    self.log_test("api_endpoints", "Authentication - Wrong Key", False, 
                                f"Expected 401, got {response.status_code}")
                    return False
        except Exception as e:
            self.log_test("api_endpoints", "Authentication - Wrong Key", False, str(e))
            return False
    
    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🧬 ASTROFLORA ANTARES - COMPREHENSIVE BACKEND TEST RESULTS")
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
        overall_status = "✅ ALL TESTS PASSED" if total_failed == 0 else f"❌ {total_failed} TESTS FAILED"
        print(f"OVERALL RESULT: {overall_status} ({total_passed} passed, {total_failed} failed)")
        print("="*80)
        
        return total_failed == 0
    
    async def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        print("🚀 Starting Astroflora Antares Backend Comprehensive Testing...")
        print(f"Backend URL: {self.backend_url}")
        print(f"API Key: {self.api_key[:20]}...")
        print("-" * 80)
        
        # Test 1: Basic Architecture
        print("\n🏗️  Testing Basic Architecture...")
        await self.test_basic_connectivity()
        await self.test_system_info()
        
        # Test 2: Health & Observability
        print("\n🏥 Testing Health & Observability...")
        await self.test_health_endpoints()
        
        # Test 3: Authentication
        print("\n🔐 Testing Authentication...")
        await self.test_authentication()
        
        # Test 4: Protocol Types
        print("\n🧪 Testing Protocol Types...")
        await self.test_protocol_types()
        
        # Test 5: Bioinformatics Tools
        print("\n🔬 Testing Bioinformatics Tools...")
        await self.test_available_tools()
        await self.test_tool_health_checks()
        
        # Test 6: API Endpoints
        print("\n🌐 Testing API Endpoints...")
        await self.test_user_analyses()
        await self.test_batch_analysis()
        
        # Test 7: Full Analysis Flow
        print("\n🔄 Testing Full Analysis Flow...")
        analysis_context = await self.test_analysis_creation()
        if analysis_context:
            await self.test_analysis_status(analysis_context["context_id"])
        
        # Test 8: Resilience & Maintenance
        print("\n🛡️  Testing Resilience & Maintenance...")
        await self.test_maintenance_endpoints()
        
        # Print final summary
        return self.print_summary()

async def main():
    """Main test runner"""
    tester = AntaresBackendTester()
    success = await tester.run_comprehensive_tests()
    
    if success:
        print("\n🎉 All tests passed! Astroflora Antares backend is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the details above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)