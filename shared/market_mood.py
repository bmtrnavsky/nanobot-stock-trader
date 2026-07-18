#!/usr/bin/env python3
"""
Market-wide sentiment gauge for a Down Tape Protocol / market-regime
check -- VIX (via yfinance, more reliable than parsing web search
results for a number that could drive hard gating rules) plus CNN's
Fear & Greed Index (via the `fear-and-greed` PyPI package).

Input (stdin): JSON {} (no parameters needed)

Output (stdout): JSON {
  "vix": {"value": 18.4, "regime": "normal" | "elevated" | "fear_mode"},
  "fear_greed": {"value": 31, "description": "Fear",
                 "last_update": "...", "regime": "extreme_fear" | "fear" |
                 "neutral" | "greed" | "extreme_greed"}
}
On failure for either source, that key's value is {"error": "..."}
rather than failing the whole call.

Requires: uv run --with yfinance --with fear-and-greed python3 market_mood.py
"""
import json
import sys

import yfinance as yf
import fear_and_greed


def get_vix() -> dict:
    try:
        info = yf.Ticker("^VIX").info
        value = info.get("regularMarketPrice") or info.get("previousClose")
        if value is None:
            return {"error": "no VIX price returned"}
        if value > 30:
            regime = "fear_mode"
        elif value > 25:
            regime = "elevated"
        else:
            regime = "normal"
        return {"value": value, "regime": regime}
    except Exception as e:
        return {"error": str(e)}


def get_fear_greed() -> dict:
    try:
        result = fear_and_greed.get()
        value = result.value
        if value <= 25:
            regime = "extreme_fear"
        elif value <= 45:
            regime = "fear"
        elif value <= 55:
            regime = "neutral"
        elif value <= 75:
            regime = "greed"
        else:
            regime = "extreme_greed"
        return {
            "value": round(value, 1),
            "description": result.description,
            "last_update": str(result.last_update),
            "regime": regime,
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    result = {"vix": get_vix(), "fear_greed": get_fear_greed()}
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
