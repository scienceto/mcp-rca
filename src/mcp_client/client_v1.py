import os
import sys
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

# load the API key from .env file
load_dotenv()

MAX_TOKENS = 8192
MODEL = "claude-3-7-sonnet-20250219"

# Follow the MCP Client Quickstart understand the client implementation
# https://modelcontextprotocol.io/quickstart/client
class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
    
    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        python_path = sys.executable  # this gives the current Python interpreter path
        command = python_path if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=os.environ.copy()  # preserves current environment vars
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])
    
    async def process_query(self, query: str) -> str:
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        final_text = []

        # loop until LLM responses suggest tool use
        # it's a good practice to put an upperbound on the number of calls
        # to prevent LLM from cyclic reasoning
        while True:
            # alternatively enable stream to process messages efficiently
            response = self.anthropic.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=messages,
                tools=available_tools
            )

            assistant_message_content = []
            tool_used = False

            for content in response.content:
                if content.type == 'text':
                    final_text.append(content.text)
                    assistant_message_content.append(content)

                elif content.type == 'tool_use':
                    tool_used = True
                    tool_name = content.name
                    tool_args = content.input
                    print(f".........Calling tool {tool_name} with args {tool_args}.........")

                    # Call the tool
                    result = await self.session.call_tool(tool_name, tool_args)

                    # Append assistant's tool_use message
                    assistant_message_content.append(content)
                    messages.append({
                        "role": "assistant",
                        "content": assistant_message_content
                    })

                    # Add tool_result message
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": result.content
                            }
                        ]
                    })

            # If no tools were called, just append the response and exit
            if not tool_used:
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })
                break

        return "\n".join(final_text)

    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
