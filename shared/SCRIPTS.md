# Shared Scripts Reference

Detailed input/output reference for every script in `shared/`. All scripts
share the same interface: **pipe JSON to stdin, get JSON back on stdout,
no CLI flags.** This doc covers exact fields; see the main [README](../README.md)
for setup and quick-start.

Every script returns `{"status": "error", "reason": "..."}` (top-level, exit
code 1) for malformed input or missing required fields. Where a script
processes a batch (e.g. multiple tickers), a per-item failure returns
`{"error": "..."}` for that item only -- the rest of the batch still
completes.

---

## fetch_stock_data.py

Price, fundamentals, dividends, insiders, institutional holders, and
analyst data via `yfinance`. No API key.

```
uv run --with yfinance python3 shared/fetch_stock_data.py
```

**Input:**
```json
{
  "tickers": ["AAPL", "GSAT"],
  "fields": ["price", "fundamentals", "dividends", "insiders", "institutional", "analyst"]
}
```
`fields` is optional -- omit for the full default bundle (all six groups above).

**Output:** `{ticker: {...merged fields from each requested group...}, ...}`. A
ticker that fails entirely returns `{"error": "..."}` in its place.

**Field groups and what they return:**

| Group | Key fields |
|---|---|
| `price` | `price`, `market_cap`, `volume`, `avg_volume_3m`, `float_shares`, `shares_outstanding`, `fifty_two_wk_high`/`low`, `short_pct_of_float`, `beta` |
| `fundamentals` | `pe_ratio`, `forward_pe`, `price_to_sales`, `profit_margin`, `revenue_growth`, `earnings_growth`, `total_cash`, `total_debt`, `free_cashflow`, `sector`, `industry` |
| `dividends` | `dividend_yield_pct`, `dividend_rate`, `payout_ratio`, `five_year_avg_yield`, `ex_dividend_date`, `dividend_cagr_est_pct`, `consecutive_annual_increases_est` |
| `insiders` | `insider_purchase_summary`, `recent_insider_transactions` (records, not a percentage -- see `institutional` for ownership %) |
| `institutional` | `pct_held_institutions`, `pct_held_insiders`, `top_institutional_holders` (top 5), `major_holders_summary` |
| `analyst` | `recommendation_key`, `target_mean_price`/`high`/`low`, `number_of_analysts`, `recent_upgrades_downgrades` |

**Notes:**
- Dividend CAGR/consecutive-increase math compares same-quarter year-over-year
  on the raw payment series (not calendar-year resampling, which was tested
  and rejected -- it distorts partial first/last years into false "decreases").
  Both figures are labeled `_est` since payment frequency is inferred from
  recent payment-date gaps, not confirmed from the filing.
- `insiders` returns transaction records only, not an ownership percentage --
  use `institutional`'s `pct_held_insiders` for that.
- Data lag (Yahoo Finance, not this script): price/volume ~15-20 min delayed;
  insider trades ~2-3 days; short interest ~2 weeks (FINRA cycle).

---

## screen_stocks.py

Candidate screening by market cap, price, sector, or dividend yield, or a
Yahoo predefined screener. No API key.

```
uv run --with yfinance python3 shared/screen_stocks.py
```

**Input:**
```json
{
  "market_cap_min": 50000000,
  "market_cap_max": 2000000000,
  "price_min": 5,
  "price_max": 25,
  "sector": null,
  "min_dividend_yield": null,
  "predefined": null,
  "count": 25
}
```
- `predefined`, if set, bypasses the filter clauses entirely and calls
  `yfinance.screen()` with that named query directly (e.g. `"small_cap_gainers"`,
  `"day_gainers"`, `"most_actives"`).
- `region` defaults to `"us"`, which restricts to NYSE (`NYQ`) + Nasdaq (`NMS`)
  exchanges specifically -- Yahoo's own `region` field was tested and found to
  leak foreign OTC/pink-sheet tickers even when scoped to "us".

**Output:**
```json
{"total": 143, "candidates": [{"symbol": "...", "name": "...", "market_cap": 0, "price": 0, "sector": "...", "pct_change": 0}]}
```

