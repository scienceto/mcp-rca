from quart import Quart, request, jsonify
import atexit
from mcp_client.client_v1 import MCPClient

app = Quart(__name__)
mcp_client = MCPClient()
PROMPT_TEMPLATE_FILE = "./mcp_client/prompt_template.txt"
MCP_SERVER_SCRIPT = "./mcp_servers/google_observability.py"

with open(PROMPT_TEMPLATE_FILE, "r") as f:
    prompt_template = f.read()

# Initialize MCP client on startup - now just storing the server path
@app.before_serving
async def init_mcp():
    try:
        await mcp_client.initialize(MCP_SERVER_SCRIPT)
        print("MCP client initialized.")
    except Exception as e:
        print(f"Failed to initialize MCP client: {e}")

# Clean up resources on shutdown
@atexit.register
def shutdown():
    print("Resources cleaned up on shutdown.")

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
        # Each call to process_query will create its own session
        result = await mcp_client.process_query(prompt)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error processing query: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
        
    print("_______________________________________________________________________________________________")
    return jsonify({"status": "success", "message": "Alert processed"}), 200

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)