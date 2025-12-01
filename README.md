# 🤖 Kubernetes-Aware RAG Agent

A production-ready LLM agent that combines Retrieval Augmented Generation (RAG) with live Kubernetes cluster metrics. Built with FastAPI, Ollama, Qdrant, and Kubernetes integration.

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.112.0-green.svg)](https://fastapi.tiangolo.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.28+-blue.svg)](https://kubernetes.io/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 🌟 Features

- **📚 RAG System**: Vector-based document retrieval using Qdrant and Ollama embeddings
- **☸️ K8s Integration**: Real-time cluster metrics (CPU, memory, pods, nodes)
- **🔄 Unified API**: Single FastAPI server combining RAG and Kubernetes queries
- **🐳 Container Ready**: Full Docker and Kubernetes deployment support
- **🔌 MCP Server**: Model Context Protocol server for Claude Desktop integration
- **🎯 Flexible Architecture**: Deploy as unified server, sidecar, or standalone services

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Deployment Options](#deployment-options)
- [Usage Examples](#usage-examples)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   K8s-Aware RAG Agent                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐ │
│  │   FastAPI    │───▶│   Qdrant     │    │  Kubernetes │ │
│  │    Server    │    │  Vector DB   │    │   Cluster   │ │
│  └──────┬───────┘    └──────────────┘    └──────┬──────┘ │
│         │                                         │        │
│         │            ┌──────────────┐            │        │
│         └───────────▶│    Ollama    │            │        │
│                      │  (LLM/Embed) │            │        │
│                      └──────────────┘            │        │
│                                                   │        │
│         RAG Queries ◄─────────┬─────────────────┘        │
│                               │                           │
│         K8s Metrics ◄─────────┘                          │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Components

1. **LLM Agent** (`src/main.py`): Basic RAG implementation with FastAPI
2. **Unified Server** (`src/unified_server.py`): Combined RAG + K8s metrics server
3. **MCP Server** (`src/k8s_mcp_server.py`): Standalone K8s metrics via MCP protocol
4. **Examples** (`examples/k8s_rag_example.py`): Cluster-aware RAG query examples

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional for local development)
- Kubernetes cluster (Minikube, Kind, or cloud provider)
- kubectl configured
- Metrics Server installed in your K8s cluster

### 1. Clone and Install

```bash
git clone https://github.com/Jonsy13/ollama-k8s-rag.git
cd ollama-k8s-rag

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Locally (Basic Agent)

```bash
# Start Ollama (in separate terminal)
ollama serve

# Pull required models
ollama pull tinyllama
ollama pull all-minilm

# Start Qdrant (Docker)
docker run -d -p 6333:6333 qdrant/qdrant

# Run the agent
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Ingest a document
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "Kubernetes is a container orchestration platform.", "metadata": {"topic": "k8s"}}'

# Query the RAG system
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is Kubernetes?", "top_k": 3}'
```

---

## 📦 Installation

### Option 1: Local Development

```bash
# Install Python dependencies
pip install -r requirements.txt

# Set environment variables (optional)
export OLLAMA_URL="http://localhost:11434/api/generate"
export QDRANT_URL="http://localhost:6333"
```

### Option 2: Docker Compose

```bash
# Coming soon - docker-compose.yml for local stack
docker-compose up -d
```

### Option 3: Kubernetes Deployment

See [Deployment Options](#deployment-options) below.

---

## 🎯 Deployment Options

### Option 1: Unified Server (Recommended)

**Best for**: Production deployments where RAG needs cluster context

```bash
# Apply RBAC
kubectl apply -f k8s/k8s-mcp-rbac.yaml

# Deploy the stack
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/vectorDB.yaml
kubectl apply -f k8s/ollama.yaml
kubectl apply -f k8s/llm-agent.yaml

# Test the deployment
kubectl port-forward -n llm-chaos svc/llm-agent 8000:8000
curl http://localhost:8000/k8s/cluster/cpu
```

### Option 2: MCP Server for Claude Desktop

**Best for**: Using Claude Desktop to query your cluster

```bash
# Run locally
python src/k8s_mcp_server.py

