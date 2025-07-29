# -*- coding: utf-8 -*-
"""
ASTROFLORA - ATOMIC TOOLS FOR MCP ARCHITECTURE
Enhanced atomic tools that integrate with MCP servers and agentic orchestration.
Migration from monolithic pipeline to atomic, composable tools.
"""
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
import json

from mcp.protocol import CorrelationContext, ToolCapability
from models.analysis import ToolResult

logger = logging.getLogger(__name__)

@dataclass
class AtomicToolResult:
    """Enhanced result from atomic tool execution"""
    tool_name: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: int = 0
    metadata: Optional[Dict[str, Any]] = None
    suggestions: List[str] = None  # Suggested next tools
    correlation_id: Optional[str] = None
    
    def to_tool_result(self) -> ToolResult:
        """Convert to legacy ToolResult for compatibility"""
        return ToolResult(
            success=self.success,
            result=self.result or {},
            error_message=self.error_message,
            execution_time=self.execution_time_ms / 1000.0
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata or {},
            "suggestions": self.suggestions or [],
            "correlation_id": self.correlation_id
        }

class AtomicTool(ABC):
    """Enhanced base class for atomic tools with MCP integration"""
    
    def __init__(self, tool_name: str, capabilities: List[ToolCapability]):
        self.tool_name = tool_name
        self.capabilities = capabilities
        self.logger = logging.getLogger(f"{__name__}.{tool_name}")
    
    @abstractmethod
    async def execute(
        self, 
        parameters: Dict[str, Any], 
        correlation_context: CorrelationContext
    ) -> AtomicToolResult:
        """Execute the tool with given parameters"""
        pass
    
    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """Get JSON schema for tool inputs"""
        pass
    
    @abstractmethod
    def get_output_schema(self) -> Dict[str, Any]:
        """Get JSON schema for tool outputs"""
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate input parameters against schema"""
        required_fields = self.get_input_schema().get("required", [])
        return all(field in parameters for field in required_fields)
    
    def get_estimated_duration_ms(self, parameters: Dict[str, Any]) -> int:
        """Estimate execution duration based on parameters"""
        return 1000  # Default 1 second

class BlastAtomicTool(AtomicTool):
    """Enhanced atomic BLAST sequence search tool"""
    
    def __init__(self):
        super().__init__("blast", [ToolCapability.BIOINFORMATICS])
    
    async def execute(
        self, 
        parameters: Dict[str, Any], 
        correlation_context: CorrelationContext
    ) -> AtomicToolResult:
        """Execute BLAST search with enhanced results"""
        start_time = time.time()
        
        try:
            self.logger.info(f"[{correlation_context.correlation_id}] Executing enhanced BLAST search")
            
            if not self.validate_parameters(parameters):
                raise ValueError("Missing required parameters for BLAST")
            
            sequence = parameters["sequence"]
            database = parameters.get("database", "nr")
            e_value = parameters.get("e_value", 0.001)
            
            # Enhanced simulation with realistic timing
            simulation_time = min(1.5 + (len(sequence) / 1000), 4.0)
            await asyncio.sleep(simulation_time)
            
            # Generate enhanced BLAST results
            hits = self._generate_enhanced_blast_hits(sequence, e_value)
            
            result = AtomicToolResult(
                tool_name=self.tool_name,
                success=True,
                result={
                    "hits": hits,
                    "statistics": {
                        "total_hits": len(hits),
                        "significant_hits": len([h for h in hits if h["e_value"] < e_value]),
                        "database": database,
                        "query_length": len(sequence),
                        "search_space": f"{len(sequence)} x 500M"
                    },
                    "query_sequence": sequence[:50] + "..." if len(sequence) > 50 else sequence,
                    "functional_annotations": self._extract_functional_annotations(hits)
                },
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "blast_version": "2.14.0",
                    "database_size": "500M sequences",
                    "algorithm": "blastp" if self._is_protein_sequence(sequence) else "blastn"
                },
                suggestions=self._suggest_next_tools(hits),
                correlation_id=correlation_context.correlation_id
            )
            
            return result
            
        except Exception as e:
            return AtomicToolResult(
                tool_name=self.tool_name,
                success=False,
                error_message=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
                correlation_id=correlation_context.correlation_id
            )
    
    def _generate_enhanced_blast_hits(self, sequence: str, e_value: float) -> List[Dict[str, Any]]:
        """Generate enhanced mock BLAST hits with functional information"""
        hits = []
        
        # Generate hits based on sequence characteristics
        if len(sequence) > 50:  # Substantial sequence
            hits.extend([
                {
                    "accession": "P12345.1",
                    "description": "DNA-binding transcriptional regulator [Escherichia coli K-12]",
                    "e_value": 1e-85,
                    "bit_score": 312.7,
                    "identity": 87.2,
                    "coverage": 95.5,
                    "length": len(sequence) - 5,
                    "organism": "Escherichia coli",
                    "function": "transcriptional regulation",
                    "go_terms": ["GO:0003677", "GO:0006355", "GO:0043565"]
                },
                {
                    "accession": "Q8X5A2.2", 
                    "description": "Hypothetical protein YqeH [Bacillus subtilis subsp. subtilis str. 168]",
                    "e_value": 2e-42,
                    "bit_score": 156.4,
                    "identity": 72.8,
                    "coverage": 88.2,
                    "length": len(sequence) - 15,
                    "organism": "Bacillus subtilis",
                    "function": "unknown",
                    "go_terms": []
                }
            ])
        
        if self._is_protein_sequence(sequence):
            hits.append({
                "accession": "A0A1B2C3D4.1",
                "description": "Conserved protein of unknown function DUF1234 [Multiple organisms]",
                "e_value": 5e-25,
                "bit_score": 98.6,
                "identity": 65.4,
                "coverage": 76.3,
                "length": len(sequence) - 25,
                "organism": "Various",
                "function": "protein binding",
                "go_terms": ["GO:0005515"]
            })
        
        # Filter by e-value and add position information
        filtered_hits = []
        for hit in hits:
            if hit["e_value"] <= e_value:
                hit["query_start"] = 1
                hit["query_end"] = hit["length"]
                hit["subject_start"] = 1  
                hit["subject_end"] = hit["length"]
                filtered_hits.append(hit)
        
        return filtered_hits
    
    def _extract_functional_annotations(self, hits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract functional annotations from BLAST hits"""
        functions = []
        go_terms = []
        organisms = []
        
        for hit in hits[:5]:  # Top 5 hits
            if hit.get("function") and hit["function"] not in functions:
                functions.append(hit["function"])
            if hit.get("go_terms"):
                go_terms.extend(hit["go_terms"])
            if hit.get("organism") and hit["organism"] not in organisms:
                organisms.append(hit["organism"])
        
        return {
            "predicted_functions": functions,
            "go_terms": list(set(go_terms)),
            "source_organisms": organisms,
            "confidence": "high" if len(hits) > 0 and hits[0]["e_value"] < 1e-50 else "medium"
        }
    
    def _suggest_next_tools(self, hits: List[Dict[str, Any]]) -> List[str]:
        """Suggest next tools based on BLAST results"""
        suggestions = []
        
        if len(hits) > 1:
            suggestions.append("mafft")  # Multiple alignment of hits
        
        if any(hit.get("function") and "protein" in hit["function"] for hit in hits):
            suggestions.extend(["alphafold", "interpro"])
        
        if any(hit.get("go_terms") for hit in hits):
            suggestions.append("function_analyzer")
        
        if not hits:
            suggestions.append("sequence_analyzer")  # AI analysis for orphan sequences
        
        return suggestions
    
    def _is_protein_sequence(self, sequence: str) -> bool:
        """Simple heuristic to determine if sequence is protein"""
        protein_chars = set("ACDEFGHIKLMNPQRSTVWY")
        seq_chars = set(sequence.upper())
        return len(seq_chars - protein_chars) / len(seq_chars) < 0.1 if seq_chars else False
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sequence": {"type": "string", "description": "Input sequence", "minLength": 10},
                "database": {"type": "string", "default": "nr", "enum": ["nr", "swissprot", "pdb", "refseq"]},
                "e_value": {"type": "number", "default": 0.001, "minimum": 1e-300, "maximum": 1000}
            },
            "required": ["sequence"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "hits": {"type": "array", "items": {"type": "object"}},
                "statistics": {"type": "object"},
                "functional_annotations": {"type": "object"},
                "query_sequence": {"type": "string"}
            }
        }
    
    def get_estimated_duration_ms(self, parameters: Dict[str, Any]) -> int:
        """Estimate BLAST execution time"""
        sequence_length = len(parameters.get("sequence", ""))
        return min(1500 + (sequence_length * 2), 8000)  # 1.5s base + 2ms per residue, max 8s

