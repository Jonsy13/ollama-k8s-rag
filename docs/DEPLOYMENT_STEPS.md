# Step-by-Step Deployment Guide

## Quick Decision Matrix

| Use Case | Option | File to Use |
|----------|--------|-------------|
| Claude Desktop queries cluster | External | Run `python k8s_mcp_server.py` locally |
| LLM Agent needs cluster context | Unified | Deploy `unified_server.py` |
| Keep services separate | Sidecar | Use `k8s/llm-agent-with-mcp.yaml` |
| Standalone MCP service | Separate | Use `k8s/k8s-mcp-server.yaml` |

---

## Option 1: External MCP Server (Easiest - For Claude Desktop)

**Best for:** Using Claude Desktop to query your cluster

### Steps:

1. **Ensure cluster access:**
   ```bash
   kubectl cluster-info
   kubectl top nodes  # Verify metrics-server
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the MCP server:**
   ```bash
   python src/k8s_mcp_server.py
   ```

4. **Configure Claude Desktop:**
   
   Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "k8s-cluster": {
         "command": "python",
         "args": ["/path/to/k8s-rag-agent/src/k8s_mcp_server.py"]
       }
     }
   }
   ```

5. **Restart Claude Desktop**

6. **Test it:**
   In Claude, ask: "What's my cluster CPU usage?"

---

## Option 2: Unified Server (Recommended - Single Deployment)

**Best for:** Your LLM agent needs cluster metrics in RAG context

### Steps:

1. **Update Dockerfile:**
   ```dockerfile
   # The Dockerfile already copies src/ directory
   # Just update CMD to:
   CMD ["uvicorn", "src.unified_server:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Rebuild and push image:**
   ```bash
   docker build -t your-registry/llm-agent-unified:latest .
   docker push your-registry/llm-agent-unified:latest
   ```

3. **Apply RBAC:**
   ```bash
   kubectl apply -f k8s/k8s-mcp-rbac.yaml
   ```

4. **Update deployment:**
   
   Edit `k8s/llm-agent.yaml` to use the new image and add serviceAccount:
   ```yaml
   spec:
     serviceAccountName: llm-agent-sa
     containers:
     - name: agent
       image: your-registry/llm-agent-unified:latest
   ```

5. **Deploy:**
   ```bash
   kubectl apply -f k8s/llm-agent.yaml
   ```

6. **Test endpoints:**
   ```bash
   # Port forward
   kubectl port-forward -n llm-chaos svc/llm-agent 8000:8000
   
   # Test RAG (existing)
   curl http://localhost:8000/health
   
   # Test K8s endpoints (new)
   curl http://localhost:8000/k8s/cluster/cpu
   curl http://localhost:8000/k8s/cluster/memory
   curl http://localhost:8000/k8s/pods
   curl http://localhost:8000/k8s/cluster/info
   ```

7. **Use in your LLM queries:**
   Your agent can now include cluster metrics in RAG context!
   
   Example: Query "What's consuming resources in my cluster?" will:
   - Fetch cluster metrics via K8s endpoints
   - Include in RAG context
   - Generate informed response

---

## Option 3: Sidecar Container

**Best for:** Separate concerns, shared pod lifecycle

### Steps:

1. **Update Dockerfile (same as Option 2):**
   ```dockerfile
   # Dockerfile already copies src/ directory
   # No changes needed
   ```

2. **Rebuild image:**
   ```bash
   docker build -t your-registry/llm-agent:latest .
   docker push your-registry/llm-agent:latest
   ```

3. **Apply RBAC:**
   ```bash
   kubectl apply -f k8s/k8s-mcp-rbac.yaml
   ```

4. **Deploy with sidecar:**
   ```bash
   kubectl apply -f k8s/llm-agent-with-mcp.yaml
   ```

5. **Verify both containers:**
   ```bash
   kubectl get pods -n llm-chaos
   kubectl logs -n llm-chaos <pod-name> -c agent
   kubectl logs -n llm-chaos <pod-name> -c mcp-server
   ```

6. **Access both services:**
   ```bash
   kubectl port-forward -n llm-chaos svc/llm-agent 8000:8000
   # Main agent: http://localhost:8000
   # MCP server: http://localhost:9000 (if exposed)
   ```

---

## Option 4: Separate Deployment

**Best for:** Independent scaling, multiple clients

### Steps:

1. **Apply RBAC:**
   ```bash
   kubectl apply -f k8s/k8s-mcp-rbac.yaml
   ```

2. **Deploy MCP server:**
   ```bash
   kubectl apply -f k8s/k8s-mcp-server.yaml
   ```

3. **Keep existing LLM agent:**
   ```bash
   kubectl apply -f k8s/llm-agent.yaml
   ```

4. **Verify deployment:**
   ```bash
   kubectl get pods -n llm-chaos
   kubectl get svc -n llm-chaos
   ```

5. **Access MCP server from within cluster:**
   ```bash
   # From another pod
   curl http://k8s-mcp-server.llm-chaos.svc.cluster.local:9000
   ```

---

## Common Post-Deployment Tasks

### 1. Verify Metrics Server

```bash
kubectl top nodes
kubectl top pods -n llm-chaos
```

If metrics aren't available:
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### 2. Check RBAC Permissions

```bash
# Test as service account
kubectl auth can-i list nodes --as=system:serviceaccount:llm-chaos:llm-agent-sa
kubectl auth can-i list pods --as=system:serviceaccount:llm-chaos:llm-agent-sa --all-namespaces
```

### 3. View Logs

```bash
# For unified or sidecar
kubectl logs -n llm-chaos -l app=llm-agent --tail=50 -f

