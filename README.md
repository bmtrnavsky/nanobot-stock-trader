# nanobot-stock-trader

**Free, open-source stock research skills for AI agents** -- built for Nanobot, Claude, or any agent runtime that can call a skill file and run Python via `uv run`. No paid data sources required for the core layer, no execution/brokerage integration, and no black-box scoring -- every rule is written out in plain markdown so you can read exactly how a decision gets made before you trust it.

This is a **decision-support toolkit, not a trading bot.** Nothing here places trades. Each skill pulls live data, runs it through a documented rules-based pipeline, and hands back a structured BUY / WATCH / PASS (or REJECT) decision with the reasoning shown -- you still pull the trigger.

## Why this exists

Most "AI stock bot" repos on GitHub are either black-box ML predictors or automated execution bots with real money risk baked in. This project is neither. It's a set of **agent skills** -- the same primitive Claude and Nanobot use for reusable, composable capabilities -- that encode three distinct, well-known investing methodologies into a disciplined, repeatable pipeline an AI agent can run consistently, every time, without emotion or shortcuts.

If you've ever wanted an AI agent that evaluates a stock the same rigorous way twice in a row instead of freestyling a different answer each time you ask, that's what this is for.

## What's here

### Skills (`skills/`)

Three independent investor-facing skill files, each a complete markdown-based framework an AI agent reads and follows, plus a shared-library stub. Use one, two, or all three investor skills depending on your investing style.

| Skill | Holding Window | Methodology | Best for |
|---|---|---|---|
| **[swing-trade-scanner](skills/swing-trade-scanner/SKILL.md)** | 1-90 days | Qullamaggie Episodic Pivot (EP) | Small-cap catalyst-driven swing trades: gap-and-go setups after a major news catalyst |
| **[catalyst-growth-investor](skills/catalyst-growth-investor/SKILL.md)** | 3 months-3 years | Catalyst-confirmed growth investing | Multi-quarter growth stories with a durable, verifiable catalyst -- too slow for a swing, too early for a 10-year thesis |
| **[longterm-quality-investor](skills/longterm-quality-investor/SKILL.md)** | 10+ years | Buffett / Akre / Terry Smith / Nick Sleep quality-compounder framework + Piotroski F-Score | Small/mid-cap buy-and-hold compounders, including a dedicated Dividend Eval mode for durable dividend payers |
| **[stock-data](skills/stock-data/SKILL.md)** | N/A | Shared script library | Not directly invokable -- the data layer the three investor skills above call into. Documented separately so agent skill-loaders don't try to run it standalone. |

Each investor skill includes:
- Hard reject rules (automatic disqualifiers, no exceptions)
- Hard inclusion rules (minimum bar to even be considered)
- A weighted, multi-component scoring rubric
- Multiple operating modes (scan a universe / deep-evaluate one ticker / monitor an open position)
- A fully structured output template so every evaluation looks the same and is easy to compare across tickers

`swing-trade-scanner` specifically hard-filters to a **$3-$20 price range** with a **$1B-$5B market-cap gray zone** (evaluated, but grade capped at A, never A+, since repricing power weakens with size) -- see the skill file for the full Layer 2 liquidity rules.

### Shared data layer (`shared/`)

All three investor skills call the same scripts for live data instead of relying on an LLM's training-data memory of stock prices (which is always stale) or unstructured web search (which is slow and inconsistent to parse):

- **`fetch_stock_data.py`** -- price, fundamentals, dividend history, insider transactions, institutional holders, analyst actions. Powered by `yfinance`, free, no API key.
- **`screen_stocks.py`** -- candidate screening by market cap, price, sector, dividend yield, or predefined categories (small caps, day gainers, most actives). Powered by `yfinance`'s `EquityQuery`/`screen()`, free.
- **`sec_filings.py`** -- recent SEC filings, Form 4 insider transactions, going-concern language detection. Powered by `edgartools`, free, MIT licensed, requires only a name+email identity string per SEC's fair-access policy (no account, no key).
- **`financials.py`** -- structured balance sheet, income statement, cash flow, debt/equity, and cash runway (for cash-burning companies) straight from SEC filings. Powered by `edgartools`, same identity-string requirement as `sec_filings.py`. Used where `fetch_stock_data.py` doesn't have an equity or burn-rate figure.
- **`market_mood.py`** -- VIX and CNN Fear & Greed Index in one call, used by `swing-trade-scanner`'s Down Tape Protocol to gate setups during risk-off market conditions. Powered by `yfinance` and the `fear-and-greed` package, free.
- **`sentisense_sentiment.py`** -- Reddit-sourced ticker sentiment via the SentiSense API, used strictly as a confirmation/discovery signal on candidates that already passed earlier pipeline layers, never as a standalone decision input. Licensed, read-only financial-data API; free tier is 1,000 requests/month, 30/min. Replaces the project's original `reddit_sentiment.py` (removed -- Reddit's own OAuth app registration closed to new self-serve apps in late 2025).
- **`perplexity_verify.py`** -- independent-source claim verification (e.g. "did company X actually sign this partnership") with citations. Powered by Perplexity's Sonar API, paid per-call (cheap, roughly $1 per million tokens plus a small request fee).

Every script follows the same interface: **pipe JSON to stdin, get JSON back on stdout.** No CLI flags, no argparse -- trivial for an agent to call via `uv run --with <package> python3 script.py`.

