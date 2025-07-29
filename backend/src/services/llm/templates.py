# -*- coding: utf-8 -*-
"""
Prompt Templates for LLM Workers
Provides standardized templates for scientific analysis
"""
from typing import Dict, Any, List, Optional
from enum import Enum
import json

class TemplateType(str, Enum):
    """Types of prompt templates"""
    SEQUENCE_ANALYSIS = "sequence_analysis"
    FUNCTION_PREDICTION = "function_prediction"
    STRUCTURAL_ANALYSIS = "structural_analysis"
    EVOLUTIONARY_ANALYSIS = "evolutionary_analysis"
    DATA_INTEGRATION = "data_integration"
    EXPERIMENTAL_DESIGN = "experimental_design"

class PromptTemplate:
    """Prompt template for LLM requests"""
    
    def __init__(
        self,
        name: str,
        template_type: TemplateType,
        system_prompt: str,
        user_prompt_template: str,
        variables: List[str],
        output_format: str = "json",
        description: str = ""
    ):
        self.name = name
        self.template_type = template_type
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.variables = variables
        self.output_format = output_format
        self.description = description
    
    def render(self, variables: Dict[str, Any]) -> List[Dict[str, str]]:
        """Render template with variables"""
        # Check required variables
        missing_vars = [var for var in self.variables if var not in variables]
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        
        # Render user prompt
        user_prompt = self.user_prompt_template
        for var_name, var_value in variables.items():
            placeholder = f"{{{var_name}}}"
            if isinstance(var_value, (dict, list)):
                var_value = json.dumps(var_value, indent=2)
            user_prompt = user_prompt.replace(placeholder, str(var_value))
        
        # Return messages format
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        if user_prompt.strip():
            messages.append({"role": "user", "content": user_prompt})
        
        return messages

class PromptTemplateRegistry:
    """Registry for prompt templates"""
    
    def __init__(self):
        self.templates: Dict[str, PromptTemplate] = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default scientific templates"""
        
        # Sequence Analysis Template
        self.register_template(PromptTemplate(
            name="sequence_analysis",
            template_type=TemplateType.SEQUENCE_ANALYSIS,
            system_prompt="""You are an expert bioinformatician with deep knowledge of molecular biology, genomics, and proteomics. 
You analyze biological sequences and provide scientifically accurate insights. Always respond in valid JSON format with structured analysis.""",
            user_prompt_template="""Analyze the following biological sequence data:

SEQUENCE: {sequence}
SEQUENCE_TYPE: {sequence_type}
CONTEXT: {context}

Provide a comprehensive analysis including:
1. Sequence characteristics and composition
2. Likely function and biological role
3. Structural features and domains
4. Evolutionary context
5. Confidence assessment
6. Recommended follow-up analyses

Respond in JSON format with the following structure:
{
    "sequence_analysis": {
        "length": <int>,
        "composition": <object>,
        "gc_content": <float>,
        "complexity": <float>
    },
    "functional_prediction": {
        "predicted_function": <string>,
        "confidence": <float>,
        "evidence": [<string>],
        "alternative_functions": [<string>]
    },
    "structural_features": {
        "domains": [<string>],
        "motifs": [<string>],
        "secondary_structure": <string>,
        "transmembrane_regions": <int>
    },
    "evolutionary_context": {
        "family": <string>,
        "conservation": <string>,
        "phylogenetic_distribution": <string>
    },
    "recommendations": [<string>],
    "confidence_score": <float>
}""",
            variables=["sequence", "sequence_type", "context"],
            output_format="json",
            description="Comprehensive biological sequence analysis"
        ))
        
        # Function Prediction Template
        self.register_template(PromptTemplate(
            name="function_prediction",
            template_type=TemplateType.FUNCTION_PREDICTION,
            system_prompt="""You are a protein function prediction expert with extensive knowledge of molecular mechanisms, 
biochemical pathways, and protein families. Analyze data to predict protein function with scientific rigor.""",
            user_prompt_template="""Predict the function of a protein based on multiple data sources:

BLAST RESULTS: {blast_results}
DOMAIN ANALYSIS: {domain_analysis}
SEQUENCE FEATURES: {sequence_features}
STRUCTURAL INFORMATION: {structural_info}

Integrate all available evidence to predict the most likely function. Consider:
1. Homology evidence from BLAST
2. Domain composition and architecture
3. Sequence-based features
4. Known structural similarities
5. Metabolic pathway context

Provide your analysis in JSON format:
{
    "primary_prediction": {
        "function": <string>,
        "ec_number": <string>,
        "pathway": <string>,
        "confidence": <float>,
        "evidence_strength": <string>
    },
    "alternative_predictions": [
        {
            "function": <string>,
            "confidence": <float>,
            "supporting_evidence": [<string>]
        }
    ],
    "domain_analysis": {
        "functional_domains": [<string>],
        "catalytic_residues": [<string>],
        "binding_sites": [<string>]
    },
    "pathway_context": {
        "metabolic_pathways": [<string>],
        "cellular_location": <string>,
        "interaction_partners": [<string>]
    },
    "experimental_validation": {
        "suggested_assays": [<string>],
        "key_experiments": [<string>],
        "expected_phenotypes": [<string>]
    },
    "confidence_assessment": {
        "overall_confidence": <float>,
        "limiting_factors": [<string>],
        "additional_data_needed": [<string>]
    }
}""",
            variables=["blast_results", "domain_analysis", "sequence_features", "structural_info"],
            output_format="json",
            description="Protein function prediction from multiple data sources"
        ))
        
        # Data Integration Template
        self.register_template(PromptTemplate(
            name="data_integration",
            template_type=TemplateType.DATA_INTEGRATION,
            system_prompt="""You are a systems biologist expert in integrating diverse biological data types. 
