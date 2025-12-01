"""
Example: Using K8s metrics in RAG context

This shows how to enhance your LLM agent with cluster awareness.
The agent can answer questions about both your documents AND your cluster state.
"""

import httpx
import asyncio
from typing import List, Dict


async def enhanced_rag_query(prompt: str, agent_url: str = "http://localhost:8000"):
    """
    Enhanced RAG query that includes cluster context.

    Example prompts:
    - "Which pods are using the most CPU in my cluster?"
    - "Should I scale up based on current memory usage?"
    - "What's the health status of my cluster?"
    """

    client = httpx.AsyncClient(timeout=60)

    # Step 1: Get relevant documents from vector DB
    print(f"🔍 Querying vector DB for: {prompt}")
    rag_response = await client.post(
        f"{agent_url}/query",
        json={"prompt": prompt, "top_k": 3}
    )
    doc_matches = rag_response.json().get("matches", [])
    print(f"✓ Found {len(doc_matches)} relevant documents")

    # Step 2: Check if query is cluster-related
    cluster_keywords = ["cpu", "memory", "pod",
                        "node", "cluster", "resource", "usage"]
    is_cluster_query = any(keyword in prompt.lower()
                           for keyword in cluster_keywords)

    cluster_context = ""
    if is_cluster_query:
        print("🎯 Detected cluster query, fetching K8s metrics...")

        # Get cluster metrics
        try:
            cpu_resp = await client.get(f"{agent_url}/k8s/cluster/cpu")
            memory_resp = await client.get(f"{agent_url}/k8s/cluster/memory")
            info_resp = await client.get(f"{agent_url}/k8s/cluster/info")
            pods_resp = await client.get(f"{agent_url}/k8s/pods?namespace=all")

            cpu_data = cpu_resp.json()
            memory_data = memory_resp.json()
            info_data = info_resp.json()
            pods_data = pods_resp.json()

            # Build cluster context
            cluster_context = f"""
CURRENT CLUSTER STATE:
- Kubernetes Version: {info_data.get('version', 'N/A')}
- Total Nodes: {info_data.get('nodes_count', 'N/A')}
- Total Pods: {pods_data.get('count', 'N/A')}

CPU USAGE:
- Total Usage: {cpu_data['cluster_cpu']['total_usage_cores']} cores
- Total Capacity: {cpu_data['cluster_cpu']['total_capacity_cores']} cores
- Utilization: {cpu_data['cluster_cpu']['utilization_percent']}%

MEMORY USAGE:
- Total Usage: {memory_data['cluster_memory']['total_usage_gi']} GiB
- Total Capacity: {memory_data['cluster_memory']['total_capacity_gi']} GiB
- Utilization: {memory_data['cluster_memory']['utilization_percent']}%

NODE DETAILS:
"""
            for node in cpu_data['nodes'][:3]:  # Show top 3 nodes
                cluster_context += f"- {node['node']}: CPU {node['utilization_percent']}%\n"

            print("✓ Fetched cluster metrics")

        except Exception as e:
            print(f"⚠ Could not fetch cluster metrics: {e}")
            cluster_context = "Cluster metrics unavailable."

    # Step 3: Build enhanced context
    doc_context = "\n".join([
        f"- {match['payload'].get('text', '')}"
        for match in doc_matches
    ])

    full_context = f"""
You are an intelligent assistant with access to both documentation and live cluster metrics.

RELEVANT DOCUMENTATION:
{doc_context}

{cluster_context}

USER QUERY:
{prompt}

Please provide a comprehensive answer using both the documentation and cluster state.
"""

    print("\n📝 Enhanced Context:")
    print("=" * 60)
    print(full_context)
    print("=" * 60)

    # Step 4: Get LLM response (you would send to your LLM)
    # For demo, we'll just return the context
    return {
        "query": prompt,
        "cluster_aware": is_cluster_query,
        "context": full_context,
        "doc_matches": len(doc_matches),
        "cluster_metrics_included": bool(cluster_context and cluster_context != "Cluster metrics unavailable.")
    }