# For separate deployment
kubectl logs -n llm-chaos -l app=k8s-mcp-server --tail=50 -f
```

### 4. Test Endpoints

```bash
# Port forward
kubectl port-forward -n llm-chaos svc/llm-agent 8000:8000

# Test in another terminal
curl http://localhost:8000/health
curl http://localhost:8000/k8s/cluster/info
```

---

## Troubleshooting

### Issue: "Kubernetes client not initialized"

**Cause:** RBAC not configured or kubeconfig missing

**Fix:**
```bash
kubectl apply -f k8s/k8s-mcp-rbac.yaml
kubectl rollout restart deployment/llm-agent -n llm-chaos
```

### Issue: "Metrics server not available"

**Cause:** Metrics server not installed

**Fix:**
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl wait --for=condition=available --timeout=60s deployment/metrics-server -n kube-system
```

### Issue: MCP server can't reach FastAPI agent

**Cause:** Network policy or wrong service URL

**Fix:**
```bash
# For sidecar: use localhost
# For separate deployment: use service DNS
# Example: http://llm-agent.llm-chaos.svc.cluster.local:8000
```

### Issue: Permission denied errors

**Cause:** Service account doesn't have proper RBAC

**Fix:**
```bash
# Check what's denied
kubectl logs -n llm-chaos <pod-name> | grep -i forbidden

# Verify RBAC is applied
kubectl get clusterrolebinding llm-agent-k8s-mcp-reader -o yaml

# Ensure pod uses correct service account
kubectl get pod -n llm-chaos <pod-name> -o jsonpath='{.spec.serviceAccountName}'
```

---

## Next Steps After Deployment

1. **Integrate with your workflows:**
   - Use K8s metrics in RAG queries
   - Set up alerts based on resource usage
   - Create cluster health dashboards

2. **Extend functionality:**
   - Add more K8s resources (Services, Ingress, etc.)
   - Implement write operations (with caution!)
   - Add custom metrics

3. **Security hardening:**
   - Use NetworkPolicies to restrict access
   - Implement authentication for external access
   - Rotate service account tokens regularly

4. **Monitoring:**
   - Add Prometheus metrics
   - Set up alerting
   - Track API usage

## Testing Your Integration

### Test Script

```bash
#!/bin/bash
# test_integration.sh

echo "Testing LLM Agent + K8s Integration..."

# Test basic health
echo "1. Health check..."
curl -s http://localhost:8000/health | jq

# Test K8s cluster info
echo "2. Cluster info..."
curl -s http://localhost:8000/k8s/cluster/info | jq

# Test CPU metrics
echo "3. Cluster CPU..."
curl -s http://localhost:8000/k8s/cluster/cpu | jq

# Test memory metrics
echo "4. Cluster memory..."
curl -s http://localhost:8000/k8s/cluster/memory | jq

# Test pods listing
echo "5. List pods..."
curl -s "http://localhost:8000/k8s/pods?namespace=llm-chaos" | jq

echo "All tests complete!"
```

Make it executable and run:
```bash
chmod +x test_integration.sh
kubectl port-forward -n llm-chaos svc/llm-agent 8000:8000 &
./test_integration.sh
```
