import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Initialize K8s client
try:
    # Try to load in-cluster config first, then fall back to kubeconfig
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()

    v1 = client.CoreV1Api()
    metrics_api = client.CustomObjectsApi()
except Exception as e:
    print(f"Warning: Could not initialize Kubernetes client: {e}")
    v1 = None
    metrics_api = None

# Create MCP server instance
mcp_server = Server("k8s-cluster-mcp")


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List available K8s MCP tools."""
    return [
        Tool(
            name="get_cluster_cpu",
            description="Get CPU usage across all nodes in the cluster. Returns current CPU usage, capacity, and utilization percentage.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_cluster_memory",
            description="Get memory usage across all nodes in the cluster. Returns current memory usage, capacity, and utilization percentage.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_node_metrics",
            description="Get detailed CPU and memory metrics for a specific node or all nodes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_name": {
                        "type": "string",
                        "description": "Name of the node (optional, omit to get all nodes)"
                    }
                }
            }
        ),
        Tool(
            name="get_pods",
            description="List pods in a namespace with their status, resource usage, and details.",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Namespace to query (default: all namespaces)",
                        "default": "all"
                    },
                    "label_selector": {
                        "type": "string",
                        "description": "Label selector to filter pods (e.g., 'app=nginx')"
                    }
                }
            }
        ),
        Tool(
            name="get_pod_metrics",
            description="Get CPU and memory metrics for pods in a namespace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Namespace to query (default: all namespaces)",
                        "default": "all"
                    },
                    "pod_name": {
                        "type": "string",
                        "description": "Specific pod name (optional)"
                    }
                }
            }
        ),
        Tool(
            name="get_cluster_info",
            description="Get general cluster information including version, nodes count, and health status.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_namespaces",
            description="List all namespaces in the cluster.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


def parse_quantity(quantity_str):
    """Parse Kubernetes quantity string to numeric value."""
    if not quantity_str:
        return 0

    # Handle CPU units
    if quantity_str.endswith('m'):
        return float(quantity_str[:-1]) / 1000
    elif quantity_str.endswith('n'):
        return float(quantity_str[:-1]) / 1_000_000_000

    # Handle memory units
    units = {'Ki': 1024, 'Mi': 1024**2, 'Gi': 1024**3, 'Ti': 1024**4,
             'K': 1000, 'M': 1000**2, 'G': 1000**3, 'T': 1000**4}

    for suffix, multiplier in units.items():
        if quantity_str.endswith(suffix):
            return float(quantity_str[:-len(suffix)]) * multiplier

    return float(quantity_str)


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""

    if not v1:
        return [TextContent(
            type="text",
            text=json.dumps(
                {"error": "Kubernetes client not initialized. Check kubeconfig."})
        )]

    try:
        if name == "get_cluster_cpu":
            # Get node metrics
            try:
                nodes_metrics = metrics_api.list_cluster_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    plural="nodes"
                )

                total_usage = 0
                total_capacity = 0
                node_details = []

                nodes = v1.list_node()
                node_capacities = {
                    node.metadata.name: node.status.capacity for node in nodes.items}

                for item in nodes_metrics.get('items', []):
                    node_name = item['metadata']['name']
                    usage_str = item['usage']['cpu']
                    usage = parse_quantity(usage_str)

                    capacity_str = node_capacities.get(
                        node_name, {}).get('cpu', '0')
                    capacity = parse_quantity(capacity_str)

                    total_usage += usage
                    total_capacity += capacity

                    node_details.append({
                        "node": node_name,
                        "usage_cores": round(usage, 3),
                        "capacity_cores": round(capacity, 3),
                        "utilization_percent": round((usage / capacity * 100) if capacity > 0 else 0, 2)
                    })

                result = {
                    "cluster_cpu": {
                        "total_usage_cores": round(total_usage, 3),
                        "total_capacity_cores": round(total_capacity, 3),
                        "utilization_percent": round((total_usage / total_capacity * 100) if total_capacity > 0 else 0, 2)
                    },
                    "nodes": node_details
                }

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except ApiException as e:
                if e.status == 404:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "error": "Metrics server not available. Install metrics-server in your cluster.",
                            "hint": "kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml"
                        })
                    )]
                raise

        elif name == "get_cluster_memory":
            try:
                nodes_metrics = metrics_api.list_cluster_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    plural="nodes"
                )

                total_usage = 0
                total_capacity = 0
                node_details = []

                nodes = v1.list_node()
                node_capacities = {
                    node.metadata.name: node.status.capacity for node in nodes.items}

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

                result = {
                    "cluster_memory": {
                        "total_usage_gi": round(total_usage / (1024**3), 2),
                        "total_capacity_gi": round(total_capacity / (1024**3), 2),
                        "utilization_percent": round((total_usage / total_capacity * 100) if total_capacity > 0 else 0, 2)
                    },
                    "nodes": node_details
                }

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except ApiException as e:
                if e.status == 404:
                    return [TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": "Metrics server not available"})
                    )]
                raise

        elif name == "get_node_metrics":
            node_name = arguments.get("node_name")

            try:
                if node_name:
                    node_metrics = metrics_api.get_cluster_custom_object(
                        group="metrics.k8s.io",
                        version="v1beta1",
                        plural="nodes",
                        name=node_name
                    )
                    nodes_data = [node_metrics]
                else:
                    nodes_metrics = metrics_api.list_cluster_custom_object(
                        group="metrics.k8s.io",
                        version="v1beta1",
                        plural="nodes"
                    )
                    nodes_data = nodes_metrics.get('items', [])

                result = []
                nodes = v1.list_node()
                node_info = {node.metadata.name: node for node in nodes.items}

                for item in nodes_data:
                    node_name = item['metadata']['name']
                    node = node_info.get(node_name)

                    if node:
                        cpu_usage = parse_quantity(item['usage']['cpu'])
                        cpu_capacity = parse_quantity(
                            node.status.capacity.get('cpu', '0'))
                        mem_usage = parse_quantity(item['usage']['memory'])
                        mem_capacity = parse_quantity(
                            node.status.capacity.get('memory', '0'))

                        result.append({
                            "name": node_name,
                            "status": node.status.conditions[-1].type if node.status.conditions else "Unknown",
                            "cpu": {
                                "usage_cores": round(cpu_usage, 3),
                                "capacity_cores": round(cpu_capacity, 3),
                                "utilization_percent": round((cpu_usage / cpu_capacity * 100) if cpu_capacity > 0 else 0, 2)
                            },
                            "memory": {
                                "usage_gi": round(mem_usage / (1024**3), 2),
                                "capacity_gi": round(mem_capacity / (1024**3), 2),
                                "utilization_percent": round((mem_usage / mem_capacity * 100) if mem_capacity > 0 else 0, 2)
                            },
                            "pods": {
                                "current": int(node.status.allocatable.get('pods', 0)),
                                "capacity": int(node.status.capacity.get('pods', 0))
                            }
                        })

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            except ApiException as e:
                if e.status == 404:
                    return [TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": "Metrics server not available or node not found"})
                    )]
                raise

        elif name == "get_pods":
            namespace = arguments.get("namespace", "all")
            label_selector = arguments.get("label_selector", "")

            if namespace == "all":
                if label_selector:
                    pods = v1.list_pod_for_all_namespaces(
                        label_selector=label_selector)
                else:
                    pods = v1.list_pod_for_all_namespaces()
            else:
                if label_selector:
                    pods = v1.list_namespaced_pod(
                        namespace, label_selector=label_selector)
                else:
                    pods = v1.list_namespaced_pod(namespace)

            result = []
            for pod in pods.items:
                container_statuses = []
                if pod.status.container_statuses:
                    for cs in pod.status.container_statuses:
                        container_statuses.append({
                            "name": cs.name,
                            "ready": cs.ready,
                            "restart_count": cs.restart_count,
                            "state": str(cs.state)
                        })

                result.append({
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "status": pod.status.phase,
                    "node": pod.spec.node_name,
                    "ip": pod.status.pod_ip,
                    "containers": container_statuses,
                    "created": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else None
                })

            return [TextContent(
                type="text",
                text=json.dumps(
                    {"count": len(result), "pods": result}, indent=2)
            )]

        elif name == "get_pod_metrics":
            namespace = arguments.get("namespace", "all")
            pod_name = arguments.get("pod_name")

            try:
                if namespace == "all":
                    pods_metrics = metrics_api.list_cluster_custom_object(
                        group="metrics.k8s.io",
                        version="v1beta1",
                        plural="pods"
                    )
                    items = pods_metrics.get('items', [])
                else:
                    if pod_name:
                        pod_metrics = metrics_api.get_namespaced_custom_object(
                            group="metrics.k8s.io",
                            version="v1beta1",
                            namespace=namespace,
                            plural="pods",
                            name=pod_name
                        )
                        items = [pod_metrics]
                    else:
                        pods_metrics = metrics_api.list_namespaced_custom_object(
                            group="metrics.k8s.io",
                            version="v1beta1",
                            namespace=namespace,
                            plural="pods"
                        )
                        items = pods_metrics.get('items', [])

                result = []
                for item in items:
                    pod_name = item['metadata']['name']
                    pod_ns = item['metadata']['namespace']

                    containers_metrics = []
                    total_cpu = 0
                    total_mem = 0

                    for container in item.get('containers', []):
                        cpu = parse_quantity(container['usage']['cpu'])
                        mem = parse_quantity(container['usage']['memory'])
                        total_cpu += cpu
                        total_mem += mem

                        containers_metrics.append({
                            "name": container['name'],
                            "cpu_cores": round(cpu, 3),
                            "memory_mi": round(mem / (1024**2), 2)
                        })

                    result.append({
                        "name": pod_name,
                        "namespace": pod_ns,
                        "total_cpu_cores": round(total_cpu, 3),
                        "total_memory_mi": round(total_mem / (1024**2), 2),
                        "containers": containers_metrics
                    })

                return [TextContent(
                    type="text",
                    text=json.dumps(
                        {"count": len(result), "pods": result}, indent=2)
                )]

            except ApiException as e:
                if e.status == 404:
                    return [TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": "Metrics server not available or pod not found"})
                    )]
                raise

        elif name == "get_cluster_info":
            version_info = client.VersionApi().get_code()
            nodes = v1.list_node()
            namespaces = v1.list_namespace()

            node_statuses = []
            for node in nodes.items:
                conditions = {c.type: c.status for c in node.status.conditions}
                node_statuses.append({
                    "name": node.metadata.name,
                    "ready": conditions.get("Ready", "Unknown"),
                    "roles": list(node.metadata.labels.keys()) if node.metadata.labels else []
                })

            result = {
                "version": {
                    "major": version_info.major,
                    "minor": version_info.minor,
                    "git_version": version_info.git_version,
                    "platform": version_info.platform
                },
                "nodes": {
                    "count": len(nodes.items),
                    "details": node_statuses
                },
                "namespaces_count": len(namespaces.items)
            }

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get_namespaces":
            namespaces = v1.list_namespace()

            result = []
            for ns in namespaces.items:
                result.append({
                    "name": ns.metadata.name,
                    "status": ns.status.phase,
                    "created": ns.metadata.creation_timestamp.isoformat() if ns.metadata.creation_timestamp else None,
                    "labels": ns.metadata.labels if ns.metadata.labels else {}
                })

            return [TextContent(
                type="text",
                text=json.dumps(
                    {"count": len(result), "namespaces": result}, indent=2)
            )]

        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps(
                {"error": str(e), "type": type(e).__name__}, indent=2)
        )]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
