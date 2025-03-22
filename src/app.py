from flask import Flask, request, jsonify
import asyncio
import atexit

from mcp_client.client import MCPClient  # Adjust the import as needed

app = Flask(__name__)

mcp_client = MCPClient()

# Initialize server connection before handling requests
@app.before_first_request
def startup():
    asyncio.run(mcp_client.connect_to_server("path/to/your/server_script.py"))  # Update path

# Graceful shutdown using atexit
@atexit.register
def shutdown():
    try:
        asyncio.run(mcp_client.cleanup())
        print("Resources cleaned up on shutdown.")
    except Exception as e:
        print(f"Error during shutdown cleanup: {e}")

@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    try:
        result = asyncio.run(mcp_client.process_query(data['query']))
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
