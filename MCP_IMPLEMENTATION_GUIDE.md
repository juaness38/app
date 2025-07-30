# 🧬 Astroflora MCP (Model Context Protocol) Implementation Guide

## Overview

This document describes the complete MCP (Model Context Protocol) implementation in Astroflora, providing pure MCP alignment with agentic DriverIA and plug-and-play workers for scientific research automation.

## Architecture

### Core Components

1. **MCP Server for Tools** (`/mcp/tools`)
   - Standardized tool execution interface
   - Atomic tool integration
   - Hardware device management
   - Circuit breaker protection

2. **MCP Server for Data** (`/mcp/data`)
   - Context and resource management
   - Event storage and retrieval
   - Audit trail maintenance

3. **Agentic DriverIA** (`services/ai/agentic_driver_ia.py`)
   - HTTP-based MCP server consumption
   - Dynamic protocol orchestration
   - Correlation tracking

4. **LLM Workers** (`services/llm/`)
   - Plug-and-play LLM providers (OpenAI, Claude, Gemini)
   - SQS queue processing
   - Template-based scientific analysis

5. **Hardware Namespace** (`services/hardware/`)
   - Mock device simulation
   - Realistic device behavior
   - MCP-exposed functionality

## API Endpoints

### MCP Tools Server (`/mcp/tools`)

#### `POST /mcp/tools/list`
List available tools with filtering capabilities.

**Request:**
```json
{
  "correlation_context": {
    "correlation_id": "uuid",
    "user_id": "string",
    "session_id": "string"
  },
  "mcp_version": {
    "major": 1,
    "minor": 0,
    "patch": 0
  },
  "filter_capabilities": ["bioinformatics", "hardware", "ai_analysis"]
}
```

**Response:**
```json
{
  "success": true,
  "tools": [
    {
      "tool_name": "blast",
      "display_name": "BLAST Sequence Search",
      "description": "Basic Local Alignment Search Tool",
      "version": "2.0.0",
      "capabilities": ["bioinformatics"],
      "input_schema": { ... },
      "output_schema": { ... },
      "estimated_duration_ms": 5000
    }
  ],
  "total_count": 1,
  "correlation_context": { ... }
}
```

#### `POST /mcp/tools/call`
Execute a specific tool with parameters.

**Request:**
```json
{
  "correlation_context": { ... },
  "tool_name": "blast",
  "parameters": {
    "sequence": "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPD",
    "database": "nr",
    "e_value": 0.001
  },
  "timeout_ms": 30000
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "hits": [ ... ],
    "statistics": { ... },
    "functional_annotations": { ... }
  },
  "execution_time_ms": 2450,
  "tool_version": "2.0.0",
  "correlation_context": { ... },
  "metadata": {
    "audit_id": "uuid"
  }
}
```

### MCP Data Server (`/mcp/data`)

#### `POST /mcp/data/get_context`
Retrieve analysis context with optional history.

**Request:**
```json
{
  "correlation_context": { ... },
  "context_id": "analysis_uuid",
  "include_history": true
}
```

**Response:**
```json
{
  "success": true,
  "context_data": {
    "context_id": "analysis_uuid",
    "status": "completed",
    "results": { ... }
  },
  "metadata": {
    "resource_id": "analysis_uuid",
    "resource_type": "analysis_context",
    "created_at": "2024-01-01T00:00:00Z",
    "size_bytes": 1024
  },
  "history": [ ... ]
}
```

#### `POST /mcp/data/save_event`
Save event with correlation tracking.

**Request:**
```json
{
  "correlation_context": { ... },
  "event_type": "tool_executed",
  "event_data": {
    "tool_name": "blast",
    "success": true,
    "execution_time_ms": 2450
  },
  "agent": "mcp_tools_server"
}
```

## Tool Categories

### Bioinformatics Tools

1. **BLAST** - Enhanced sequence homology search
   - Functional annotations
   - Taxonomic distribution analysis
   - Tool suggestions based on results

2. **MAFFT** - Multiple sequence alignment
   - Conservation analysis
   - Quality metrics
   - Structural predictions

3. **AlphaFold** - Protein structure prediction (planned)
   - 3D structure modeling
   - Confidence scoring
   - Domain identification

### Hardware Tools

1. **Microscope Control**
   - Image capture
   - Magnification control
   - Z-stack acquisition

2. **Thermal Cycler**
   - PCR program execution
   - Temperature monitoring
   - Real-time status

### AI Analysis Tools

1. **Sequence Analyzer**
   - LLM-powered analysis
   - Function prediction
   - Structural insights

## LLM Workers

### Supported Providers

1. **OpenAI**
   - Models: GPT-4o, GPT-4, GPT-3.5-turbo
   - Default: gpt-4o

2. **Anthropic**
   - Models: Claude-3.5-sonnet, Claude-3-opus, Claude-3-sonnet
   - Default: claude-3-5-sonnet-20241022

3. **Google**
   - Models: Gemini-1.5-pro, Gemini-1.5-flash, Gemini-1.0-pro
   - Default: gemini-1.5-pro

### Prompt Templates

1. **Sequence Analysis**
   - Comprehensive biological sequence analysis
   - JSON-structured output
   - Scientific interpretation