You synthesize information from multiple sources to provide comprehensive biological insights.""",
            user_prompt_template="""Integrate and analyze the following multi-omics data:

SEQUENCE_DATA: {sequence_data}
BLAST_RESULTS: {blast_results}
STRUCTURAL_DATA: {structural_data}
FUNCTIONAL_ANNOTATIONS: {functional_annotations}
EXPRESSION_DATA: {expression_data}
PATHWAY_DATA: {pathway_data}

Provide an integrated analysis that:
1. Synthesizes information across all data types
2. Identifies consistent patterns and discrepancies
3. Generates testable hypotheses
4. Suggests experimental validation strategies

Respond in JSON format:
{
    "integrated_analysis": {
        "consistent_findings": [<string>],
        "conflicting_evidence": [<string>],
        "data_quality_assessment": <string>,
        "confidence_level": <float>
    },
    "biological_insights": {
        "molecular_function": <string>,
        "biological_process": <string>,
        "cellular_component": <string>,
        "pathway_involvement": [<string>]
    },
    "systems_perspective": {
        "network_context": <string>,
        "regulatory_mechanisms": [<string>],
        "evolutionary_constraints": <string>
    },
    "hypotheses": [
        {
            "hypothesis": <string>,
            "supporting_evidence": [<string>],
            "testable_predictions": [<string>]
        }
    ],
    "experimental_design": {
        "priority_experiments": [<string>],
        "validation_approaches": [<string>],
        "expected_outcomes": [<string>]
    },
    "limitations": [<string>],
    "future_directions": [<string>]
}""",
            variables=["sequence_data", "blast_results", "structural_data", "functional_annotations", "expression_data", "pathway_data"],
            output_format="json",
            description="Integration of multi-omics biological data"
        ))
        
        # Experimental Design Template
        self.register_template(PromptTemplate(
            name="experimental_design",
            template_type=TemplateType.EXPERIMENTAL_DESIGN,
            system_prompt="""You are an experimental biologist with expertise in designing rigorous experiments 
to test biological hypotheses. You consider experimental feasibility, controls, and statistical power.""",
            user_prompt_template="""Design experiments to test the following biological hypothesis:

HYPOTHESIS: {hypothesis}
BACKGROUND_DATA: {background_data}
AVAILABLE_RESOURCES: {available_resources}
TIME_CONSTRAINTS: {time_constraints}
BUDGET_LEVEL: {budget_level}

Design a comprehensive experimental plan that includes:
1. Specific experimental approaches
2. Appropriate controls and replicates
3. Statistical considerations
4. Expected outcomes and interpretation
5. Alternative strategies if primary approach fails

Provide your experimental design in JSON format:
{
    "experimental_overview": {
        "primary_hypothesis": <string>,
        "specific_aims": [<string>],
        "expected_duration": <string>,
        "feasibility_assessment": <string>
    },
    "experimental_approaches": [
        {
            "approach_name": <string>,
            "methodology": <string>,
            "rationale": <string>,
            "expected_outcome": <string>,
            "pros_and_cons": [<string>]
        }
    ],
    "experimental_design": {
        "sample_size_calculation": <string>,
        "randomization_strategy": <string>,
        "blinding_approach": <string>,
        "replication_plan": <string>
    },
    "controls": {
        "positive_controls": [<string>],
        "negative_controls": [<string>],
        "technical_controls": [<string>]
    },
    "materials_and_methods": {
        "required_reagents": [<string>],
        "equipment_needed": [<string>],
        "protocols": [<string>]
    },
    "data_analysis": {
        "statistical_tests": [<string>],
        "multiple_testing_correction": <string>,
        "interpretation_criteria": [<string>]
    },
    "risk_assessment": {
        "potential_issues": [<string>],
        "mitigation_strategies": [<string>],
        "alternative_approaches": [<string>]
    },
    "timeline": [
        {
            "phase": <string>,
            "duration": <string>,
            "deliverables": [<string>]
        }
    ]
}""",
            variables=["hypothesis", "background_data", "available_resources", "time_constraints", "budget_level"],
            output_format="json",
            description="Design rigorous biological experiments"
        ))
    
    def register_template(self, template: PromptTemplate):
        """Register a new template"""
        self.templates[template.name] = template
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get template by name"""
        return self.templates.get(name)
    
    def list_templates(self, template_type: Optional[TemplateType] = None) -> List[str]:
        """List available templates, optionally filtered by type"""
        if template_type is None:
            return list(self.templates.keys())
        
        return [
            name for name, template in self.templates.items()
            if template.template_type == template_type
        ]
    
    def get_template_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get template information"""
        template = self.get_template(name)
        if not template:
            return None
        
        return {
            "name": template.name,
            "type": template.template_type.value,
            "description": template.description,
            "variables": template.variables,
            "output_format": template.output_format
        }
    
    def render_template(self, name: str, variables: Dict[str, Any]) -> List[Dict[str, str]]:
        """Render template with variables"""
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template '{name}' not found")
        
        return template.render(variables)

# Global template registry
template_registry = PromptTemplateRegistry()