---

## sec_filings.py

Recent SEC filings, Form 4 insider transactions, and a going-concern
language check via `edgartools`. Requires an identity string (SEC fair-access
policy, not a real account).

```
uv run --with edgartools python3 shared/sec_filings.py
```

**Input:**
```json
{
  "ticker": "GSAT",
  "checks": ["recent_filings", "insider_form4", "going_concern"],
  "identity": "Your Name your.email@example.com"
}
```
`identity` can come from the `EDGAR_IDENTITY` env var instead. `checks`
defaults to `["recent_filings", "insider_form4"]` if omitted (going-concern
is opt-in since it's a heuristic, not a hard fact -- see below).

**Output:** `{"status": "ok", "ticker": "...", <each requested check as a key>}`

- `recent_filings` / `insider_form4` -> list of `{form, filed, accession_no, url}`
  (insider_form4 omits `form` since it's always Form 4)
- `going_concern` -> `{"checked": bool, "filing_form": "...", "filing_date": "...", "going_concern_language_found": bool}`.
  This is a keyword grep ("going concern", "substantial doubt") on the latest
  10-K/10-Q -- a `true` hit is rare and material, worth a manual read of the
  actual filing, not a substitute for one.

---

## financials.py

Structured balance sheet / income statement / cash flow line items, Piotroski
F-Score, ROIC, EV/EBITDA, and cash runway -- everything `fetch_stock_data.py`'s
summary ratios don't cover. Same identity requirement as `sec_filings.py`.

```
uv run --with edgartools python3 shared/financials.py
```

**Input:**
```json
{
  "ticker": "GSAT",
  "periods": 3,
  "market_cap": 4900000000,
  "total_cash": 500000000,
  "total_debt": 200000000,
  "free_cashflow": 300000000,
  "identity": "Your Name your.email@example.com"
}
```
`periods` (default 3) controls how many most-recent filing periods to pull.
`market_cap`/`total_cash`/`total_debt`/`free_cashflow` are optional
passthroughs from `fetch_stock_data.py`'s Yahoo-sourced figures, used
alongside the filing data for EV, EV/EBITDA, FCF conversion, and cash runway.

**Output:**
```json
{
  "status": "ok",
  "ticker": "GSAT",
  "periods_returned": 3,
  "line_items": { "revenue": [latest, ..., oldest], "gross_profit": [...], "...": "each value a list, most-recent first, null = not found in the filing" },
  "ratios_by_period": [{"gross_margin": 0, "operating_margin": 0, "roa": 0, "current_ratio": 0, "cfo_to_assets": 0, "asset_turnover": 0, "debt_to_assets": 0}],
  "piotroski_f_score": {"score": 0, "max_possible": 0, "signals": {"...": 0}, "missing_signals": [], "note": "..."},
  "roic": {"roic": 0, "nopat": 0, "invested_capital": 0, "note": "..."},
  "fcf_conversion": {"fcf_conversion": 0},
  "ebitda": 0,
  "ev": {"ev": 0},
  "ev_ebitda": 0,
  "cash_runway": {"cash_runway_months": 0}
}
```

**Important caveats -- read before trusting the numbers:**
- **Piotroski F-Score is scored out of `max_possible`, not always out of 9.**
  Any signal that can't be computed from what the filing actually reports is
  `null` and listed in `missing_signals` -- never guessed. A score with several
  missing signals is lower-confidence than the same raw number with none missing.
- **ROIC's NOPAT assumes a flat 21% effective tax rate** (US federal statutory),
  not the filer's actual effective rate -- it's flagged as an estimate in the
  `note` field, not a filed figure.
- **Line items use a standard_concept lookup first, falling back to a
  case-insensitive label-text search** when the standard concept is missing
  or unreliable for a given filer. Only verified-live standard_concept names
  (Revenue, OperatingIncomeLoss, NetIncome, Assets, CurrentAssetsTotal,
  CurrentLiabilitiesTotal, Liabilities, LongTermDebt, AllEquityBalance) are
  hardcoded; cash flow and shares outstanding rely on the label fallback only.
- **XBRL dimensional-breakdown rows (segment/member sub-lines) are excluded**
  from both lookup paths -- matching one of these instead of the consolidated
  total was confirmed to produce garbage for periods where a segment wasn't
  separately broken out.
- `cash_runway` only returns a value for companies with **negative** net
  income (cash burners) -- it's explicitly null with a note otherwise.

---

## market_mood.py

VIX and CNN's Fear & Greed Index in one call -- backs swing-trade-scanner's
Down Tape Protocol. No API key, no input parameters.

```
uv run --with yfinance --with fear-and-greed python3 shared/market_mood.py
```

**Input:** `{}` (empty -- no parameters needed)

**Output:**
```json
{
  "vix": {"value": 18.4, "regime": "normal"},
  "fear_greed": {"value": 31, "description": "Fear", "last_update": "...", "regime": "fear"}
}
```
`vix.regime`: `normal` (<=25) / `elevated` (>25) / `fear_mode` (>30).
`fear_greed.regime`: `extreme_fear` (<=25) / `fear` (<=45) / `neutral` (<=55) /
`greed` (<=75) / `extreme_greed` (>75). Either key can independently be
`{"error": "..."}` if that specific source fails -- the other still returns.

---

## sentisense_sentiment.py

Reddit-sourced ticker sentiment via the licensed SentiSense API. Replaces
the project's original `reddit_sentiment.py` (removed -- Reddit's own OAuth
app registration closed to new self-serve apps in late 2025).

```
uv run --with requests python3 shared/sentisense_sentiment.py
```

**Input:**
```json
{"ticker": "GSAT", "days": 7, "api_key": "ss_live_..."}
```
`api_key` can come from `SENTISENSE_API_KEY` env var instead. `days` (1-365,
default 7) is the lookback window.

**Output:**
```json
{
  "status": "ok",
  "ticker": "GSAT",
  "reddit_documents": { "...": "raw SentiSense /documents response" },
  "sentiment_series": { "...": "raw SentiSense /metrics/sentiment response" },
  "summary": {
    "document_count": 0,
    "documents_mentioning_ticker": 0,
    "positive": 0, "negative": 0, "neutral": 0,
    "average_sentiment_label": "positive",
    "note": "..."
  }
}
```

**Important caveats:**
- **A single Reddit post's sentiment array can carry dozens of unrelated
  tickers** -- this script filters to entries whose `ticker` field matches
  the one queried, case-insensitively, before rolling up. `document_count`
  is the raw count returned; `documents_mentioning_ticker` is how many
  actually reference the queried ticker in their sentiment breakdown --
  these can differ.
- **No post/headline text is returned** -- SentiSense's response includes a
  `url` but not title or body text. This is a sentiment signal only, not
  something to read for content.
- **Zero documents in the window is explicitly not a neutral signal** --
  it means no chatter was found, not that sentiment was neutral. The
  `summary.note` field flags this case so it isn't silently misread.
- Free tier: 1,000 requests/month, 30/min. Call this on pipeline survivors
  only (after News Quality, Volume/Liquidity, Chart Behavior pass), not on
  every raw scan candidate -- see swing-trade-scanner's SCAN MODE.

---

## perplexity_verify.py

Independent web-source claim verification with citations, via Perplexity's
Sonar API. Paid per-call.

```
uv run --with requests python3 shared/perplexity_verify.py
```

**Input:**
```json
{
  "query": "Has Globalstar signed a deal with Apple for emergency satellite service? What are the confirmed terms?",
  "api_key": "...",
  "model": "sonar"
}
```
`api_key` can come from `PERPLEXITY_API_KEY` env var instead. `model`
defaults to `"sonar"`.

**Output:**
```json
{"status": "ok", "answer": "...", "citations": ["https://...", "..."]}
```

The system prompt instructs the model to answer only from citable sources
and to say plainly if a claim can't be independently confirmed, rather than
inferring or guessing.