async def demo_queries():
    """Run demo queries showing cluster-aware RAG."""

    agent_url = "http://localhost:8000"

    queries = [
        "What is Kubernetes?",  # Regular RAG query
        "What's my cluster CPU usage right now?",  # Cluster-specific
        "Should I scale up my pods based on current resource usage?",  # Combined
        "Explain Python programming",  # Regular RAG query
    ]

    print("🚀 Enhanced RAG Demo - Cluster-Aware Queries\n")

    for i, query in enumerate(queries, 1):
        print(f"\n{'='*70}")
        print(f"Query {i}: {query}")
        print('='*70)

        try:
            result = await enhanced_rag_query(query, agent_url)

            print(f"\n✓ Results:")
            print(f"  - Cluster-aware: {result['cluster_aware']}")
            print(f"  - Doc matches: {result['doc_matches']}")
            print(f"  - K8s metrics: {result['cluster_metrics_included']}")

        except Exception as e:
            print(f"❌ Error: {e}")

        if i < len(queries):
            await asyncio.sleep(1)  # Brief pause between queries


async def ingest_cluster_docs():
    """
    Example: Ingest cluster-related documentation.
    This makes your RAG system more aware of K8s concepts.
    """

    agent_url = "http://localhost:8000"
    client = httpx.AsyncClient(timeout=60)

    cluster_docs = [
        {
            "text": "High CPU usage above 80% typically indicates need for horizontal pod autoscaling or node expansion.",
            "metadata": {"category": "cluster", "topic": "scaling"}
        },
        {
            "text": "Memory pressure on nodes can cause pod evictions. Monitor memory utilization and set appropriate resource limits.",
            "metadata": {"category": "cluster", "topic": "resources"}
        },
        {
            "text": "Kubernetes metrics-server provides real-time resource usage data for nodes and pods.",
            "metadata": {"category": "cluster", "topic": "monitoring"}
        },
    ]

    print("📚 Ingesting cluster documentation...")

    for doc in cluster_docs:
        try:
            response = await client.post(
                f"{agent_url}/ingest",
                json=doc
            )
            result = response.json()
            print(f"✓ Ingested: {doc['text'][:50]}... (ID: {result['id']})")
        except Exception as e:
            print(f"❌ Failed to ingest: {e}")

    print("\n✓ Documentation ingested successfully!")


# ============================================
# USAGE EXAMPLES
# ============================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║           K8s-Aware RAG System Demo                          ║
║                                                              ║
║  This demonstrates how to combine:                          ║
║  1. Vector DB document retrieval (RAG)                      ║
║  2. Live Kubernetes cluster metrics                         ║
║  3. LLM generation                                          ║
║                                                              ║
║  Prerequisites:                                              ║
║  - Unified server running on localhost:8000                 ║
║  - K8s cluster with metrics-server                          ║
╚══════════════════════════════════════════════════════════════╝
    """)

    print("\nChoose an option:")
    print("1. Run demo queries (shows cluster-aware RAG)")
    print("2. Ingest cluster documentation")
    print("3. Run single query")

    import sys
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\nEnter choice (1-3): ").strip()

    if choice == "1":
        asyncio.run(demo_queries())
    elif choice == "2":
        asyncio.run(ingest_cluster_docs())
    elif choice == "3":
        query = input("Enter your query: ").strip()
        result = asyncio.run(enhanced_rag_query(query))
        print("\n✓ Query processed!")
    else:
        print("Invalid choice. Run with: python k8s_rag_example.py [1|2|3]")


# ============================================
# PRACTICAL USE CASES
# ============================================

"""
USE CASE 1: Cluster Health Assistant
Query: "Is my cluster healthy?"
Response: Uses K8s metrics + docs about health indicators

USE CASE 2: Resource Optimization
Query: "Should I scale up my deployment?"
Response: Analyzes current CPU/memory + scaling best practices from docs

USE CASE 3: Troubleshooting
Query: "Why are my pods crashing?"
Response: Checks pod status + retrieves troubleshooting docs

USE CASE 4: Cost Optimization
Query: "Am I over-provisioning resources?"
Response: Compares usage vs capacity + retrieves cost optimization docs

USE CASE 5: Capacity Planning
Query: "Can I deploy 10 more pods?"
Response: Analyzes available resources + retrieves capacity planning docs
"""
