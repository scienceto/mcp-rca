# Automating Root Cause Analysis with LLMs and MCP: From Golden Signals to Intelligent Response

This repository contains the code for a sample application, an MCP client, and an MCP server used in a proof-of-concept (PoC) for automated Root Cause Analysis (RCA), as described in my [blog](https://medium.com/p/b921e4d46829).

## RCA Webhook Server
The entry point for the webhook server responsible for RCA is located at `src/app.py`.

Update `src/mcp_client/prompt_template.txt` to match your requirements and environment.

To run the RCA server:

```bash
# Navigate to the source directory
cd src

# Run using debug server (suitable for non-production use)
python3 app.py

# For production use, it's recommended to run with production ASGI servers such as Hypercorn
```

## Sample Application
The code for the sample application used in the PoC is located in the `sample_app` directory.

## Note
- Even though I've used Quart to properly handle concurrent requests using event loop, I've not tested the application under load.
