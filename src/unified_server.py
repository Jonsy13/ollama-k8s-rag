"""
Unified server combining FastAPI LLM Agent with K8s MCP capabilities.
This exposes both RAG endpoints and K8s cluster query tools via FastAPI.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
import uuid
import asyncio
from typing import Optional, Dict, Any
from kubernetes import client, config
from kubernetes.client.rest import ApiException

app = FastAPI(title="LLM Agent with K8s Integration")

# Existing LLM Agent config
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")
EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://ollama:11434/api/embeddings")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION_NAME = "rag_memory"

http_client = httpx.AsyncClient(timeout=120)

# K8s client initialization
k8s_enabled = False
try:
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()

    v1 = client.CoreV1Api()
    metrics_api = client.CustomObjectsApi()
    k8s_enabled = True
    print("✓ Kubernetes client initialized")
except Exception as e:
    print(f"⚠ K8s client not available: {e}")
    v1 = None
    metrics_api = None

# Sample documents (from original main.py)
SAMPLE_DOCUMENTS = [
    {
        "text": "Python is a high-level, interpreted programming language known for its simplicity and readability.",
        "metadata": {"category": "programming", "topic": "python"}
    },
    {
        "text": "Kubernetes is an open-source container orchestration platform that automates deploying, scaling, and managing containerized applications.",
        "metadata": {"category": "devops", "topic": "kubernetes"}
    },
    {
        "text": "FastAPI is a modern, fast web framework for building APIs with Python based on standard Python type hints.",
        "metadata": {"category": "programming", "topic": "fastapi"}
    },
]


@app.on_event("startup")
async def startup_event():
    """Initialize collection and ingest sample data on startup."""
    print("🚀 Starting unified LLM Agent + K8s server...")

    # Wait for dependencies and initialize (same as original main.py)
    try:
        max_retries = 30
        for i in range(max_retries):
            try:
                r = await http_client.get(f"{QDRANT_URL}/collections")
                if r.status_code == 200:
                    print("✓ Qdrant is ready")
                    break
            except:
                if i < max_retries - 1:
                    print(f"Waiting for Qdrant... ({i+1}/{max_retries})")
                    await asyncio.sleep(2)

        # Initialize collection if needed (abbreviated - see main.py for full logic)
        print("✓ Startup complete!")
    except Exception as e:
        print(f"⚠ Startup initialization warning: {e}")


# ============================================
# EXISTING LLM AGENT ENDPOINTS
# ============================================

class Query(BaseModel):
    prompt: str
    top_k: int = 3


class Document(BaseModel):
    text: str
    metadata: dict = {}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "k8s_enabled": k8s_enabled
    }


@app.post("/ingest")
async def ingest(doc: Document):
    """Ingest a document into the vector database."""
    try:
        vector = await embed_text(doc.text)
        point_id = str(uuid.uuid4())
        payload = {
            "points": [{
                "id": point_id,
                "vector": vector,
                "payload": {"text": doc.text, **doc.metadata}
            }]
        }
        r = await http_client.put(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points",
            json=payload
        )
        r.raise_for_status()
        return {
            "message": "Document ingested",
            "id": point_id,
            "text_length": len(doc.text)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def query(data: Query):
    """RAG query endpoint."""
    try:
        vector = await embed_text(data.prompt)
        matches = await qdrant_search(vector, data.top_k)
        rag_prompt = build_rag_prompt(data.prompt, matches)
        answer = await llm_generate(rag_prompt)

        return {
            "query": data.prompt,
            "matches": matches,
            "response": answer
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# NEW K8S ENDPOINTS
# ============================================

@app.get("/k8s/cluster/cpu")
async def get_cluster_cpu():
    """Get cluster-wide CPU usage."""
    if not k8s_enabled:
        raise HTTPException(status_code=503, detail="K8s client not available")

    try:
        nodes_metrics = metrics_api.list_cluster_custom_object(
            group="metrics.k8s.io", version="v1beta1", plural="nodes"
        )

        total_usage = 0
        total_capacity = 0
        nodes = v1.list_node()
        node_capacities = {
            node.metadata.name: node.status.capacity for node in nodes.items}

        node_details = []
        for item in nodes_metrics.get('items', []):
            node_name = item['metadata']['name']
            usage = parse_quantity(item['usage']['cpu'])
            capacity = parse_quantity(
                node_capacities.get(node_name, {}).get('cpu', '0'))

            total_usage += usage
            total_capacity += capacity

            node_details.append({
                "node": node_name,
                "usage_cores": round(usage, 3),
                "capacity_cores": round(capacity, 3),
                "utilization_percent": round((usage / capacity * 100) if capacity > 0 else 0, 2)
            })

        return {
            "cluster_cpu": {
                "total_usage_cores": round(total_usage, 3),
                "total_capacity_cores": round(total_capacity, 3),
                "utilization_percent": round((total_usage / total_capacity * 100) if total_capacity > 0 else 0, 2)
            },
            "nodes": node_details
        }
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(
                status_code=404, detail="Metrics server not available")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/k8s/cluster/memory")
async def get_cluster_memory():
    """Get cluster-wide memory usage."""
    if not k8s_enabled:
        raise HTTPException(status_code=503, detail="K8s client not available")

    try:
        nodes_metrics = metrics_api.list_cluster_custom_object(
            group="metrics.k8s.io", version="v1beta1", plural="nodes"
        )

        total_usage = 0
        total_capacity = 0
        nodes = v1.list_node()
        node_capacities = {
            node.metadata.name: node.status.capacity for node in nodes.items}

        node_details = []
        for item in nodes_metrics.get('items', []):
            node_name = item['metadata']['name']
            usage_bytes = parse_quantity(item['usage']['memory'])
            capacity_bytes = parse_quantity(
                node_capacities.get(node_name, {}).get('memory', '0'))

            total_usage += usage_bytes
            total_capacity += capacity_bytes

            node_details.append({
                "node": node_name,
                "usage_gi": round(usage_bytes / (1024**3), 2),
                "capacity_gi": round(capacity_bytes / (1024**3), 2),
                "utilization_percent": round((usage_bytes / capacity_bytes * 100) if capacity_bytes > 0 else 0, 2)
            })

        return {
            "cluster_memory": {
                "total_usage_gi": round(total_usage / (1024**3), 2),
                "total_capacity_gi": round(total_capacity / (1024**3), 2),
                "utilization_percent": round((total_usage / total_capacity * 100) if total_capacity > 0 else 0, 2)
            },
            "nodes": node_details
        }
    except ApiException as e:
        if e.status == 404:
            raise HTTPException(
                status_code=404, detail="Metrics server not available")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/k8s/pods")
async def get_pods(namespace: str = "all", label_selector: str = ""):
    """List pods with optional filtering."""
    if not k8s_enabled:
        raise HTTPException(status_code=503, detail="K8s client not available")

    try:
        if namespace == "all":
            pods = v1.list_pod_for_all_namespaces(
                label_selector=label_selector) if label_selector else v1.list_pod_for_all_namespaces()
        else:
            pods = v1.list_namespaced_pod(
                namespace, label_selector=label_selector) if label_selector else v1.list_namespaced_pod(namespace)

        result = []
        for pod in pods.items:
            result.append({
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "node": pod.spec.node_name,
                "ip": pod.status.pod_ip,
            })

        return {"count": len(result), "pods": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/k8s/cluster/info")
async def get_cluster_info():
    """Get general cluster information."""
    if not k8s_enabled:
        raise HTTPException(status_code=503, detail="K8s client not available")

    try:
        version_info = client.VersionApi().get_code()
        nodes = v1.list_node()
        namespaces = v1.list_namespace()

        return {
            "version": version_info.git_version,
            "nodes_count": len(nodes.items),
            "namespaces_count": len(namespaces.items),
            "k8s_enabled": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# HELPER FUNCTIONS
# ============================================

async def embed_text(text: str):
    """Generate embeddings from Ollama."""
    payload = {"model": "all-minilm", "prompt": text}
    r = await http_client.post(EMBED_URL, json=payload)
    r.raise_for_status()
    response_data = r.json()
    embedding = response_data.get(
        "embedding", response_data.get("embeddings", []))
    if not embedding:
        raise HTTPException(status_code=500, detail="Empty embedding returned")
    return embedding


async def qdrant_search(vector, top_k: int):
    payload = {"vector": vector, "limit": top_k, "with_payload": True}
    try:
        r = await http_client.post(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search", json=payload)
        r.raise_for_status()
        return r.json()["result"]
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=500, detail=f"Qdrant error: {e.response.text}")


async def llm_generate(prompt: str):
    payload = {"model": "tinyllama", "prompt": prompt, "stream": False}
    r = await http_client.post(OLLAMA_URL, json=payload)
    r.raise_for_status()
    return r.json()["response"]


def build_rag_prompt(query, matches):
    context = "\n".join([m["payload"].get("text", "") for m in matches])
    return f"""Use the context below to answer the user query.

Context:
{context}

User Query:
{query}

Answer:"""


def parse_quantity(quantity_str):
    """Parse Kubernetes quantity string to numeric value."""
    if not quantity_str:
        return 0

    if quantity_str.endswith('m'):
        return float(quantity_str[:-1]) / 1000
    elif quantity_str.endswith('n'):
        return float(quantity_str[:-1]) / 1_000_000_000

    units = {'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3, 'Ti': 1024**4,
             'K': 1000, 'M': 1000**2, 'G': 1000**3, 'T': 1000**4}

    for suffix, multiplier in units.items():
        if quantity_str.endswith(suffix):
            return float(quantity_str[:-len(suffix)]) * multiplier

    return float(quantity_str)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