2. **Function Prediction**
   - Multi-source data integration
   - Confidence assessment
   - Experimental validation suggestions

3. **Data Integration**
   - Multi-omics data synthesis
   - Hypothesis generation
   - Systems biology insights

4. **Experimental Design**
   - Rigorous experimental planning
   - Statistical considerations
   - Risk assessment

## Configuration

### Environment Variables

```bash
# MCP Configuration
MCP_TOOLS_URL="http://localhost:8001/mcp/tools"
MCP_DATA_URL="http://localhost:8001/mcp/data"

# LLM Provider Keys
OPENAI_API_KEY="sk-your-openai-key"
ANTHROPIC_API_KEY="your-anthropic-key"
GEMINI_API_KEY="your-gemini-key"

# AWS SQS (optional)
SQS_ANALYSIS_QUEUE_URL="https://sqs.region.amazonaws.com/account/queue"

# Circuit Breaker Settings
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
```

### Development Mode

For development, the system supports mock modes:
- SQS mock queue instead of AWS SQS
- Simulated LLM responses
- Hardware device mocks

## Security Features

### Correlation Tracking
- Unique correlation IDs for all requests
- User and session tracking
- Audit trail maintenance

### Input Validation
- Schema validation for all requests
- SQL injection prevention
- XSS protection
- Input length limits

### Circuit Breakers
- Failure detection and recovery
- Timeout protection
- Graceful degradation

### Audit Logging
```json
{
  "audit_id": "uuid",
  "correlation_context": { ... },
  "timestamp": "2024-01-01T00:00:00Z",
  "operation": "tool_call",
  "tool_name": "blast",
  "success": true,
  "execution_time_ms": 2450,
  "input_data_hash": "sha256_hash",
  "output_data_hash": "sha256_hash"
}
```

## Usage Examples

### Basic Tool Execution

```python
from mcp.protocol import ToolCallRequest, CorrelationContext
import httpx

# Create correlation context
correlation_context = CorrelationContext(
    correlation_id="unique-id",
    user_id="researcher-123"
)

# Execute BLAST search
request = ToolCallRequest(
    correlation_context=correlation_context,
    tool_name="blast",
    parameters={
        "sequence": "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPD",
        "database": "nr"
    }
)

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8001/mcp/tools/call",
        json=request.dict()
    )
    result = response.json()
```

### LLM Analysis with Template

```python
from services.llm.sqs_service import sqs_service
from services.llm.workers import LLMRequest, LLMProvider

# Create LLM request with template
llm_request = LLMRequest(
    request_id="unique-request-id",
    correlation_context=correlation_context,
    provider=LLMProvider.OPENAI,
    model="gpt-4o",
    messages=[],  # Will be populated by template
    parameters={
        "sequence": "MKQVFERRKSTSGLNPDEAVAAHHRKLLTQLLRRPD",
        "sequence_type": "protein",
        "context": "Unknown protein from bacterial genome",
        "max_tokens": 1000
    },
    template_name="sequence_analysis"
)

# Send to queue for processing
await sqs_service.send_message(llm_request)
```

## Performance Characteristics

### Throughput
- **Tools**: 10-50 requests/second per tool
- **LLM Workers**: 5-20 requests/second per provider
- **SQS Processing**: 100+ messages/minute

### Latency
- **Tool Execution**: 0.1-30 seconds (tool-dependent)
- **LLM Processing**: 1-10 seconds (model-dependent)
- **Data Operations**: <100ms

### Concurrency
- **Max Concurrent Jobs**: Configurable (default 10)
- **Worker Threads**: Configurable (default 5)
- **Circuit Breaker**: Automatic failure handling

## Testing

### Test Categories

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: MCP server interaction
3. **Contract Tests**: API contract compliance
4. **Security Tests**: Input validation and audit
5. **Performance Tests**: Load and concurrency
6. **End-to-End Tests**: Complete workflow validation

### Running Tests

```bash
# All MCP implementation tests
python test_mcp_implementation.py

# Enhanced integration tests
python test_enhanced_integration.py

# LLM worker tests
python test_llm_workers.py

# Comprehensive test suite
python test_comprehensive.py
```

## Troubleshooting

### Common Issues

1. **Tool Not Found**: Check tool registration in atomic tool registry
2. **LLM Provider Error**: Verify API keys and model availability
3. **Circuit Breaker Open**: Wait for recovery timeout or check service health
4. **SQS Connection**: Verify AWS credentials or use mock mode

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger("mcp").setLevel(logging.DEBUG)
logging.getLogger("services.llm").setLevel(logging.DEBUG)
```

### Health Checks

- **Tools Server**: `GET /mcp/tools/health`
- **Data Server**: `GET /mcp/data/health`
- **Main Application**: `GET /api/health`

## Future Enhancements

1. **WebSocket Support**: Real-time protocol visualization
2. **Advanced Templates**: Domain-specific prompt libraries
3. **Multi-modal LLMs**: Image and document analysis
4. **Enhanced Security**: Encryption for sensitive data
5. **Distributed Deployment**: Kubernetes-ready architecture

## Support

For technical support and questions:
- Check the comprehensive test suite for examples
- Review the contract tests for API specifications
- Monitor audit logs for debugging information
- Use health check endpoints for system status