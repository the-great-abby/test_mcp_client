#!/usr/bin/env python3
"""
Standalone script to test Anthropic's HTTP POST API (Claude-3).

Usage:
  export ANTHROPIC_API_KEY=your_real_key
  python scripts/anthropic_http_post.py

This script will incur real API usage and should only be run intentionally.
"""
import os
import sys
import requests
import json

ANTHROPIC_API_URL = os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    print("No Anthropic API key set in ANTHROPIC_API_KEY")
    sys.exit(1)

headers = {
    "x-api-key": ANTHROPIC_API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}

payload = {
    "model": "claude-3-opus-20240229",
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": "Hello, Claude!"}
    ]
}

try:
    response = requests.post(ANTHROPIC_API_URL, headers=headers, data=json.dumps(payload))
    print("Status code:", response.status_code)
    print("Response:", response.text)
    response.raise_for_status()
    print("Anthropic HTTP POST API test PASSED")
except Exception as e:
    print(f"Anthropic HTTP POST API test FAILED: {e}")
    sys.exit(1) 