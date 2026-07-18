#!/usr/bin/env python3
"""
Reddit-sourced sentiment via the SentiSense API -- replaces
reddit_sentiment.py, which relied on Reddit's own OAuth app creation
(closed to new self-serve apps since Nov 2025). SentiSense is a
licensed, read-only financial-data API (Compass AI Data Services, LLC)
that has already solved the sourcing/licensing problem; this script
just calls their documented endpoints.

Rate limit reality: free tier is 1,000 requests/month, 30/min. Don't
call this on every raw candidate in a broad scan -- run it only on
survivors that already cleared News Quality, Volume/Liquidity, and
Chart Behavior. See swing-trade-scanner's SCAN MODE for the intended
call order.

Input (stdin): JSON {
  "ticker": "GSAT",
  "days": 7,
  "api_key": "ss_live_..."
}
  api_key can also come from env var SENTISENSE_API_KEY instead.
  days is the lookback window for documents/sentiment (1-365, default 7).

Output (stdout): JSON {
  "status": "ok",
  "ticker": "...",
  "reddit_documents": {...},   # raw response from /documents/ticker/{ticker}?source=REDDIT
  "sentiment_series": {...},   # raw response from /metrics/entity/{ticker}/metric/sentiment
  "summary": {
    "document_count": N,
    "positive": N, "negative": N, "neutral": N,
    "average_sentiment_label": "positive"|"negative"|"neutral"|null,
    "note": "..."
  }
}
Note: SentiSense document responses include a url but not headline/
title text -- this gives sentiment signal, not post content to read.

Requires: uv run --with requests python3 sentisense_sentiment.py
"""
import json
import os
import sys

import requests

BASE_URL = "https://app.sentisense.ai"


def get_api_key(payload: dict) -> str:
    key = payload.get("api_key") or os.environ.get("SENTISENSE_API_KEY")
    if not key:
        raise RuntimeError(
            "Missing SentiSense API key. Provide via payload 'api_key' "
            "or SENTISENSE_API_KEY env var."
        )
    return key


def _get(path: str, api_key: str, params: dict = None):
    resp = requests.get(
        f"{BASE_URL}{path}",
        headers={"X-SentiSense-API-Key": api_key},
        params=params or {},
        timeout=15,
    )
    if resp.status_code == 401:
        raise RuntimeError("SentiSense rejected the API key (401)")
    if resp.status_code == 429:
        raise RuntimeError("SentiSense rate limit or monthly quota exceeded (429)")
    resp.raise_for_status()
    return resp.json()


def summarize_documents(documents: list, ticker: str) -> dict:
    """Per-document sentiment comes from the `sentiment` array, which
    classifies EVERY entity mentioned in that post/article, not just
    the ticker being queried -- confirmed live that a single Reddit
    post can carry dozens of unrelated tickers in this array. Filter
    to entries whose `ticker` field matches the one we asked about,
    case-insensitively, or the rollup silently mixes in sentiment
    about other companies mentioned in the same post."""
    ticker_upper = ticker.upper()
    pos = neg = neu = 0
    matched_docs = 0
    for doc in documents:
        doc_matched = False
        for s in doc.get("sentiment", []):
            if (s.get("ticker") or "").upper() != ticker_upper:
                continue
            doc_matched = True
            label = (s.get("sentiment") or s.get("label") or "").upper()
            if label == "POSITIVE":
                pos += 1
            elif label == "NEGATIVE":
                neg += 1
            elif label == "NEUTRAL":
                neu += 1
        if doc_matched:
            matched_docs += 1

    total = pos + neg + neu
    if total == 0:
        overall = None
    elif pos > neg and pos >= neu:
        overall = "positive"
    elif neg > pos and neg >= neu:
        overall = "negative"
    else:
        overall = "neutral"

    return {
        "document_count": len(documents),
        "documents_mentioning_ticker": matched_docs,
        "positive": pos,
        "negative": neg,
        "neutral": neu,
        "average_sentiment_label": overall,
        "note": (
            "No Reddit documents found in this window -- absence of "
            "chatter, not a neutral signal. Don't treat this as bearish "
            "or bullish, just as no confirmation available."
        ) if len(documents) == 0 else (
            "SentiSense's ticker filter on this endpoint returns documents "
            "co-mentioning many tickers -- documents_mentioning_ticker "
            "shows how many actually reference this specific ticker in "
            "their sentiment breakdown, which may be fewer than document_count."
        ) if matched_docs < len(documents) else None,
    }


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "reason": f"invalid JSON input: {e}"}))
        sys.exit(1)

    ticker = payload.get("ticker")
    if not ticker:
        print(json.dumps({"status": "error", "reason": "no ticker provided"}))
        sys.exit(1)

    days = payload.get("days", 7)

    try:
        api_key = get_api_key(payload)

        reddit_docs = _get(
            f"/api/v1/documents/ticker/{ticker}",
            api_key,
            {"source": "REDDIT", "days": days, "limit": 200},
        )
        sentiment_series = _get(
            f"/api/v2/metrics/entity/{ticker}/metric/sentiment",
            api_key,
        )

        summary = summarize_documents(reddit_docs.get("documents", []), ticker)

        result = {
            "status": "ok",
            "ticker": ticker,
            "reddit_documents": reddit_docs,
            "sentiment_series": sentiment_series,
            "summary": summary,
        }
    except Exception as e:
        print(json.dumps({"status": "error", "reason": str(e), "ticker": ticker}))
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