# Configure Claude Desktop
# Edit: ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "k8s-cluster": {
      "command": "python",
      "args": ["/path/to/src/k8s_mcp_server.py"]
    }
  }
}
```

### Option 3: Sidecar Container

**Best for**: Separate concerns with shared pod lifecycle

```bash
kubectl apply -f k8s/llm-agent-with-mcp.yaml
```

### Option 4: Separate Deployments

**Best for**: Independent scaling of services

```bash
kubectl apply -f k8s/k8s-mcp-server.yaml
kubectl apply -f k8s/llm-agent.yaml
```

📖 **Detailed deployment instructions**: See [docs/DEPLOYMENT_STEPS.md](docs/DEPLOYMENT_STEPS.md)

---

## 💡 Usage Examples

### Basic RAG Query

```python
import httpx
import asyncio

async def query_agent():
    client = httpx.AsyncClient()
    response = await client.post(
        "http://localhost:8000/query",
        json={"prompt": "Explain Python programming", "top_k": 3}
    )
    result = response.json()
    print(result["response"])

asyncio.run(query_agent())
```

### Cluster-Aware RAG Query

```python
from examples.k8s_rag_example import enhanced_rag_query
import asyncio

async def main():
    # Automatically includes K8s metrics when relevant
    result = await enhanced_rag_query(
        "What's my cluster CPU usage right now?"
    )
    print(result["context"])

asyncio.run(main())
```

### Get Cluster Metrics

```bash
# CPU usage
curl http://localhost:8000/k8s/cluster/cpu

# Memory usage
curl http://localhost:8000/k8s/cluster/memory

# List pods
curl http://localhost:8000/k8s/pods?namespace=default

# Cluster info
curl http://localhost:8000/k8s/cluster/info
```

### Run Example Script

```bash
# Demo cluster-aware queries
python examples/k8s_rag_example.py 1

# Ingest cluster documentation
python examples/k8s_rag_example.py 2

# Single custom query
python examples/k8s_rag_example.py 3
```

---

## 📚 API Reference

### RAG Endpoints

#### `POST /ingest`
Ingest a document into the vector database.

**Request Body:**
```json
{
  "text": "Your document text here",
  "metadata": {
    "category": "programming",
    "topic": "python"
  }
}
```

**Response:**
```json
{
  "message": "Document ingested",
  "id": "uuid-here",
  "text_length": 150
}
```

#### `POST /query`
Query the RAG system.

**Request Body:**
```json
{
  "prompt": "What is Kubernetes?",
  "top_k": 3
}
```

**Response:**
```json
{
  "query": "What is Kubernetes?",
  "matches": [...],
  "response": "Kubernetes is..."
}
```

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "k8s_enabled": true
}
```

### Kubernetes Endpoints

#### `GET /k8s/cluster/cpu`
Get cluster-wide CPU usage.

**Response:**
```json
{
  "cluster_cpu": {
    "total_usage_cores": 2.5,
    "total_capacity_cores": 8.0,
    "utilization_percent": 31.25
  },
  "nodes": [...]
}
```

#### `GET /k8s/cluster/memory`
Get cluster-wide memory usage.

**Response:**
```json
{
  "cluster_memory": {
    "total_usage_gi": 4.2,
    "total_capacity_gi": 16.0,
    "utilization_percent": 26.25
  },
  "nodes": [...]
}
```

#### `GET /k8s/pods`
List pods with optional filtering.

**Query Parameters:**
- `namespace` (string): Namespace to query (default: "all")
- `label_selector` (string): Label selector (e.g., "app=nginx")

**Response:**
```json
{
  "count": 5,
  "pods": [
    {
      "name": "pod-name",
      "namespace": "default",
      "status": "Running",
      "node": "node-1",
      "ip": "10.244.0.5"
    }
  ]
}
```

#### `GET /k8s/cluster/info`
Get general cluster information.

