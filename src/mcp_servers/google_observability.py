from typing import Any
from mcp.server.fastmcp import FastMCP


# Initialize FastMCP server
mcp = FastMCP("google_observability", "Google Observability", "1.0.0")


async def exec_promql_query(promql: str) -> dict[str, Any] | None:
    """Use prometheus to query the observability data."""
    print(f"Querying Prometheus with: {promql}")

@mcp.tool()
async def get_aggregate_monitoring_data(promql_queries: list[list[str]]) -> str:
    """Grab the aggregate monitoring data from Google Observability.

    Args:
        queries: A list of tupples of PromQL query and its purpose to be executed.
    """
    print(f"Received queries: {promql_queries}")

    return "Aggregate monitoring data"