from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
import uuid
import asyncio

app = FastAPI(title="LLM Agent")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")
EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://ollama:11434/api/embeddings")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION_NAME = "rag_memory"

client = httpx.AsyncClient(timeout=120)

# Sample documents to ingest on startup
SAMPLE_DOCUMENTS = [
    {
        "text": "Python is a high-level, interpreted programming language known for its simplicity and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
        "metadata": {"category": "programming", "topic": "python"}
    },
    {
        "text": "Kubernetes is an open-source container orchestration platform that automates deploying, scaling, and managing containerized applications. It was originally designed by Google.",
        "metadata": {"category": "devops", "topic": "kubernetes"}
    },
    {
        "text": "FastAPI is a modern, fast web framework for building APIs with Python based on standard Python type hints. It provides automatic API documentation and data validation.",
        "metadata": {"category": "programming", "topic": "fastapi"}
    },
    {
        "text": "Vector databases store and retrieve high-dimensional vectors efficiently. They are essential for semantic search, recommendation systems, and RAG applications.",
        "metadata": {"category": "database", "topic": "vector-db"}
    },
    {
        "text": "RAG (Retrieval Augmented Generation) combines information retrieval with language models to provide more accurate and contextual responses by grounding answers in retrieved documents.",
        "metadata": {"category": "ai", "topic": "rag"}
    }
]


@app.on_event("startup")
async def startup_event():
    """Initialize collection and ingest sample data on startup."""
    print("🚀 Starting up LLM Agent...")

    try:
        # Wait for Qdrant to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                r = await client.get(f"{QDRANT_URL}/collections")
                if r.status_code == 200:
                    print("✓ Qdrant is ready")
                    break
            except:
                if i < max_retries - 1:
                    print(f"Waiting for Qdrant... ({i+1}/{max_retries})")
                    await asyncio.sleep(2)
                else:
                    print("⚠ Qdrant not ready, skipping initialization")
                    return

        # Wait for Ollama to be ready
        for i in range(max_retries):
            try:
                r = await client.get(f"http://ollama:11434/api/tags")
                if r.status_code == 200:
                    print("✓ Ollama is ready")
                    break
            except:
                if i < max_retries - 1:
                    print(f"Waiting for Ollama... ({i+1}/{max_retries})")
                    await asyncio.sleep(2)
                else:
                    print("⚠ Ollama not ready, skipping auto-ingestion")
                    return

        # Check if collection exists
        try:
            r = await client.get(f"{QDRANT_URL}/collections/{COLLECTION_NAME}")
            collection_exists = r.status_code == 200
        except:
            collection_exists = False

        if not collection_exists:
            print(f"Creating collection: {COLLECTION_NAME}")
            payload = {
                "vectors": {
                    "size": 384,
                    "distance": "Cosine"
                }
            }
            r = await client.put(f"{QDRANT_URL}/collections/{COLLECTION_NAME}", json=payload)
            r.raise_for_status()
            print(f"✓ Collection '{COLLECTION_NAME}' created")

            # Ingest sample documents
            print("Ingesting sample documents...")
            success_count = 0
            for idx, doc_data in enumerate(SAMPLE_DOCUMENTS):
                try:
                    vector = await embed_text(doc_data["text"])
                    point_id = str(uuid.uuid4())
                    payload = {
                        "points": [{
                            "id": point_id,
                            "vector": vector,
                            "payload": {
                                "text": doc_data["text"],
                                **doc_data["metadata"]
                            }
                        }]
                    }
                    r = await client.put(
                        f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points",
                        json=payload
                    )
                    r.raise_for_status()
                    success_count += 1
                    print(
                        f"  ✓ Ingested document {idx + 1}/{len(SAMPLE_DOCUMENTS)}")
                except Exception as e:
                    print(f"  ⚠ Failed to ingest document {idx + 1}: {e}")

            print(
                f"✓ Successfully ingested {success_count}/{len(SAMPLE_DOCUMENTS)} sample documents")
        else:
            print(f"✓ Collection '{COLLECTION_NAME}' already exists")

        print("✓ Startup complete!")

    except Exception as e:
        print(f"⚠ Startup initialization failed: {e}")


class Query(BaseModel):
    prompt: str
    top_k: int = 3


class Document(BaseModel):
    text: str
    metadata: dict = {}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    try:
        r = await client.get(f"{QDRANT_URL}/collections")
        if r.status_code != 200:
            raise Exception("Qdrant not ready")
        return {"ready": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
async def ingest(doc: Document):
    """Ingest a document into the vector database."""
    try:
        # Generate embedding for the text
        vector = await embed_text(doc.text)

        # Create point payload
        point_id = str(uuid.uuid4())
        payload = {
            "points": [
                {
                    "id": point_id,
                    "vector": vector,
                    "payload": {
                        "text": doc.text,
                        **doc.metadata
                    }
                }
            ]
        }

        # Insert into Qdrant
        r = await client.put(
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


async def embed_text(text: str):
    """Generate embeddings from Ollama."""
    payload = {"model": "all-minilm", "prompt": text}
    r = await client.post(EMBED_URL, json=payload)
    r.raise_for_status()
    response_data = r.json()
    print(f"DEBUG - Ollama response: {response_data}")
    print(f"DEBUG - Response keys: {response_data.keys()}")
    embedding = response_data.get(
        "embedding", response_data.get("embeddings", []))
    print(f"DEBUG - Embedding length: {len(embedding) if embedding else 0}")
    if not embedding:
        raise HTTPException(
            status_code=500, detail=f"Empty embedding returned. Full response: {response_data}")
    return embedding


async def qdrant_search(vector, top_k: int):
    payload = {
        "vector": vector,
        "limit": top_k,
        "with_payload": True
    }
    try:
        r = await client.post(f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search", json=payload)
        r.raise_for_status()
        return r.json()["result"]
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        raise HTTPException(
            status_code=500, detail=f"Qdrant error: {error_detail}")


async def llm_generate(prompt: str):
    payload = {
        "model": "tinyllama",
        "prompt": prompt,
        "stream": False
    }
    r = await client.post(OLLAMA_URL, json=payload)
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


@app.post("/query")
async def query(data: Query):
    try:
        # 1. Generate embeddings
        vector = await embed_text(data.prompt)

        # 2. Search in Qdrant
        matches = await qdrant_search(vector, data.top_k)

        # 3. Build RAG prompt
        rag_prompt = build_rag_prompt(data.prompt, matches)

        # 4. Generate answer from LLM
        answer = await llm_generate(rag_prompt)

        return {
            "query": data.prompt,
            "matches": matches,
            "response": answer
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
