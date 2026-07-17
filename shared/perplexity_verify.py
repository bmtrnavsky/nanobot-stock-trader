#!/usr/bin/env python3
"""
Independent-tier claim verification via Perplexity's Sonar API. Used to
corroborate a catalyst claim (e.g. a named partnership or contract)
against live web sources with citations, separate from company PR.

Input (stdin): JSON {
  "query": "Has Globalstar signed a deal with Apple for emergency
             satellite service? What are the confirmed terms?",
  "api_key": "..."   # or PERPLEXITY_API_KEY env var
}

Output (stdout): JSON {"answer": "...", "citations": [...], "status": "ok"}

Requires: uv run --with requests python3 perplexity_verify.py
"""
import json
import os
import sys

import requests

API_URL = "https://api.perplexity.ai/chat/completions"


def get_api_key(payload: dict) -> str:
    key = payload.get("api_key") or os.environ.get("PERPLEXITY_API_KEY")
    if not key:
        raise RuntimeError(
            "Missing Perplexity API key. Sign up at perplexity.ai/settings/api, "
            "provide via payload 'api_key' or PERPLEXITY_API_KEY env var."
        )
    return key


def verify_claim(query: str, api_key: str, model: str = "sonar") -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are verifying a specific factual claim for an "
                    "investment research process. Answer only from "
                    "sources you can cite. If the claim cannot be "
                    "independently confirmed, say so plainly rather "
                    "than inferring or guessing."
                ),
            },
            {"role": "user", "content": query},
        ],
    }
    resp = requests.post(API_URL, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    answer = data["choices"][0]["message"]["content"]
    citations = data.get("citations", [])
    return {"answer": answer, "citations": citations}


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "reason": f"invalid JSON input: {e}"}))
        sys.exit(1)

    query = payload.get("query")
    if not query:
        print(json.dumps({"status": "error", "reason": "no query provided"}))
        sys.exit(1)

    model = payload.get("model", "sonar")

    try:
        api_key = get_api_key(payload)
        result = verify_claim(query, api_key, model)
    except Exception as e:
        print(json.dumps({"status": "error", "reason": str(e)}))
        sys.exit(1)

    print(json.dumps({"status": "ok", **result}, indent=2, default=str))


if __name__ == "__main__":
    main()