**Response:**
```json
{
  "version": "v1.28.0",
  "nodes_count": 3,
  "namespaces_count": 12,
  "k8s_enabled": true
}
```

---

## 📁 Project Structure

```
k8s-rag-agent/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── Dockerfile               # Container image definition
├── .gitignore              # Git ignore rules
│
├── src/                    # Source code
│   ├── __init__.py
│   ├── main.py            # Basic RAG agent
│   ├── unified_server.py  # Unified RAG + K8s server
│   └── k8s_mcp_server.py  # Standalone MCP server
│
├── examples/              # Usage examples
│   └── k8s_rag_example.py # Cluster-aware RAG demo
│
├── k8s/                   # Kubernetes manifests
│   ├── namespace.yaml     # llm-chaos namespace
│   ├── pvc.yaml          # Persistent volume claims
│   ├── vectorDB.yaml     # Qdrant deployment
│   ├── ollama.yaml       # Ollama deployment
│   ├── llm-agent.yaml    # LLM agent deployment
│   ├── k8s-mcp-rbac.yaml # RBAC permissions
│   ├── k8s-mcp-server.yaml      # Standalone MCP server
│   └── llm-agent-with-mcp.yaml  # Agent + MCP sidecar
│
└── docs/                  # Documentation
    └── DEPLOYMENT_STEPS.md # Detailed deployment guide
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_URL` | `http://ollama:11434/api/generate` | Ollama generation endpoint |
| `OLLAMA_EMBED_URL` | `http://ollama:11434/api/embeddings` | Ollama embeddings endpoint |
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant vector database URL |
| `COLLECTION_NAME` | `rag_memory` | Qdrant collection name |

### Kubernetes RBAC

The agent requires the following permissions:
- `get`, `list`, `watch` on nodes
- `get`, `list`, `watch` on pods (all namespaces)
- Access to metrics.k8s.io API group

See `k8s/k8s-mcp-rbac.yaml` for full RBAC configuration.

### Ollama Models

Required models:
- **tinyllama**: LLM for text generation
- **all-minilm**: Embedding model (384 dimensions)

```bash
ollama pull tinyllama
ollama pull all-minilm
```

---

## 🧪 Testing

### Run Tests

```bash
# Unit tests
pytest tests/

# Integration tests
kubectl port-forward -n llm-chaos svc/llm-agent 8000:8000
python examples/k8s_rag_example.py 1
```

### Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n llm-chaos

# Check services
kubectl get svc -n llm-chaos

# Test health endpoint
kubectl port-forward -n llm-chaos svc/llm-agent 8000:8000
curl http://localhost:8000/health

# Test K8s integration
curl http://localhost:8000/k8s/cluster/info
```

---

## 🐛 Troubleshooting

### "Kubernetes client not initialized"

**Cause**: RBAC not configured or kubeconfig missing

**Fix**:
```bash
kubectl apply -f k8s/k8s-mcp-rbac.yaml
kubectl rollout restart deployment/llm-agent -n llm-chaos
```

### "Metrics server not available"

**Cause**: Metrics server not installed in cluster

**Fix**:
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl wait --for=condition=available --timeout=60s deployment/metrics-server -n kube-system
```

### Ollama connection errors

**Cause**: Ollama service not ready or wrong URL

**Fix**:
```bash
# Check Ollama pod
kubectl get pods -n llm-chaos -l app=ollama

# Check logs
kubectl logs -n llm-chaos -l app=ollama

# Verify models are loaded
kubectl exec -n llm-chaos -it <ollama-pod> -- ollama list
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run linters
black src/ examples/
flake8 src/ examples/
mypy src/

# Run tests
pytest tests/ -v
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Ollama](https://ollama.ai/) - Local LLM inference
- [Qdrant](https://qdrant.tech/) - Vector database
- [Kubernetes](https://kubernetes.io/) - Container orchestration
- [MCP Protocol](https://github.com/anthropics/mcp) - Model Context Protocol

---

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

---

**Built with ❤️ for the Kubernetes and AI community**
