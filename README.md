# nanobot-stock-trader

Free stock research toolkit built for AI agent skills (Nanobot,
Claude, or any agent that can run Python via `uv run`). No paid data
sources required for the core layer.

## What's here

**`shared/`** -- data-fetch scripts, stdin-JSON in / stdout-JSON out,
each independently runnable and testable:

- `fetch_stock_data.py` -- price, fundamentals, dividends, insider
  transactions, institutional holders, analyst actions. Via `yfinance`,
  free, no API key.
- `screen_stocks.py` -- candidate screening by market cap, price,
  sector, dividend yield, or predefined categories (small caps,
  gainers, etc). Via `yfinance`'s `EquityQuery`/`screen()`, free.
- `sec_filings.py` -- recent filings, Form 4 insider transactions,
  going-concern language detection. Via `edgartools`, free, MIT
  licensed, requires only a name+email identity string per SEC's
  fair-access policy (no account, no key).
- `reddit_sentiment.py` -- subreddit search for ticker discussion. Via
  PRAW, free for personal/research use (100 QPM). Requires a free
  Reddit app registration at reddit.com/prefs/apps.
- `perplexity_verify.py` -- independent-source claim verification
  (e.g. "did company X actually sign this partnership") with
  citations. Via Perplexity's Sonar API, paid per-call (cheap, ~$1/M
  tokens + a small request fee).
## Usage

All scripts follow the same convention: pipe JSON to stdin, get JSON
back on stdout. No CLI flags, no argparse -- makes them trivial for an
agent to call via `uv run`.

```bash
echo '{"tickers": ["AAPL", "GSAT"]}' | \
  uv run --with yfinance python3 shared/fetch_stock_data.py

echo '{"market_cap_min": 50000000, "market_cap_max": 2000000000, "price_min": 5, "price_max": 25}' | \
  uv run --with yfinance python3 shared/screen_stocks.py

echo '{"ticker": "GSAT", "checks": ["recent_filings", "insider_form4", "going_concern"], "identity": "Your Name your.email@example.com"}' | \
  uv run --with edgartools python3 shared/sec_filings.py

echo '{"query": "GSAT", "client_id": "...", "client_secret": "..."}' | \
  uv run --with praw python3 shared/reddit_sentiment.py

echo '{"query": "Has company X signed a real partnership with Y?", "api_key": "..."}' | \
  uv run --with requests python3 shared/perplexity_verify.py
```

Credentials can be passed in the JSON payload or set as environment
variables (`REDDIT_CLIENT_ID`/`REDDIT_CLIENT_SECRET`, `EDGAR_IDENTITY`,
`PERPLEXITY_API_KEY`) -- never hardcoded in the scripts.

## Design notes

- Every ticker-level failure returns `{"error": "..."}` for that
  ticker rather than failing the whole batch.
- `screen_stocks.py` filters to NYSE (`NYQ`) + Nasdaq (`NMS`) by
  default -- Yahoo's `region` field was tested and found to leak
  foreign OTC/pink-sheet tickers even when scoped to "us"; `exchange`
  filtering is the real, working restriction.
- Dividend CAGR/consecutive-increase logic compares same-quarter
  year-over-year on the raw payment series, not calendar-year
  resampling -- resampling was tested and found to distort partial
  first/last years into false "decreases."
- Data lag: Yahoo Finance price/volume ~15-20 min delayed; insider
  trades ~2-3 days (SEC filing lag); short interest ~2 weeks (FINRA
  reporting cycle).

## Not financial advice

This is a data-fetching toolkit, not a trading system. Nothing here
recommends buy/sell/hold decisions.
