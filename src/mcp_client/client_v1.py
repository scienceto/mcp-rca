import os
import sys
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Using async anthropic client for better performance
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

# load the API key from .env file
load_dotenv()

MAX_TOKENS = 8192
MODEL = "claude-3-7-sonnet-20250219"

# Create a new session for each request
class MCPClient:
    def __init__(self):
        self.server_script_path = None
        self.anthropic = AsyncAnthropic()
    
    async def initialize(self, server_script_path: str):
        """Initialize the client with the server script path"""
        self.server_script_path = server_script_path
    
    async def process_query(self, query: str) -> str:
        """Process a query using a dedicated session for this request"""
        if not self.server_script_path:
            raise ValueError("Client not initialized. Call initialize() first.")
            
        # Create a new exit stack and session for this request
        exit_stack = AsyncExitStack()
        session = await self._create_session(exit_stack)
        
        try:
            return await self._process_with_session(query, session)
        finally:
            # Clean up this request's resources
            await exit_stack.aclose()
    
    async def _create_session(self, exit_stack):
        """Create a new session with its own connection"""
        is_python = self.server_script_path.endswith('.py')
        is_js = self.server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        python_path = sys.executable
        command = python_path if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[self.server_script_path],
            env=os.environ.copy()
        )

        stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await exit_stack.enter_async_context(ClientSession(stdio, write))

        await session.initialize()
        return session
    
    async def _process_with_session(self, query: str, session) -> str:
        """Process a query with the given session"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        final_text = []

        # Loop until LLM responses suggest tool use
        # It's a good practice to put an upperbound on the number of calls
        # to prevent LLM from cyclic reasoning
        while True:
            # Using await with AsyncAnthropic
            response = await self.anthropic.messages.create(
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

                    # Call the tool using this request's session
                    result = await session.call_tool(tool_name, tool_args)

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
        """No global resources to clean up anymore"""
        pass