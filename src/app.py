from quart import Quart, request, jsonify
import atexit

from mcp_client.client_v1 import MCPClient

app = Quart(__name__)
mcp_client = MCPClient()

PROMPT_TEMPLATE_FILE = "./mcp_client/prompt_template.txt"
MCP_SERVER_SCRIPT = "./mcp_servers/google_observability.py"

with open(PROMPT_TEMPLATE_FILE, "r") as f:
    prompt_template = f.read()

# Initialize MCP client on startup
async def init_mcp():
    try:
        await mcp_client.connect_to_server(MCP_SERVER_SCRIPT)
        print("MCP client initialized.")
    except Exception as e:
        print(f"Failed to initialize MCP client: {e}")

# Clean up resources on shutdown
@atexit.register
async def shutdown():
    try:
        await mcp_client.cleanup()
        print("Resources cleaned up on shutdown.")
    except Exception as e:
        print(f"Error during shutdown cleanup: {e}")

@app.route('/alert', methods=['POST'])
async def alert():
    data = await request.get_json()
    prompt = f"""
Received Alert:
Summary: {data['incident']['summary']}
Documentation: {data['incident']['documentation']}

{prompt_template}
"""
    # Instead of printing to stdout, configure a log stream
    # and assign unique log id to each request execution
    print("_______________________________________________________________________________________________")
    print(prompt)
    try:
        result = await mcp_client.process_query(prompt)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error processing query: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    print("_______________________________________________________________________________________________")
    return jsonify({"status": "success", "message": "Alert processed"}), 200

if __name__ == '__main__':
    app.before_serving(init_mcp)
    app.run(debug=False, host='0.0.0.0', port=5000)