class MafftAtomicTool(AtomicTool):
    """Enhanced atomic MAFFT multiple sequence alignment tool"""
    
    def __init__(self):
        super().__init__("mafft", [ToolCapability.BIOINFORMATICS])
    
    async def execute(
        self, 
        parameters: Dict[str, Any], 
        correlation_context: CorrelationContext
    ) -> AtomicToolResult:
        """Execute enhanced MAFFT alignment"""
        start_time = time.time()
        
        try:
            self.logger.info(f"[{correlation_context.correlation_id}] Executing enhanced MAFFT alignment")
            
            if not self.validate_parameters(parameters):
                raise ValueError("Missing required parameters for MAFFT")
            
            sequences = parameters["sequences"]
            algorithm = parameters.get("algorithm", "auto")
            
            if len(sequences) < 2:
                raise ValueError("At least 2 sequences required for alignment")
            
            # Enhanced simulation with realistic timing
            execution_time = 0.8 + (len(sequences) * 0.4) + (sum(len(s) for s in sequences) / 10000)
            await asyncio.sleep(min(execution_time, 5.0))
            
            # Generate enhanced alignment
            aligned_sequences = self._generate_enhanced_alignment(sequences)
            alignment_metrics = self._calculate_alignment_metrics(aligned_sequences)
            
            result = AtomicToolResult(
                tool_name=self.tool_name,
                success=True,
                result={
                    "aligned_sequences": aligned_sequences,
                    "alignment_score": alignment_metrics["overall_score"],
                    "statistics": {
                        "sequence_count": len(sequences),
                        "alignment_length": len(aligned_sequences[0]) if aligned_sequences else 0,
                        "algorithm_used": algorithm,
                        "gaps_introduced": sum(seq.count("-") for seq in aligned_sequences),
                        "conservation_score": alignment_metrics["conservation_score"]
                    },
                    "conservation_analysis": alignment_metrics["conservation_analysis"],
                    "quality_metrics": alignment_metrics
                },
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "mafft_version": "7.505",
                    "parameters_used": {"algorithm": algorithm},
                    "memory_usage": f"{len(sequences) * 50}MB"
                },
                suggestions=self._suggest_alignment_tools(alignment_metrics),
                correlation_id=correlation_context.correlation_id
            )
            
            return result
            
        except Exception as e:
            return AtomicToolResult(
                tool_name=self.tool_name,
                success=False,
                error_message=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
                correlation_id=correlation_context.correlation_id
            )
    
    def _generate_enhanced_alignment(self, sequences: List[str]) -> List[str]:
        """Generate enhanced sequence alignment with conservation patterns"""
        if not sequences:
            return []
        
        # Find common subsequences for better alignment simulation
        common_regions = self._find_common_regions(sequences)
        max_length = max(len(seq) for seq in sequences)
        
        aligned = []
        for i, seq in enumerate(sequences):
            aligned_seq = ""
            seq_pos = 0
            
            for pos in range(max_length + 20):  # Add some buffer for gaps
                if seq_pos < len(seq):
                    # Occasionally add gaps in less conserved regions
                    if pos % 15 == i % 3 and pos not in common_regions:  # Stagger gaps
                        aligned_seq += "-"
                    else:
                        aligned_seq += seq[seq_pos]
                        seq_pos += 1
                else:
                    aligned_seq += "-"
                    
                # Don't exceed reasonable length
                if len(aligned_seq) >= max_length + 50:
                    break
            
            aligned.append(aligned_seq)
        
        # Ensure all sequences have the same length
        final_length = max(len(seq) for seq in aligned)
        aligned = [seq.ljust(final_length, "-") for seq in aligned]
        
        return aligned
    
    def _find_common_regions(self, sequences: List[str]) -> List[int]:
        """Identify positions likely to be conserved"""
        if len(sequences) < 2:
            return []
        
        min_length = min(len(seq) for seq in sequences)
        common_positions = []
        
        for i in range(min_length):
            column = [seq[i] for seq in sequences if i < len(seq)]
            if len(set(column)) <= 2:  # Mostly conserved
                common_positions.append(i)
        
        return common_positions
    
    def _calculate_alignment_metrics(self, aligned_sequences: List[str]) -> Dict[str, Any]:
        """Calculate comprehensive alignment quality metrics"""
        if not aligned_sequences or len(aligned_sequences) < 2:
            return {"overall_score": 0.0, "conservation_score": 0.0, "conservation_analysis": {}}
        
        alignment_length = len(aligned_sequences[0])
        conserved_positions = 0
        identical_positions = 0
        gap_positions = 0
        
        conservation_by_position = []
        
        for i in range(alignment_length):
            column = [seq[i] for seq in aligned_sequences if i < len(seq)]
            non_gap_column = [c for c in column if c != "-"]
            
            if not non_gap_column:
                gap_positions += 1
                conservation_by_position.append(0.0)
                continue
            
            # Calculate position conservation
            unique_residues = len(set(non_gap_column))
            if unique_residues == 1:
                identical_positions += 1
                conservation_by_position.append(1.0)
            elif unique_residues <= 2:
                conserved_positions += 1
                conservation_by_position.append(0.7)
            elif unique_residues <= 3:
                conservation_by_position.append(0.4)
            else:
                conservation_by_position.append(0.1)
        
        conservation_score = (identical_positions + conserved_positions * 0.7) / alignment_length
        overall_score = conservation_score * (1 - gap_positions / alignment_length * 0.5)
        
        return {
            "overall_score": overall_score,
            "conservation_score": conservation_score,
            "identical_positions": identical_positions,
            "conserved_positions": conserved_positions,
            "gap_positions": gap_positions,
            "conservation_analysis": {
                "highly_conserved_regions": len([c for c in conservation_by_position if c > 0.8]),
                "moderately_conserved_regions": len([c for c in conservation_by_position if 0.4 < c <= 0.8]),
                "variable_regions": len([c for c in conservation_by_position if c <= 0.4]),
                "average_conservation": sum(conservation_by_position) / len(conservation_by_position)
            }
        }
    
    def _suggest_alignment_tools(self, metrics: Dict[str, Any]) -> List[str]:
        """Suggest next tools based on alignment quality"""
        suggestions = []
        
        if metrics["conservation_score"] > 0.7:
            suggestions.extend(["conservation_analyzer", "phylogenetic_analyzer"])
        
        if metrics["overall_score"] > 0.6:
            suggestions.append("alphafold")  # Good alignment suggests structure prediction
        
        if metrics.get("conservation_analysis", {}).get("highly_conserved_regions", 0) > 5:
            suggestions.append("domain_analyzer")
        
        suggestions.append("sequence_analyzer")  # AI analysis of alignment
        
        return suggestions
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sequences": {
                    "type": "array", 
                    "items": {"type": "string", "minLength": 10}, 
                    "minItems": 2,
                    "maxItems": 100
                },
                "algorithm": {
                    "type": "string", 
                    "default": "auto", 
                    "enum": ["auto", "linsi", "ginsi", "einsi", "fftns", "fftnsi"]
                }
            },
            "required": ["sequences"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "aligned_sequences": {"type": "array", "items": {"type": "string"}},
                "alignment_score": {"type": "number"},
                "statistics": {"type": "object"},
                "conservation_analysis": {"type": "object"},
                "quality_metrics": {"type": "object"}
            }
        }
    
    def get_estimated_duration_ms(self, parameters: Dict[str, Any]) -> int:
        """Estimate MAFFT execution time"""
        sequences = parameters.get("sequences", [])
        if not sequences:
            return 1000
        
        num_sequences = len(sequences)
        total_length = sum(len(seq) for seq in sequences)
        
        # Quadratic scaling with sequence count, linear with length
        return min(800 + (num_sequences * num_sequences * 100) + (total_length // 10), 30000)

# Enhanced Tool Registry with MCP integration
class EnhancedAtomicToolRegistry:
    """Enhanced registry for atomic tools with MCP integration"""
    
    def __init__(self):
        self.tools: Dict[str, AtomicTool] = {}
        self.execution_stats: Dict[str, Dict[str, Any]] = {}
        self._register_enhanced_tools()
    
    def _register_enhanced_tools(self):
        """Register enhanced atomic tools"""
        enhanced_tools = [
            BlastAtomicTool(),
            MafftAtomicTool(),
            # AlphaFoldAtomicTool() can be added here
        ]
        
        for tool in enhanced_tools:
            self.register_tool(tool)
    
    def register_tool(self, tool: AtomicTool):
        """Register a new atomic tool with statistics tracking"""
        self.tools[tool.tool_name] = tool
        self.execution_stats[tool.tool_name] = {
            "total_executions": 0,
            "successful_executions": 0,
            "average_duration_ms": 0,
            "last_executed": None
        }
        logger.info(f"Registered enhanced atomic tool: {tool.tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[AtomicTool]:
        """Get tool by name"""
        return self.tools.get(tool_name)
    
    def list_tools(self, capability_filter: Optional[ToolCapability] = None) -> List[str]:
        """List tools, optionally filtered by capability"""
        if capability_filter is None:
            return list(self.tools.keys())
        
        return [
            name for name, tool in self.tools.items() 
            if capability_filter in tool.capabilities
        ]
    
    def get_tool_metadata(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive tool metadata"""
        tool = self.get_tool(tool_name)
        if not tool:
            return None
        
        stats = self.execution_stats.get(tool_name, {})
        
        return {
            "tool_name": tool_name,
            "capabilities": [cap.value for cap in tool.capabilities],
            "input_schema": tool.get_input_schema(),
            "output_schema": tool.get_output_schema(),
            "execution_stats": stats,
            "estimated_duration_range": "1-30 seconds"  # Could be more specific per tool
        }
    
    async def execute_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any], 
        correlation_context: CorrelationContext
    ) -> AtomicToolResult:
        """Execute a tool with statistics tracking"""
        tool = self.get_tool(tool_name)
        if not tool:
            return AtomicToolResult(
                tool_name=tool_name,
                success=False,
                error_message=f"Tool not found: {tool_name}",
                correlation_id=correlation_context.correlation_id
            )
        
        # Update execution stats
        stats = self.execution_stats[tool_name]
        stats["total_executions"] += 1
        stats["last_executed"] = datetime.utcnow().isoformat()
        
        # Execute tool
        result = await tool.execute(parameters, correlation_context)
        
        # Update success stats and average duration
        if result.success:
            stats["successful_executions"] += 1
        
        # Update average duration (simple moving average)
        if stats["average_duration_ms"] == 0:
            stats["average_duration_ms"] = result.execution_time_ms
        else:
            stats["average_duration_ms"] = (
                stats["average_duration_ms"] * 0.8 + result.execution_time_ms * 0.2
            )
        
        return result
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get overall execution statistics"""
        total_executions = sum(stats["total_executions"] for stats in self.execution_stats.values())
        total_successful = sum(stats["successful_executions"] for stats in self.execution_stats.values())
        
        return {
            "total_tools": len(self.tools),
            "total_executions": total_executions,
            "total_successful": total_successful,
            "success_rate": total_successful / total_executions if total_executions > 0 else 0,
            "tools_stats": self.execution_stats
        }

# Global enhanced atomic tool registry
atomic_tool_registry = EnhancedAtomicToolRegistry()