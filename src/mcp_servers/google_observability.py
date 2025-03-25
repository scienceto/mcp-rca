import json
import httpx
import logging
import asyncio
import datetime
from google.auth import default
from mcp.server.fastmcp import FastMCP
from google.auth.transport.requests import Request

# Set up logging to a file instead of stdout
# to avoid cluttering the console
logging.basicConfig(filename='google_observability.log', level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
REQUEST_TIMEOUT = 60.0
api_quota_project_id = "API_QUOUT_PROJECT_ID"

# Initialize Google Cloud credentials
credentials, project = default(quota_project_id=api_quota_project_id, scopes=["https://www.googleapis.com/auth/cloud-platform"])
credentials.refresh(Request())
oauth_token = credentials.token
oauth_header = {
    "Authorization": f"Bearer {oauth_token}",
    "Content-Type": "application/json"
}

# Initialize FastMCP server
mcp = FastMCP("google_observability")

async def query_prometheus_metrics(scanned_project, query_list, oauth_header):
    """Grab the prometheus metrics from Google Observability.
    
    Args:
        scanned_project: The project ID to query metrics from.
        query_list: A list of tuples of PromQL query and its purpose to be executed
    """

    metrics_result_list = []

    # https://cloud.google.com/monitoring/api/ref_v3/rest/v1/projects.location.prometheus.api.v1/query
    url = f"https://monitoring.googleapis.com/v1/projects/{scanned_project}/location/global/prometheus/api/v1/query"

    # using async httpx client to make concurrent requests
    # to the Prometheus API
    # and gather the results
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        tasks = []
        for [metric, _] in query_list:
            request_body = {"query": metric}
            tasks.append(client.post(url, json=request_body, headers=oauth_header))
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for i, response in enumerate(responses):
            metric_name = query_list[i][-1]
            if isinstance(response, Exception):
                logger.error(f"Exception occurred for metric {metric_name}: {response}")
                continue
            
            if response.status_code == 200:
                # parse the response or
                # can be returned as it is as LLM can work with general schema 
                result = response.json().get("data", {}).get("result", [])
                metrics_result_list.append({
                    "purpose": metric_name,
                    "data": result
                })
            else:
                logger.error(f"Non-200 response for metric {metric_name}: {response.status_code}")

    return metrics_result_list

# Function to safely extract message from log payload as string
def safe_message(entry):
    for key in ["textPayload", "jsonPayload", "protoPayload"]:
        if key in entry:
            try:
                return json.dumps(entry[key]) if isinstance(entry[key], dict) else str(entry[key])
            except Exception:
                return str(entry[key])
    return ""

async def query_logs(project_id: str, log_period: float, log_filter: str, order_by="timestamp asc"):
    """Grab the logs from Google Observability.
    
    Args:
        project_id: The project ID to query logs from.
        log_period: The time period, in minutes, for which to fetch logs.
        log_filter: The filter string to apply to the logs.
        order_by: The order in which to sort the logs.
    """
    # Set up the log filter and resource name
    log_entries = []
    log_filter += f' AND timestamp >= "{(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=log_period)).strftime("%Y-%m-%dT%H:%M:%SZ")}"'
    resource_name = f"projects/{project_id}"
    body = {
        "resourceNames": [resource_name],
        "filter": log_filter,
        "orderBy": order_by
    }

    # https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry
    url = "https://logging.googleapis.com/v2/entries:list"

    seen_locations = set()
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        while True:
            response = await client.post(url, headers=oauth_header, json=body)
            response.raise_for_status()
            data = response.json()

            for entry in data.get("entries", []):
                source_location = entry.get("sourceLocation", {})
                location_key = None

                # Create deduplication key if sourceLocation exists
                # and add to seen locations
                # to avoid duplicates in the log entries
                # This is to reduce LLM token usage
                # You can also write some generic deduplication logic
                # based on some similarity distance measure
                # If you don't have LLM token limit, you can skip this
                # and just return all the log entries
                if source_location:
                    location_key = (
                        source_location.get("file"),
                        source_location.get("line"),
                        source_location.get("function")
                    )
                if location_key and location_key in seen_locations:
                    continue

                message = safe_message(entry)

                # Parse the log entry
                # again this is to reduce LLM token usage
                # You can avoid this and just return the raw entry
                parsed_entry = {
                    "message": message,
                    "labels": entry.get("labels", {}),
                    "metadata": entry.get("metadata", {}),
                    "sourceLocation": source_location,
                    "resource": entry.get("resource", {})
                }

                log_entries.append(parsed_entry)

                if location_key:
                    seen_locations.add(location_key)

            if "nextPageToken" in data:
                body["pageToken"] = data["nextPageToken"]
            else:
                break

    return log_entries

@mcp.tool()
async def get_aggregate_monitoring_data(project_id: str, promql_queries: list[list[str]]):
    """Grab the aggregate monitoring data from Google Observability.

    Args:
        project_id: The project ID to query metrics from.
        promql_queries: A list of tupples of PromQL query and its purpose to be executed.
    """
    logger.info(f"Received queries: {promql_queries}")  # Log to file instead of stdout

    return await query_prometheus_metrics(project_id, promql_queries, oauth_header)

@mcp.tool()
async def get_logs(project_id: str, log_period: float, log_filter: str, order_by="timestamp asc"):
    """Grab the logs from Google Observability.

    Args:
        project_id: The project ID to query logs from.
        log_period: The time period, in minutes, for which to fetch logs.
        log_filter: The filter string to apply to the logs.
        order_by: The order in which to sort the logs.
    """
    logger.info(f"Received filter: {log_filter}")

    results = await query_logs(project_id, log_period, log_filter, order_by)
    return results

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')