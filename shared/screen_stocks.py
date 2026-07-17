#!/usr/bin/env python3
"""
Shared candidate screener, parameterized per calling skill's universe.

Input (stdin): JSON {
  "market_cap_min": 50000000, "market_cap_max": 2000000000,
  "price_min": 5, "price_max": 25,
  "sector": null,                 # optional exact match
  "min_dividend_yield": null,     # optional, percent e.g. 2.0
  "predefined": null,             # optional: use a PREDEFINED_SCREENER_QUERIES key instead
  "count": 25
}

Output (stdout): JSON {"total": N, "candidates": [{...}, ...]}

Requires: uv run --with yfinance python3 screen_stocks.py
"""
import json
import sys

import yfinance as yf
from yfinance import EquityQuery


def build_query(payload: dict) -> EquityQuery:
    clauses = []

    cap_min = payload.get("market_cap_min")
    cap_max = payload.get("market_cap_max")
    if cap_min is not None:
        clauses.append(EquityQuery("gt", ["intradaymarketcap", cap_min]))
    if cap_max is not None:
        clauses.append(EquityQuery("lt", ["intradaymarketcap", cap_max]))

    price_min = payload.get("price_min")
    price_max = payload.get("price_max")
    if price_min is not None:
        clauses.append(EquityQuery("gt", ["intradayprice", price_min]))
    if price_max is not None:
        clauses.append(EquityQuery("lt", ["intradayprice", price_max]))

    sector = payload.get("sector")
    if sector:
        clauses.append(EquityQuery("eq", ["sector", sector]))

    min_yield = payload.get("min_dividend_yield")
    if min_yield is not None:
        clauses.append(EquityQuery("gt", ["forward_dividend_yield", min_yield]))

    region = payload.get("region", "us")
    if region == "us":
        # region field returns non-US OTC/pink-sheet tickers even when
        # asked for "us" -- exchange filtering is the real, working
        # restriction to NYSE (NYQ) + Nasdaq (NMS), excludes OTC/foreign.
        clauses.append(EquityQuery("or", [
            EquityQuery("eq", ["exchange", "NMS"]),
            EquityQuery("eq", ["exchange", "NYQ"]),
        ]))

    if len(clauses) == 1:
        return clauses[0]
    return EquityQuery("and", clauses)


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "reason": f"invalid JSON input: {e}"}))
        sys.exit(1)

    count = payload.get("count", 25)
    predefined = payload.get("predefined")

    try:
        if predefined:
            result = yf.screen(predefined, count=count)
        else:
            query = build_query(payload)
            result = yf.screen(query, count=count, sortField="intradaymarketcap", sortAsc=False)
    except Exception as e:
        print(json.dumps({"status": "error", "reason": str(e)}))
        sys.exit(1)

    quotes = result.get("quotes", [])
    candidates = [
        {
            "symbol": q.get("symbol"),
            "name": q.get("shortName"),
            "market_cap": q.get("marketCap"),
            "price": q.get("regularMarketPrice"),
            "sector": q.get("sector"),
            "pct_change": q.get("regularMarketChangePercent"),
        }
        for q in quotes
    ]
    print(json.dumps({"total": result.get("total"), "candidates": candidates}, indent=2, default=str))


if __name__ == "__main__":
    main()