See [shared/SCRIPTS.md](shared/SCRIPTS.md) for the full input/output field reference for each script.

## Quick start

1. Clone this repo (or just the `skills/` and `shared/` folders) into wherever your agent looks for skills.
2. Point your agent's skill loader at one of the three investor `SKILL.md` files, or all three. `stock-data/SKILL.md` doesn't need to be loaded directly -- it's referenced by the others.
3. Set up credentials only for the scripts you need:
   - `fetch_stock_data.py` and `screen_stocks.py` need nothing -- `yfinance` is unauthenticated.
   - `sec_filings.py` and `financials.py` need an identity string (your name and email, per SEC's fair-access policy -- not a real account).
   - `market_mood.py` needs nothing -- unauthenticated.
   - `sentisense_sentiment.py` needs a SentiSense API key.
   - `perplexity_verify.py` needs a paid Perplexity API key.
4. Ask your agent something like *"scan for swing trade setups"*, *"deep-evaluate ticker XYZ as a long-term hold"*, or *"is this a good catalyst growth story"* -- the relevant skill and scripts take it from there.

```bash
echo '{"tickers": ["AAPL", "GSAT"]}' | \
  uv run --with yfinance python3 shared/fetch_stock_data.py

echo '{"market_cap_min": 50000000, "market_cap_max": 2000000000, "price_min": 5, "price_max": 25}' | \
  uv run --with yfinance python3 shared/screen_stocks.py

echo '{"ticker": "GSAT", "checks": ["recent_filings", "insider_form4", "going_concern"], "identity": "Your Name your.email@example.com"}' | \
  uv run --with edgartools python3 shared/sec_filings.py
```

Credentials can be passed in the JSON payload or set as environment variables (`EDGAR_IDENTITY`, `SENTISENSE_API_KEY`, `PERPLEXITY_API_KEY`) -- never hardcoded in the scripts.

## Design notes

- Every ticker-level failure returns `{"error": "..."}` for that ticker rather than failing the whole batch.
- `screen_stocks.py` filters to NYSE (`NYQ`) + Nasdaq (`NMS`) by default -- Yahoo's `region` field was tested and found to leak foreign OTC/pink-sheet tickers even when scoped to "us"; `exchange` filtering is the real, working restriction.
- Dividend CAGR/consecutive-increase logic compares same-quarter year-over-year on the raw payment series, not calendar-year resampling -- resampling was tested and found to distort partial first/last years into false "decreases."
- `sentisense_sentiment.py`'s ticker-level sentiment doesn't distinguish which subreddit a post came from, unlike the old subreddit-by-subreddit approach -- it counts as one source type in cross-source confirmation, not several.
- Data lag: Yahoo Finance price/volume is roughly 15-20 minutes delayed; insider trades lag 2-3 days (SEC filing lag); short interest lags roughly 2 weeks (FINRA reporting cycle).
- Each investor skill is fully self-contained -- you can install just one if you only care about swing trading, or just the long-term compounder framework, without needing the others.

## FAQ

**Is this financial advice?**
No. This is a data-fetching and decision-framework toolkit. Nothing here recommends you buy, sell, or hold anything. Every skill ends its output with a disclaimer, and you should treat every BUY/WATCH/PASS as a structured opinion to evaluate, not an instruction to follow.

**Does this execute trades?**
No. There is no brokerage integration anywhere in this repo. It fetches data and evaluates it. You place trades yourself, wherever you already do.

**What's an Episodic Pivot?**
A methodology popularized by trader Kristjan Qullamaggie for identifying small-cap stocks that gap up sharply on a major catalyst after a period of neglect, with potential to keep drifting higher for weeks to months as the market re-prices the stock. The `swing-trade-scanner` skill implements a full 5-layer pipeline (news quality, volume/liquidity, chart behavior, fundamentals, risk management) built around this pattern.

**What's the Piotroski F-Score?**
A 9-point financial-strength checklist (profitability, leverage, liquidity, and operating efficiency signals) developed by accounting professor Joseph Piotroski to separate genuinely improving companies from value traps. The `longterm-quality-investor` skill uses the full 9-point score as a hard financial-strength gate.

**Why three separate investor skills instead of one?**
Because a 2-day swing trade, a 6-month growth story, and a 10-year compounder require genuinely different evaluation criteria, different data emphasis, and different risk frameworks. Bolting all three into one skill would mean constant mode-confusion. Each skill is scoped to one holding-period regime and does it thoroughly.

**Why is `stock-data` a separate skill folder if it's not directly invokable?**
So agent skill-loaders that scan the `skills/` folder for capabilities have a place to find documentation on the shared scripts without accidentally treating it as a fourth standalone evaluation mode.

**Can I use just the shared scripts without the skills?**
Yes. `shared/` is fully independent -- pipe JSON in, get JSON out, use it in any agent or script of your own.

## Not financial advice

This is a data-fetching and evaluation toolkit, not a trading system, and not a substitute for your own due diligence. Nothing in this repository recommends any buy/sell/hold decision. All investing and trading involves risk, including loss of principal.

## License

MIT. See individual script headers for third-party library attributions (`yfinance`, `edgartools`, SentiSense API, Perplexity Sonar API).
