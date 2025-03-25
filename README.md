# Automating Root Cause Analysis with LLMs and MCP: From Golden Signals to Intelligent Response

This repository contains the code for a sample application, an MCP client, and an MCP server used in a proof-of-concept (PoC) for automated Root Cause Analysis (RCA), as described in my blog.

## RCA Webhook Server
The entry point for the webhook server responsible for RCA is located at `src/app.py`.

To run the RCA server:

```bash
# Navigate to the source directory
cd src

# Run using Flask (suitable for non-production use)
python3 app.py

# For production use, it's recommended to run with Gunicorn
```

## Sample Application
The code for the sample application used in the PoC is located in the `sample_app` directory.