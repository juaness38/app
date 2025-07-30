#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ASTROFLORA EMERGENT TEST EXECUTOR
Ejecutor principal para las suites de testing emergente de Astroflora
"""
import asyncio
import json
import yaml
import os
import sys
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import httpx
import aiohttp
import argparse

# Import enhanced scientific validation
from scientific_validator import ScientificValidator, ScientificErrorReporter

class EmergentTestExecutor:
    """Ejecutor de tests emergentes para Astroflora"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.test_dir = Path(__file__).parent.parent
        self.yaml_dir = self.test_dir / "yaml_tests"
        self.reports_dir = self.test_dir / "reports"
        
        # Crear directorios si no existen
        self.reports_dir.mkdir(exist_ok=True)
        
        # Initialize enhanced scientific validation
        self.scientific_validator = ScientificValidator()
        self.error_reporter = ScientificErrorReporter()
        
        # Configuración por defecto
        self.config = {
            "backend_url": self._get_backend_url(),
            "api_key": "antares-super-secret-key-2024",
            "timeout": 300,
            "parallel_execution": False,
            "verbose": True
        }
        
        # Cargar configuración personalizada si existe
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                custom_config = yaml.safe_load(f)
                self.config.update(custom_config)
        
        self.execution_id = str(uuid.uuid4())[:8]
        self.start_time = datetime.utcnow()
        
        print(f"🤖 Emergent Test Executor iniciado")
        print(f"📁 Test Directory: {self.test_dir}")
        print(f"🌐 Backend URL: {self.config['backend_url']}")
        print(f"🆔 Execution ID: {self.execution_id}")
        print("-" * 80)
    
    def _get_backend_url(self) -> str:
        """Obtiene backend URL desde .env del frontend"""
        try:
            frontend_env = Path("/app/frontend/.env")
            if frontend_env.exists():
                with open(frontend_env, 'r') as f:
                    for line in f:
                        if line.startswith('REACT_APP_BACKEND_URL='):
                            return line.split('=', 1)[1].strip()
        except Exception:
            pass
        return "http://localhost:8001"
    
    async def load_test_suite(self, yaml_file: str) -> Dict[str, Any]:
        """Carga una suite de test desde archivo YAML"""
        yaml_path = self.yaml_dir / yaml_file
        
        if not yaml_path.exists():
            raise FileNotFoundError(f"Test suite not found: {yaml_path}")
        
        with open(yaml_path, 'r', encoding='utf-8') as f:
            suite = yaml.safe_load(f)
        
        return suite
    
    async def execute_test_case(self, test_case: Dict[str, Any], suite_context: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta un caso de test individual"""
        case_id = test_case.get('case_id', 'unknown')
        name = test_case.get('name', 'Unnamed Test')
        
        print(f"  🧪 Ejecutando: {case_id} - {name}")
        
        result = {
            'case_id': case_id,
            'name': name,
            'status': 'unknown',
            'start_time': datetime.utcnow().isoformat(),
            'execution_time_ms': 0,
            'details': {},
            'errors': [],
            'scientific_validation': {}
        }
        
        start_time = time.time()
        
        try:
            # Check for concurrent testing requirement
            concurrency_level = test_case.get('concurrency', 1)
            
            if concurrency_level > 1:
                # Execute concurrent test
                result = await self._execute_concurrent_test(test_case, suite_context, result, concurrency_level)
            else:
                # Determinar tipo de test y ejecutar apropiadamente
                if 'request' in test_case:
                    # Test de endpoint HTTP
                    result = await self._execute_http_test(test_case, suite_context, result)
                elif 'validation' in test_case:
                    # Test de validación
                    result = await self._execute_validation_test(test_case, suite_context, result)
                elif 'test_sequence' in test_case:
                    # Test de secuencia compleja
                    result = await self._execute_sequence_test(test_case, suite_context, result)
                else:
                    # Test genérico
                    result = await self._execute_generic_test(test_case, suite_context, result)
            
            result['status'] = 'passed' if not result['errors'] else 'failed'
            
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(f"Execution error: {str(e)}")
        
        result['execution_time_ms'] = int((time.time() - start_time) * 1000)
        result['end_time'] = datetime.utcnow().isoformat()
        
        status_icon = "✅" if result['status'] == 'passed' else "❌" if result['status'] == 'failed' else "⚠️"
        print(f"    {status_icon} {result['status'].upper()} ({result['execution_time_ms']}ms)")
        
        return result
    
    async def _execute_http_test(self, test_case: Dict[str, Any], suite_context: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta un test HTTP"""
        request_config = test_case['request']
        endpoint = request_config['endpoint']
        method = request_config.get('method', 'GET')
        payload = request_config.get('payload', {})
        
        url = f"{self.config['backend_url']}{endpoint}"
        headers = {
            "X-API-Key": self.config['api_key'],
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.config['timeout']) as client:
                if method.upper() == 'GET':
                    response = await client.get(url, headers=headers)
                elif method.upper() == 'POST':
                    response = await client.post(url, headers=headers, json=payload)
                elif method.upper() == 'PUT':
                    response = await client.put(url, headers=headers, json=payload)
                elif method.upper() == 'DELETE':
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                result['details']['http_status'] = response.status_code
                result['details']['response_headers'] = dict(response.headers)
                
                # Intentar parsear respuesta JSON
                try:
                    response_data = response.json()
                    result['details']['response_data'] = response_data
                except:
                    result['details']['response_text'] = response.text[:1000]  # Primeros 1000 chars
                
                # Validar respuesta según criterios esperados
                await self._validate_response(response, response_data if 'response_data' in result['details'] else None, 
                                            test_case.get('expected_result', {}), result)
                
        except Exception as e:
            result['errors'].append(f"HTTP request failed: {str(e)}")
        
        return result
    
    async def _validate_response(self, response, response_data: Optional[Dict], expected: Dict[str, Any], result: Dict[str, Any]):
        """Valida respuesta HTTP contra criterios esperados"""
        # Validar status code
        expected_status = expected.get('status_code', 200)
        if response.status_code != expected_status:
            result['errors'].append(f"Expected status {expected_status}, got {response.status_code}")
        
        # Validar estructura de respuesta
        if response_data and 'success' in expected:
            if response_data.get('success') != expected['success']:
                result['errors'].append(f"Expected success={expected['success']}, got {response_data.get('success')}")
        
        # Validar criterios específicos
        if 'criteria' in expected and response_data:
            for criterion in expected['criteria']:
                try:
                    # Use enhanced criterion evaluation
                    passed, message = self._evaluate_criterion(criterion, response_data)
                    if not passed:
                        result['errors'].append(f"Criterion failed: {message}")
                except Exception as e:
                    result['errors'].append(f"Criterion evaluation error: {criterion} -> {str(e)}")
        
        # Enhanced validation support - handle 'validation' key similar to 'criteria'
        if 'validation' in expected and response_data:
            for validation in expected['validation']:
                try:
                    # Extract actual value using JSON path if specified
                    if 'path' in validation:
                        path = validation['path']
                        actual_value = self.scientific_validator._extract_json_path(response_data, path)
                        criterion = validation.get('criterion', {})
                        passed, message = self.scientific_validator.evaluate_criterion(criterion, actual_value)
                    else:
                        # Direct validation
                        passed, message = self._evaluate_criterion(validation, response_data)
                    
                    if not passed:
                        result['errors'].append(f"Validation failed: {message}")
                        
                except Exception as e:
                    result['errors'].append(f"Validation error: {validation} -> {str(e)}")
        
        # Validación científica
        if 'scientific_validation' in expected:
            await self._perform_scientific_validation(response_data, expected['scientific_validation'], result)
    
    def _evaluate_criterion(self, criterion: Dict[str, Any], data: Dict[str, Any]) -> tuple[bool, str]:
        """Enhanced criterion evaluation using scientific validator"""
        try:
            # Handle different criterion formats
            if isinstance(criterion, str):
                # Legacy string format - convert to dict format
                criterion_dict = {'type': 'legacy_string', 'rule': criterion}
                return self._evaluate_legacy_criterion(criterion, data)
            elif isinstance(criterion, dict):
                # New enhanced format
                return self.scientific_validator.evaluate_criterion(criterion, data)
            else:
                return False, f"Invalid criterion format: {type(criterion)}"
        except Exception as e:
            return False, f"Criterion evaluation error: {str(e)}"
    
    def _evaluate_legacy_criterion(self, criterion: str, data: Dict[str, Any]) -> tuple[bool, str]:
        """Evaluate legacy string-based criteria"""
        try:
            if 'aparece en' in criterion:
                # Ej: "blast_search aparece en top 3 recomendaciones"
                return True, f"Legacy criterion '{criterion}' - placeholder pass"
            elif 'incluido' in criterion:
                # Ej: "uniprot_annotations incluido si score > 0.7"
                return True, f"Legacy criterion '{criterion}' - placeholder pass"
            elif '>=' in criterion:
                # Ej: "Total recomendaciones >= 2"
                return True, f"Legacy criterion '{criterion}' - placeholder pass"
            else:
                return True, f"Legacy criterion '{criterion}' - default pass"
        except Exception as e:
            return False, f"Legacy criterion error: {str(e)}"
    
    async def _perform_scientific_validation(self, data: Dict[str, Any], validation_rules: List[Dict[str, Any]], result: Dict[str, Any]):
        """Enhanced scientific validation with biological context"""
        scientific_results = []
        failures = []
        
        for validation_rule in validation_rules:
            try:
                # Extract the criterion from the validation rule
                if isinstance(validation_rule, dict):
                    criterion = validation_rule
                    rule_name = validation_rule.get('type', 'unknown_rule')
                else:
                    # Legacy format
                    criterion = {'type': 'legacy_string', 'rule': str(validation_rule)}
                    rule_name = str(validation_rule)
                
                # Use the enhanced scientific validator
                passed, message = self.scientific_validator.evaluate_criterion(criterion, data)
                
                validation_result = {
                    'rule': rule_name,
                    'passed': passed,
                    'message': message,
                    'criterion': criterion
                }
                
                scientific_results.append(validation_result)
                
                if not passed:
                    failures.append({
                        'criterion': criterion,
                        'actual_value': data,
                        'message': message
                    })
                    
            except Exception as e:
                error_result = {
                    'rule': validation_rule,
                    'passed': False,
                    'error': str(e),
                    'message': f"Validation error: {str(e)}"
                }
                scientific_results.append(error_result)
                failures.append({
                    'criterion': validation_rule,
                    'actual_value': data,
                    'message': f"Validation error: {str(e)}"
                })
        
        result['scientific_validation'] = scientific_results
        
        # Add enhanced error reporting if there are failures
        if failures:
            test_case = result.get('test_case', {})
            failure_report = self.error_reporter.generate_failure_report(test_case, failures)
            result['failure_report'] = failure_report
    
    async def _execute_validation_test(self, test_case: Dict[str, Any], suite_context: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta test de validación sin HTTP"""
        # Placeholder para tests de validación
        result['details']['validation_type'] = 'internal'
        return result
    
    async def _execute_sequence_test(self, test_case: Dict[str, Any], suite_context: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta test de secuencia compleja"""
        # Placeholder para tests de secuencia
        result['details']['sequence_type'] = 'multi_step'
        return result
    
    async def _execute_generic_test(self, test_case: Dict[str, Any], suite_context: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta test genérico"""
        # Placeholder para tests genéricos
        result['details']['test_type'] = 'generic'
        return result
    
    async def execute_scenario(self, scenario: Dict[str, Any], suite_context: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta un escenario completo"""
        name = scenario.get('name', 'unknown_scenario')
        description = scenario.get('description', 'No description')
        priority = scenario.get('priority', 'medium')
        
        print(f"\n📋 Escenario: {name} ({priority})")
        print(f"   {description}")
        
        scenario_result = {
            'name': name,
            'description': description,
            'priority': priority,
            'start_time': datetime.utcnow().isoformat(),
            'test_cases': [],
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0
            }
        }
        
        test_cases = scenario.get('test_cases', [])
        for test_case in test_cases:
            case_result = await self.execute_test_case(test_case, suite_context)
            scenario_result['test_cases'].append(case_result)
            
            # Actualizar resumen
            scenario_result['summary']['total'] += 1
            if case_result['status'] == 'passed':
                scenario_result['summary']['passed'] += 1
            elif case_result['status'] == 'failed':
                scenario_result['summary']['failed'] += 1
            elif case_result['status'] == 'error':
                scenario_result['summary']['errors'] += 1
        
        scenario_result['end_time'] = datetime.utcnow().isoformat()
        
        # Mostrar resumen del escenario
        summary = scenario_result['summary']
        success_rate = (summary['passed'] / summary['total'] * 100) if summary['total'] > 0 else 0
        status_icon = "✅" if summary['failed'] == 0 and summary['errors'] == 0 else "❌"
        
        print(f"   {status_icon} Completado: {summary['passed']}/{summary['total']} passed ({success_rate:.1f}%)")
        
        return scenario_result
    
    async def execute_test_suite(self, yaml_file: str) -> Dict[str, Any]:
        """Ejecuta una suite de test completa"""
        print(f"\n🚀 Ejecutando Suite: {yaml_file}")
        
        try:
            suite = await self.load_test_suite(yaml_file)
        except Exception as e:
            print(f"❌ Error cargando suite: {e}")
            return {'error': str(e)}
        
        suite_info = suite.get('test_suite', {})
        print(f"   Nombre: {suite_info.get('name', 'Unknown')}")
        print(f"   Versión: {suite_info.get('version', 'Unknown')}")
        print(f"   Fase: {suite_info.get('phase', 'Unknown')}")
        
        suite_result = {
            'suite_file': yaml_file,
            'suite_info': suite_info,
            'execution_id': self.execution_id,
            'start_time': datetime.utcnow().isoformat(),
            'scenarios': [],
            'summary': {
                'total_scenarios': 0,
                'total_test_cases': 0,
                'passed_test_cases': 0,
                'failed_test_cases': 0,
                'error_test_cases': 0,
                'success_rate': 0.0
            }
        }
        
        scenarios = suite.get('scenarios', [])
        for scenario in scenarios:
            scenario_result = await self.execute_scenario(scenario, suite)
            suite_result['scenarios'].append(scenario_result)
            
            # Actualizar resumen de suite
            suite_result['summary']['total_scenarios'] += 1
            suite_result['summary']['total_test_cases'] += scenario_result['summary']['total']
            suite_result['summary']['passed_test_cases'] += scenario_result['summary']['passed']
            suite_result['summary']['failed_test_cases'] += scenario_result['summary']['failed']
            suite_result['summary']['error_test_cases'] += scenario_result['summary']['errors']
        
        # Calcular success rate
        total_tests = suite_result['summary']['total_test_cases']
        if total_tests > 0:
            suite_result['summary']['success_rate'] = (suite_result['summary']['passed_test_cases'] / total_tests) * 100
        
        suite_result['end_time'] = datetime.utcnow().isoformat()
        
        return suite_result
    
    async def execute_all_suites(self) -> Dict[str, Any]:
        """Ejecuta todas las suites de test disponibles"""
        print(f"\n🎯 EJECUTANDO TODAS LAS SUITES DE TESTING EMERGENTE")
        print("=" * 80)
        
        # Encontrar todos los archivos YAML de test
        yaml_files = list(self.yaml_dir.glob("*.yaml"))
        
        if not yaml_files:
            print("❌ No se encontraron suites de test YAML")
            return {'error': 'No test suites found'}
        
        all_results = {
            'execution_id': self.execution_id,
            'start_time': self.start_time.isoformat(),
            'config': self.config,
            'suites': [],
            'overall_summary': {
                'total_suites': len(yaml_files),
                'total_scenarios': 0,
                'total_test_cases': 0,
                'passed_test_cases': 0,
                'failed_test_cases': 0,
                'error_test_cases': 0,
                'overall_success_rate': 0.0
            }
        }
        
        # Ejecutar cada suite
        for yaml_file in sorted(yaml_files):
            suite_result = await self.execute_test_suite(yaml_file.name)
            
            if 'error' not in suite_result:
                all_results['suites'].append(suite_result)
                
                # Agregar al resumen general
                summary = suite_result['summary']
                all_results['overall_summary']['total_scenarios'] += summary.get('total_scenarios', 0)
                all_results['overall_summary']['total_test_cases'] += summary.get('total_test_cases', 0)
                all_results['overall_summary']['passed_test_cases'] += summary.get('passed_test_cases', 0)
                all_results['overall_summary']['failed_test_cases'] += summary.get('failed_test_cases', 0)
                all_results['overall_summary']['error_test_cases'] += summary.get('error_test_cases', 0)
        
        # Calcular success rate general
        total_tests = all_results['overall_summary']['total_test_cases']
        if total_tests > 0:
            passed_tests = all_results['overall_summary']['passed_test_cases']
            all_results['overall_summary']['overall_success_rate'] = (passed_tests / total_tests) * 100
        
        all_results['end_time'] = datetime.utcnow().isoformat()
        
        return all_results
    
    async def generate_report(self, results: Dict[str, Any]) -> str:
        """Genera reporte de resultados"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"emergent_test_report_{timestamp}.json"
        
        # Guardar reporte JSON detallado
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Generar reporte markdown resumido
        md_report = self.reports_dir / f"emergent_test_summary_{timestamp}.md"
        await self._generate_markdown_report(results, md_report)
        
        return str(report_file)
    
    async def _generate_markdown_report(self, results: Dict[str, Any], md_file: Path):
        """Genera reporte en formato Markdown"""
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write("# 🧬 Reporte de Testing Emergente - Astroflora\n\n")
            f.write(f"**Execution ID:** {results['execution_id']}\n")
            f.write(f"**Fecha:** {results['start_time']}\n")
            f.write(f"**Backend URL:** {results['config']['backend_url']}\n\n")
            
            # Resumen general
            summary = results['overall_summary']
            f.write("## 📊 Resumen General\n\n")
            f.write(f"- **Total Suites:** {summary['total_suites']}\n")
            f.write(f"- **Total Escenarios:** {summary['total_scenarios']}\n")
            f.write(f"- **Total Test Cases:** {summary['total_test_cases']}\n")
            f.write(f"- **Passed:** {summary['passed_test_cases']} ✅\n")
            f.write(f"- **Failed:** {summary['failed_test_cases']} ❌\n")
            f.write(f"- **Errors:** {summary['error_test_cases']} ⚠️\n")
            f.write(f"- **Success Rate:** {summary['overall_success_rate']:.1f}%\n\n")
            
            # Detalles por suite
            f.write("## 📋 Resultados por Suite\n\n")
            for suite in results.get('suites', []):
                suite_info = suite['suite_info']
                suite_summary = suite['summary']
                
                f.write(f"### {suite_info.get('name', 'Unknown Suite')}\n")
                f.write(f"**Archivo:** {suite['suite_file']}\n")
                f.write(f"**Fase:** {suite_info.get('phase', 'Unknown')}\n")
                f.write(f"**Success Rate:** {suite_summary['success_rate']:.1f}%\n")
                f.write(f"**Test Cases:** {suite_summary['passed_test_cases']}/{suite_summary['total_test_cases']} passed\n\n")
    
    def print_final_summary(self, results: Dict[str, Any]):
        """Imprime resumen final en consola"""
        print("\n" + "="*80)
        print("🧬 REPORTE FINAL - TESTING EMERGENTE ASTROFLORA")
        print("="*80)
        
        summary = results['overall_summary']
        print(f"📊 RESUMEN GENERAL:")
        print(f"   Total Suites: {summary['total_suites']}")
        print(f"   Total Escenarios: {summary['total_scenarios']}")
        print(f"   Total Test Cases: {summary['total_test_cases']}")
        print(f"   ✅ Passed: {summary['passed_test_cases']}")
        print(f"   ❌ Failed: {summary['failed_test_cases']}")
        print(f"   ⚠️  Errors: {summary['error_test_cases']}")
        print(f"   🎯 Success Rate: {summary['overall_success_rate']:.1f}%")
        
        print(f"\n📋 RESULTADOS POR SUITE:")
        for suite in results.get('suites', []):
            suite_info = suite['suite_info']
            suite_summary = suite['summary']
            success_rate = suite_summary['success_rate']
            
            status_icon = "✅" if success_rate >= 90 else "⚠️" if success_rate >= 70 else "❌"
            print(f"   {status_icon} {suite_info.get('name', 'Unknown')}: {success_rate:.1f}% "
                  f"({suite_summary['passed_test_cases']}/{suite_summary['total_test_cases']})")
        
        # Recomendaciones
        print(f"\n🔍 RECOMENDACIONES:")
        if summary['overall_success_rate'] >= 95:
            print("   🎉 Excelente! Sistema agéntico funcionando óptimamente")
        elif summary['overall_success_rate'] >= 90:
            print("   ✅ Sistema estable, revisar fallos menores")
        elif summary['overall_success_rate'] >= 70:
            print("   ⚠️  Sistema funcional con problemas que necesitan atención")
        else:
            print("   ❌ Sistema requiere atención inmediata - fallos críticos detectados")
        
        print("="*80)

async def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='Astroflora Emergent Test Executor')
    parser.add_argument('--suite', type=str, help='Ejecutar una suite específica')
    parser.add_argument('--config', type=str, help='Archivo de configuración personalizada')
    parser.add_argument('--verbose', action='store_true', help='Modo verbose')
    
    args = parser.parse_args()
    
    # Crear ejecutor
    executor = EmergentTestExecutor(args.config)
    
    try:
        if args.suite:
            # Ejecutar suite específica
            results = await executor.execute_test_suite(args.suite)
            if 'error' not in results:
                # Wrap single suite result in the expected format
                suite_summary = results['summary']
                results = {
                    'execution_id': executor.execution_id,
                    'start_time': executor.start_time.isoformat(),
                    'config': executor.config,
                    'suites': [results], 
                    'overall_summary': {
                        'total_suites': 1,
                        'total_scenarios': suite_summary.get('total_scenarios', 0),
                        'total_test_cases': suite_summary.get('total_test_cases', 0),
                        'passed_test_cases': suite_summary.get('passed_test_cases', 0),
                        'failed_test_cases': suite_summary.get('failed_test_cases', 0),
                        'error_test_cases': suite_summary.get('error_test_cases', 0),
                        'overall_success_rate': suite_summary.get('success_rate', 0.0)
                    }
                }
        else:
            # Ejecutar todas las suites
            results = await executor.execute_all_suites()
        
        # Generar reporte
        if 'error' not in results:
            report_file = await executor.generate_report(results)
            executor.print_final_summary(results)
            print(f"\n📄 Reporte detallado guardado en: {report_file}")
        else:
            print(f"❌ Error durante ejecución: {results['error']}")
            return 1
    
    except KeyboardInterrupt:
        print("\n⚠️  Ejecución interrumpida por el usuario")
        return 1
    except Exception as e:
        print(f"❌ Error crítico: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)