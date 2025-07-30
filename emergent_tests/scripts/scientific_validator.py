#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCIENTIFIC VALIDATION MODULE FOR ASTROFLORA EMERGENT TESTING

This module provides enhanced scientific validation capabilities for biological data,
including biological variance awareness, sequence similarity analysis, and E-value validation.
"""

import json
import re
from typing import Dict, Any, List, Optional, Union
from Bio import pairwise2
from Bio.Seq import Seq
import logging

logger = logging.getLogger(__name__)

class ScientificValidator:
    """Enhanced scientific validation with biological variance awareness"""
    
    def __init__(self):
        self.biological_reference_data = self._load_reference_data()
    
    def _load_reference_data(self) -> Dict[str, Any]:
        """Load biological reference data for validation contextualization"""
        return {
            'e_value_ranges': {
                'highly_significant': {'min': 0, 'max': 1e-50, 'description': 'Extremely strong homology'},
                'very_significant': {'min': 1e-50, 'max': 1e-30, 'description': 'Very strong homology'},
                'significant': {'min': 1e-30, 'max': 1e-10, 'description': 'Strong homology'},
                'marginally_significant': {'min': 1e-10, 'max': 1e-5, 'description': 'Moderate homology'},
                'weakly_significant': {'min': 1e-5, 'max': 0.01, 'description': 'Weak homology'},
                'not_significant': {'min': 0.01, 'max': float('inf'), 'description': 'No significant homology'},
            },
            'sequence_identity_interpretation': {
                'identical': {'min': 0.99, 'max': 1.0, 'description': 'Same protein'},
                'highly_conserved': {'min': 0.9, 'max': 0.99, 'description': 'Same function, likely orthologs'},
                'conserved': {'min': 0.7, 'max': 0.9, 'description': 'Same family, similar function'},
                'related': {'min': 0.5, 'max': 0.7, 'description': 'Same superfamily, potentially divergent function'},
                'distant': {'min': 0.3, 'max': 0.5, 'description': 'Distant relationship, different function likely'},
                'unrelated': {'min': 0, 'max': 0.3, 'description': 'No detectable relationship'},
            }
        }
    
    def evaluate_criterion(self, criterion: Dict[str, Any], actual_value: Any) -> tuple[bool, str]:
        """
        Enhanced criterion evaluation with biological variance awareness
        
        Args:
            criterion: Dictionary with validation criteria
            actual_value: The actual value to validate
            
        Returns:
            tuple: (passed: bool, message: str)
        """
        try:
            criterion_type = criterion.get('type', 'exact_match')
            
            if criterion_type == 'exact_match':
                expected = criterion.get('expected_value')
                passed = actual_value == expected
                message = f"Expected exactly {expected}, got {actual_value}"
                
            elif criterion_type == 'numeric_range':
                passed, message = self._validate_numeric_range(criterion, actual_value)
                
            elif criterion_type == 'sequence_similarity':
                passed, message = self._validate_sequence_similarity(criterion, actual_value)
                
            elif criterion_type == 'json_path':
                passed, message = self._validate_json_path(criterion, actual_value)
                
            elif criterion_type == 'array_length_min':
                min_length = criterion.get('min', 0)
                actual_length = len(actual_value) if hasattr(actual_value, '__len__') else 0
                passed = actual_length >= min_length
                message = f"Array length {actual_length} >= {min_length}: {'✓' if passed else '✗'}"
                
            elif criterion_type == 'string_not_empty':
                passed = bool(actual_value and str(actual_value).strip())
                message = f"String not empty: {'✓' if passed else '✗'} (value: '{actual_value}')"
                
            elif criterion_type == 'response_time':
                max_time = criterion.get('max_average_ms', 5000)
                actual_time = float(actual_value) if actual_value else 0
                passed = actual_time <= max_time
                message = f"Response time {actual_time}ms <= {max_time}ms: {'✓' if passed else '✗'}"
                
            elif criterion_type == 'success_rate':
                min_rate = criterion.get('min_percent', 90) / 100.0
                actual_rate = float(actual_value) if actual_value else 0
                passed = actual_rate >= min_rate
                message = f"Success rate {actual_rate*100:.1f}% >= {min_rate*100:.1f}%: {'✓' if passed else '✗'}"
                
            else:
                # Default to basic validation for unknown types
                passed = True
                message = f"Unknown validation type '{criterion_type}' - defaulting to pass"
                logger.warning(message)
            
            return passed, message
            
        except Exception as e:
            error_msg = f"Validation error for criterion {criterion}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _validate_numeric_range(self, criterion: Dict[str, Any], actual_value: Any) -> tuple[bool, str]:
        """Validate numeric ranges with biological variance tolerance"""
        try:
            actual_num = float(actual_value)
            min_val = criterion.get('min', float('-inf'))
            max_val = criterion.get('max', float('inf'))
            
            # Check if this is a biological metric that needs tolerance
            if criterion.get('biological_metric', False):
                tolerance = criterion.get('tolerance', 0.1)  # Default 10% tolerance
                
                # Apply tolerance to the expected range
                if min_val != float('-inf'):
                    adjusted_min = min_val * (1 - tolerance)
                else:
                    adjusted_min = min_val
                    
                if max_val != float('inf'):
                    adjusted_max = max_val * (1 + tolerance)
                else:
                    adjusted_max = max_val
                
                passed = adjusted_min <= actual_num <= adjusted_max
                
                # Add biological context for E-values
                if 'e_value' in str(criterion).lower():
                    context = self._get_evalue_context(actual_num)
                    message = f"E-value {actual_num} in range [{adjusted_min}, {adjusted_max}] (with {tolerance*100}% biological tolerance): {'✓' if passed else '✗'}. Context: {context}"
                else:
                    message = f"Biological metric {actual_num} in range [{adjusted_min}, {adjusted_max}] (with {tolerance*100}% tolerance): {'✓' if passed else '✗'}"
            else:
                # Standard numeric validation
                passed = min_val <= actual_num <= max_val
                message = f"Value {actual_num} in range [{min_val}, {max_val}]: {'✓' if passed else '✗'}"
            
            return passed, message
            
        except (ValueError, TypeError) as e:
            return False, f"Invalid numeric value '{actual_value}': {str(e)}"
    
    def _validate_sequence_similarity(self, criterion: Dict[str, Any], actual_value: Any) -> tuple[bool, str]:
        """Validate sequence similarity using alignment-based comparison"""
        try:
            expected_seq = Seq(criterion['expected_sequence'])
            actual_seq = Seq(str(actual_value))
            
            # Calculate sequence identity using global alignment
            alignments = pairwise2.align.globalxx(expected_seq, actual_seq)
            if not alignments:
                return False, "No alignment could be generated"
                
            best_alignment = alignments[0]
            sequence_identity = best_alignment.score / max(len(expected_seq), len(actual_seq))
            
            min_identity = criterion.get('min_identity', 0.8)  # Default 80% identity threshold
            passed = sequence_identity >= min_identity
            
            # Get biological context
            context = self._get_sequence_identity_context(sequence_identity)
            
            message = f"Sequence identity {sequence_identity:.3f} >= {min_identity}: {'✓' if passed else '✗'}. Context: {context['description']}. Differences: {len(expected_seq) - best_alignment.score} positions in {len(expected_seq)} residues."
            
            return passed, message
            
        except Exception as e:
            return False, f"Sequence similarity validation error: {str(e)}"
    
    def _validate_json_path(self, criterion: Dict[str, Any], data: Any) -> tuple[bool, str]:
        """Validate JSON path extraction and nested criterion"""
        try:
            path = criterion.get('path', '')
            nested_criterion = criterion.get('criterion', {})
            
            # Extract value using simple JSON path ($.path.to.value)
            extracted_value = self._extract_json_path(data, path)
            
            if extracted_value is None:
                return False, f"JSON path '{path}' not found in data"
            
            # Recursively validate the extracted value
            return self.evaluate_criterion(nested_criterion, extracted_value)
            
        except Exception as e:
            return False, f"JSON path validation error: {str(e)}"
    
    def _extract_json_path(self, data: Any, path: str) -> Any:
        """Simple JSON path extraction ($.path.to.value)"""
        if not path.startswith('$'):
            return None
            
        try:
            # Remove the leading '$.' and split by '.'
            path_parts = path[2:].split('.') if path.startswith('$.') else path[1:].split('.')
            
            current = data
            for part in path_parts:
                if isinstance(current, dict):
                    # Handle array access like results[0]
                    if '[' in part and ']' in part:
                        key, index_part = part.split('[', 1)
                        index = int(index_part.rstrip(']'))
                        current = current.get(key, [])[index]
                    else:
                        current = current.get(part)
                elif isinstance(current, list) and part.isdigit():
                    current = current[int(part)]
                else:
                    return None
                    
                if current is None:
                    return None
                    
            return current
            
        except (KeyError, IndexError, ValueError, TypeError):
            return None
    
    def _get_evalue_context(self, e_value: float) -> str:
        """Get biological context for E-value"""
        for category, range_data in self.biological_reference_data['e_value_ranges'].items():
            if range_data['min'] <= e_value <= range_data['max']:
                return f"{category} ({range_data['description']})"
        return "unknown range"
    
    def _get_sequence_identity_context(self, identity: float) -> Dict[str, Any]:
        """Get biological context for sequence identity"""
        for category, range_data in self.biological_reference_data['sequence_identity_interpretation'].items():
            if range_data['min'] <= identity <= range_data['max']:
                return range_data
        return {'description': 'unknown identity range'}
    
    def contextualize_failure(self, test_case: Dict[str, Any], criterion: Dict[str, Any], actual_value: Any) -> str:
        """Add scientific context to validation failures"""
        criterion_type = criterion.get('type', 'unknown')
        test_name = test_case.get('name', 'Unknown test')
        
        if criterion_type == 'numeric_range' and criterion.get('biological_metric'):
            if 'e_value' in test_name.lower():
                return self._contextualize_evalue_failure(actual_value, criterion)
        elif criterion_type == 'sequence_similarity':
            return self._contextualize_sequence_failure(actual_value, criterion)
            
        return f"Validation failed for {test_name}: expected {criterion}, got {actual_value}"
    
    def _contextualize_evalue_failure(self, actual_value: float, criterion: Dict[str, Any]) -> str:
        """Contextualize E-value validation failures"""
        actual_context = self._get_evalue_context(actual_value)
        expected_min = criterion['min']
        expected_max = criterion['max']
        
        # Find expected category
        expected_context = "unknown"
        for name, range_data in self.biological_reference_data['e_value_ranges'].items():
            if range_data['min'] <= expected_min and range_data['max'] >= expected_max:
                expected_context = f"{name} ({range_data['description']})"
                break
        
        tolerance = criterion.get('tolerance', 0.1)
        impact_assessment = "might not affect biological interpretation" if abs(actual_value - expected_min) < expected_min * 10 else "could affect biological interpretation"
        
        return f"E-value validation failed. Got {actual_value} ({actual_context}), expected range [{expected_min}, {expected_max}] ({expected_context}). Tolerance: {tolerance*100}%. Note: Lower E-values indicate stronger sequence similarity. This discrepancy {impact_assessment}."
    
    def _contextualize_sequence_failure(self, actual_value: str, criterion: Dict[str, Any]) -> str:
        """Contextualize sequence similarity validation failures"""
        try:
            expected_seq = Seq(criterion['expected_sequence'])
            actual_seq = Seq(str(actual_value))
            
            # Calculate actual identity
            alignments = pairwise2.align.globalxx(expected_seq, actual_seq)
            if alignments:
                best_alignment = alignments[0]
                sequence_identity = best_alignment.score / max(len(expected_seq), len(actual_seq))
                differences = len(expected_seq) - best_alignment.score
            else:
                sequence_identity = 0.0
                differences = len(expected_seq)
            
            actual_context = self._get_sequence_identity_context(sequence_identity)
            min_identity = criterion.get('min_identity', 0.8)
            
            return f"Sequence similarity validation failed. Identity: {sequence_identity:.2f} ({actual_context['description']}). Expected minimum: {min_identity}. Differences: {differences} positions in {len(expected_seq)} residues."
            
        except Exception as e:
            return f"Sequence similarity failure contextualization error: {str(e)}"


class ScientificErrorReporter:
    """Enhanced error reporting with scientific context"""
    
    def __init__(self):
        self.validator = ScientificValidator()
    
    def generate_failure_report(self, test_case: Dict[str, Any], failures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive failure report with scientific context"""
        report = {
            'test_case_name': test_case.get('name', 'Unknown'),
            'test_case_id': test_case.get('case_id', 'Unknown'),
            'total_failures': len(failures),
            'failure_details': [],
            'scientific_context': {},
            'recommendations': []
        }
        
        for failure in failures:
            criterion = failure.get('criterion', {})
            actual_value = failure.get('actual_value')
            
            failure_detail = {
                'criterion_type': criterion.get('type', 'unknown'),
                'error_message': failure.get('message', 'No message'),
                'scientific_context': self.validator.contextualize_failure(test_case, criterion, actual_value)
            }
            
            report['failure_details'].append(failure_detail)
        
        # Add overall recommendations
        report['recommendations'] = self._generate_recommendations(test_case, failures)
        
        return report
    
    def _generate_recommendations(self, test_case: Dict[str, Any], failures: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on failure patterns"""
        recommendations = []
        
        # Analyze failure patterns
        criterion_types = [f.get('criterion', {}).get('type') for f in failures]
        
        if 'numeric_range' in criterion_types:
            recommendations.append("Consider increasing biological variance tolerance for numeric validations")
        
        if 'sequence_similarity' in criterion_types:
            recommendations.append("Review minimum identity thresholds for sequence comparisons")
        
        if len(failures) > len(set(criterion_types)):
            recommendations.append("Multiple failures of same type suggest systematic issue")
        
        return recommendations