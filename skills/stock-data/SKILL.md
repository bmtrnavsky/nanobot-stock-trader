---
name: stock-data
description: "Shared script library for the trading skills. Not directly invokable -- use swing-trade-scanner, longterm-quality-investor, or catalyst-growth-investor, which document these scripts."
---

# Stock Data (shared library)

This folder holds the tested data scripts (`scripts/fetch_stock_data.py`,
`screen_stocks.py`, `sec_filings.py`, `financials.py`, `market_mood.py`,
`sentisense_sentiment.py`, `perplexity_verify.py`) shared by the three
trading skills. Invocation patterns, required API keys, and field notes
live in those skills' SKILL.md files -- consult them, not this file.
`sentisense_sentiment.py` is retired (Reddit closed self-serve OAuth, Nov 2025).

