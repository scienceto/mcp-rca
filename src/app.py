from flask import Flask, request, jsonify
import asyncio
import atexit

from mcp_client.client_v1 import MCPClient

app = Flask(__name__)
mcp_client = MCPClient()

# Create a single, shared asyncio event loop that lives for the duration of the application.
# This is necessary because MCPClient uses asyncio, and we must ensure that
# we do not create separate event loops in a multi-threaded environment (which can happen
# when using Flask with a WSGI server that spawns threads per request).
# Flask does not manage asyncio event loops, so we manage one explicitly.
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

PROMPT_TEMPLATE_FILE = "./mcp_client/prompt_template.txt"
MCP_SERVER_SCRIPT = "./mcp_servers/google_observability.py"

with open(PROMPT_TEMPLATE_FILE, "r") as f:
    prompt_template = f.read()

# Initialize MCP client on startup
def init_mcp():
    try:
        loop.run_until_complete(mcp_client.connect_to_server(MCP_SERVER_SCRIPT))
        print("MCP client initialized.")
    except Exception as e:
        print(f"Failed to initialize MCP client: {e}")

# Clean up resources on shutdown
@atexit.register
def shutdown():
    try:
        loop.run_until_complete(mcp_client.cleanup())
        loop.close()
        print("Resources cleaned up on shutdown.")
    except Exception as e:
        print(f"Error during shutdown cleanup: {e}")

@app.route('/alert', methods=['POST'])
def alert():
    data = request.get_json()
    prompt = f"""
Received Alert:
Summary: {data['incident']['summary']}
Documentation: {data['incident']['documentation']}

{prompt_template}
"""
    # instead of printing to stdout configure a log stream
    # and assign unique log id to each request execution
    print(prompt)
    try:
        result = loop.run_until_complete(mcp_client.process_query(prompt))
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error processing query: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "success", "message": "Alert processed"}), 200

if __name__ == '__main__':
    init_mcp()
    app.run(debug=False, host='0.0.0.0', port=5000)
