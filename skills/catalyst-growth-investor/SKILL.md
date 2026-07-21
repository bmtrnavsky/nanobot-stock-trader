---
name: catalyst-growth-investor
description: "Mid-horizon (3 month to 3 year) growth position evaluator for U.S. small/mid-cap companies riding a durable catalyst -- not a quick swing trade, not a 10-year compounder bet. Three modes: SCAN (screen a universe for growth-with-catalyst candidates), DEEP EVAL (full evaluation of a specific ticker's catalyst durability, growth trajectory, and insider conviction), and POSITION CHECK (re-underwrite an open growth position after an earnings print or news event). Use this skill When the user asks about a growth story with legs, a multi-quarter thesis, insider buying as a signal, or a stock that's too slow for the swing scanner but too early-stage or story-driven for the long-term quality framework."
---

# Catalyst Growth Investor -- Mid-Horizon Growth-With-Catalyst Framework

## Purpose

Fill the gap between `swing-trade-scanner` (1-90 day EP trades) and `longterm-quality-investor` (10-year compounders). This skill evaluates companies riding a **durable, multi-quarter catalyst** -- a new product cycle, a regulatory tailwind, a contract ramp, a market share inflection -- where the thesis plays out over months to a few years, not days and not a decade.

**The core question:** Is there a real, verifiable catalyst driving above-market growth right now, is it early enough in its life to still have room to run, and are the people closest to the business (insiders) putting real money behind it?

**Philosophy:** This is story-plus-numbers investing, not pure quality compounding and not pure momentum. A good catalyst-growth candidate has both a credible narrative AND the financial trajectory to back it up. Growth without financial confirmation is speculation. Financial strength without a catalyst is just `longterm-quality-investor`'s territory.

**Holding window:** 3 months to 3 years -- long enough for the catalyst to play out and get recognized, short enough that you're not making a 10-year bet on a thesis that might be a 2-year story.

**Universe:** U.S.-listed public companies, $100M-$5B market cap (wider than the other two skills -- growth catalysts show up at more sizes). No fixed price band; a catalyst can hit a $4 stock or a $180 stock equally.

---

## Data Sources (Use in This Priority Order)

This skill has real, tested scripts in `../../shared/` (shared across swing-trade-scanner, longterm-quality-investor, and catalyst-growth-investor). Prefer these over web search wherever they cover the need.

- **Live quote, growth metrics, insider/institutional ownership, analyst targets:**
  `uv run --with yfinance python3 ../../shared/fetch_stock_data.py`
- **Structured financials (cash runway for burners, debt load, revenue/margin trend across actual filed periods):**
  `uv run --with edgartools python3 ../../shared/financials.py`
  `fetch_stock_data.py` only returns a single snapshot for revenue/earnings growth -- it can't show a multi-quarter trend, and it has no burn-rate data for cash runway. Use this for Component D (Financial Foundation) and anywhere Component B references a "4-6 quarter" trend.
- **Candidate screening (market cap, sector, industry filters):**
  `uv run --with yfinance python3 ../../shared/screen_stocks.py`
- **SEC filings (10-K, 10-Q, 8-K catalyst confirmation, contract disclosures):**
  `uv run --with edgartools python3 ../../shared/sec_filings.py`
- **Reddit sentiment (discovery/confirming signal only, never a decision input):**
  `uv run --with praw python3 ../../shared/sentisense_sentiment.py`
  (currently unavailable -- Reddit closed self-serve OAuth app creation in Nov 2025. Skip this source rather than block on it; it was never a decision input here anyway.)
- **Independent catalyst verification (does this claim hold up outside company PR):**
  `uv run --with requests python3 ../../shared/perplexity_verify.py`

For qualitative catalyst research the scripts don't cover -- competitor moves, TAM sizing commentary, analyst notes not captured in `fetch_stock_data.py` -- fall back to web search.

**Critical rule:** Never fabricate financial data or catalyst details. If a figure or claim cannot be confirmed from a live source, flag it as "UNVERIFIED -- confirm before acting."

---

## Mode Selection

- **SCAN MODE** -- the user asks to screen a sector or universe for growth-with-catalyst candidates.
- **DEEP EVAL MODE** -- the user provides one ticker and a catalyst (or asks to find one) and wants a full evaluation.
- **POSITION CHECK MODE** -- the user owns this and wants a re-underwrite after earnings or news.

If the mode is ambiguous, ask before proceeding.

---

## HARD REJECT RULES (Auto "No" for New Positions)

Any hit = reject. For existing positions, immediate high-priority review.

| # | Rule | Rationale |
|---|---|---|
| 1 | Catalyst is a single press release with no independent confirmation | Unverified catalysts are the #1 source of growth-story failures |
| 2 | Going concern language in latest 10-K or 10-Q | Business may not survive to see the catalyst play out |
| 3 | Insiders net selling into the catalyst narrative | Conviction test failure -- the people who know most aren't buying their own story |
| 4 | Revenue growth decelerating for 2+ consecutive quarters despite catalyst claims | The catalyst isn't showing up in the numbers |
| 5 | Reverse stock split within 24 months | Same rationale as longterm-quality-investor -- strong negative signal |
| 6 | Average daily dollar volume < $1M | Execution risk, can't size a position safely |
| 7 | Active disclosed SEC or DOJ investigation | Credible threat that overrides any catalyst thesis |
| 8 | Catalyst already fully priced in (stock up >100% on the news with no fundamental confirmation yet) | Chasing a story after the easy money is gone |
| 9 | Chronic dilution (>8% annual share count increase) funding the "growth" | Growth bought with shareholder dilution isn't real growth |

---

## HARD INCLUSION RULES (Minimum to Proceed)

- Revenue growth >=15% YoY, or a clearly identified inflection point with credible forward guidance supporting acceleration
- Catalyst is independently verifiable (SEC filing, signed contract, regulatory approval, disclosed partnership) -- not just a company press release or Reddit rumor
- Market cap $100M-$5B
- Average daily dollar volume >=$1M
- No hard reject conditions present
- Insider transactions in the last 6 months are net neutral or net buying (net heavy selling is a disqualifier, see Hard Reject #3)

---

## MODE 1: SCAN MODE

**Goal:** Screen a sector or universe for candidates with both growth acceleration and a real catalyst. Surface for Deep Eval.

### Scan Process

1. Call `screen_stocks.py` with market cap and sector/industry filters matching the user's ask (e.g. `{"market_cap_min": 100000000, "market_cap_max": 5000000000, "sector": "Technology", "count": 25}`)
2. For each candidate, pull `fetch_stock_data.py` fields: `fundamentals` (revenue_growth, earnings_growth), `insiders`, `institutional`, `analyst`
3. Filter for revenue growth >=15% YoY and check for a news-verifiable catalyst (quick `perplexity_verify.py` pass or web search per candidate)
4. Apply hard reject rules
5. Rank by: catalyst verifiability > growth acceleration > insider buying signal

### Scan Output Format

```
CATALYST GROWTH SCAN -- [DATE] -- [Sector/Universe]
========================================

PASS TO DEEP EVAL:
- [TICKER]: $[mkt cap] | Rev growth [X%] YoY | Catalyst: [one-line description] | Insiders: [buying/neutral]
  Why it passes: [One sentence]

WATCH:
- [TICKER]: [What's missing -- catalyst unconfirmed, growth not yet accelerating, etc.]

REJECT:
- [TICKER]: [Specific hard reject rule -- no hedging]

========================================
```

After output, ask: "Want the full Deep Eval on any of the passes?"

---

## MODE 2: DEEP EVALUATION MODE

**Goal:** Produce a BUY / WATCH / REJECT decision on a specific catalyst-growth thesis with position sizing guidance appropriate to a 3-month-to-3-year hold (not swing-trade position sizing, not buy-and-hold sizing).

### Step 0: Data Pull

Pull via `fetch_stock_data.py` (all field groups): price, fundamentals, dividends (if any), insiders, institutional, analyst.

If the user hasn't specified the catalyst, search recent news and SEC filings (8-Ks especially) for what's driving the story.

### Component A: Catalyst Verification (35% weight) -- Gate Layer

1. **Source the catalyst independently.** Confirm via SEC filing (8-K, 10-Q contract disclosure), signed/announced partnership terms, regulatory decision, or `perplexity_verify.py` cross-check against independent reporting -- not just the company's own press release.
2. **Durability:** Is this a one-time event (single contract, single approval) or a multi-quarter/multi-year driver (product cycle, regulatory tailwind, structural market shift)? One-time events belong in the swing scanner, not here.
3. **Stage:** Early (thesis not yet in numbers, most upside ahead) / Confirming (first quarter or two showing up in results) / Mature (already several quarters of confirmation, market largely aware). Early and Confirming are the target zones for new positions.
4. **Competitive response risk:** Can a competitor neutralize this catalyst quickly? Patent protection, exclusive contract terms, regulatory moat, or first-mover lead time all matter here.

### Component B: Growth Trajectory (25% weight)

1. **Revenue growth trend:** Pull 4-6 quarters via `financials.py`. Accelerating is the strongest signal; flat-but-elevated is acceptable if the catalyst is still early-stage; decelerating despite catalyst claims is a red flag (see Hard Reject #4).
2. **Earnings growth vs revenue growth:** Is growth translating to the bottom line, or is this top-line-only with margin compression?
3. **Forward guidance:** What has management explicitly guided to, and does the current run-rate support it?
4. **Analyst estimate revisions:** Rising estimates (via `fetch_stock_data.py` analyst fields) confirm the market is starting to recognize the catalyst; falling estimates despite a "growth story" narrative is a red flag.

### Component C: Insider and Institutional Conviction (20% weight)

1. **Insider transactions (last 6-12 months):** Net buying, especially open-market purchases (not just option exercises) from multiple insiders, is a strong positive signal. Net selling is a hard reject trigger.
2. **Institutional ownership trend:** Increasing institutional stake suggests smart money is accumulating; heavy institutional exit despite a bullish narrative is a caution flag.
3. **Ownership concentration:** Reasonable insider ownership (skin in the game) without being so concentrated that a single holder's exit could crater the stock.

### Component D: Financial Foundation (15% weight)

Lighter-weight than `longterm-quality-investor`'s full financial strength component, but the company still needs to survive to see the catalyst play out:

1. Cash runway: enough cash + credible path to breakeven or profitability to not need a dilutive raise mid-thesis
2. Debt load: not so leveraged that the catalyst's upside gets eaten by interest expense
3. No hard reject conditions (going concern, chronic heavy dilution)

### Component E: Valuation Context (5% weight)

Not the primary decision driver here (unlike `longterm-quality-investor`), but sanity-check: is the catalyst already priced in? Compare current valuation multiple to where the stock traded before the catalyst became known, and to sector peers.

### Composite Scoring

Weight as: Catalyst Verification 35, Growth Trajectory 25, Insider/Institutional Conviction 20, Financial Foundation 15, Valuation Context 5 (100 total).

**Score interpretation:**
- >=65: Strong BUY candidate (if no hard reject conditions)
- 50-64: WATCH (specify what needs confirmation)
- <50: REJECT

### Deep Eval Output Format

```
CATALYST GROWTH EVALUATION -- [TICKER] | [COMPANY NAME]
========================================
Date: [DATE] | Price: $[X] | Market Cap: $[X]M

DECISION: [BUY / WATCH / REJECT]
Composite Score: [X/100]
Confidence: [High / Medium / Low]
Catalyst Stage: [Early / Confirming / Mature]

----------------------------------------
COMPONENT SCORES:
Catalyst Verification:     [X/35] -- [Source: independently confirmed / company-only, Durability: one-time/multi-quarter, Stage: Early/Confirming/Mature]
Growth Trajectory:         [X/25] -- [Rev growth: X% (accelerating/flat/decel), Earnings growth: X%, Estimate revisions: up/flat/down]
Insider/Institutional:     [X/20] -- [Insider txns: net buy/neutral/sell, Institutional trend: accumulating/flat/exiting]
Financial Foundation:      [X/15] -- [Cash runway: X quarters, Debt/EBITDA: Xx, Dilution risk: low/moderate/high]
Valuation Context:         [X/5]  -- [Current multiple vs pre-catalyst: X, vs sector peers: X]

----------------------------------------
CATALYST DETAIL:
[3-5 sentences. What exactly is driving this, how was it verified, why is it durable rather than one-time, what could kill it.]

GROWTH TRAJECTORY:
[2-4 sentences on the numbers backing the story.]

INSIDER/INSTITUTIONAL SIGNAL:
[2-3 sentences. Specific transactions if notable.]

----------------------------------------
THESIS (if BUY or WATCH):
[3-5 sentences. Why this catalyst plays out over the next 3 months to 3 years and what the market hasn't fully priced yet.]

KEY RISKS:
1. [Most important risk to the catalyst thesis -- be specific]
2. [Second risk]
3. [Third risk]

POSITION SIZING GUIDANCE:
[This is a 3-month-to-3-year hold -- larger position than a swing trade, smaller than a core long-term holding, sized to the catalyst's confidence level.]

METRICS TO MONITOR (quarterly):
- [Specific metric that confirms or breaks the catalyst thesis]
- [Specific metric #2]

If WATCH: [Exactly what confirms this to BUY]
If REJECT: [The specific durable reason -- no hedging]

========================================
Disclaimer: This is not financial advice. All investing involves risk. Do your own due diligence before taking any position.
```

---

## MODE 3: POSITION CHECK MODE

**Goal:** Re-underwrite an open catalyst-growth position after an earnings print, guidance update, or material news event. The question is whether the catalyst is still confirming, not whether the stock moved.

### Inputs Needed

- Ticker, entry price/date, original catalyst thesis, what triggered this check (earnings, news, scheduled review)

If the user doesn't provide these, ask before running.

### Re-Underwriting Checklist

1. **Catalyst still confirming?** Did the latest quarter show continued acceleration consistent with the original thesis, or is growth stalling?
2. **Stage progressed appropriately?** Early -> Confirming -> Mature should track roughly with time elapsed. Stalled progression is a yellow flag.
3. **Insiders still holding or adding?** New insider selling that wasn't part of a pre-scheduled plan is worth flagging.
4. **Guidance direction?** Raised, maintained, or cut -- and does the stock's move match the guidance direction (over/under-reaction)?
5. **Any hard reject conditions newly triggered?**
6. **Competitive response materialized?** Has a competitor moved to neutralize the catalyst since entry?
7. **Has the catalyst matured into "priced in" territory?** If the whole thesis has played out and the stock has re-rated to reflect it, this may be a graduation point -- either to a `longterm-quality-investor` re-evaluation if it's become a genuine compounder, or a trim/exit if the catalyst's edge is now gone.

### Decision Table

| Signal | Action |
|---|---|
| Catalyst confirming on schedule, guidance raised or maintained | Hold; consider adding if not already full-sized |
| Single-quarter miss, catalyst thesis structurally intact | Hold; monitor next quarter closely |
| Growth stalling, catalyst stage not progressing | Trim; set a hard deadline for re-confirmation |
| Competitor materially neutralized the catalyst | Sell |
| Catalyst fully played out, stock re-rated, no new catalyst identified | Trim/exit -- graduate to longterm-quality-investor eval if fundamentals now support a compounder thesis, otherwise take the win |
| Insiders selling heavily outside a pre-scheduled plan | Trim; investigate before adding further |
| New hard reject condition triggered | Sell immediately |

### Position Check Output Format

```
POSITION CHECK -- [TICKER] | [COMPANY NAME]
========================================
Entry: $[X] on [date] | Days held: [X] | Current: $[X] | P&L: [+/-X%]
Trigger for this check: [Earnings / News / Scheduled review]

DECISION: [HOLD / ADD / TRIM / SELL]
Confidence: [High / Medium / Low]
Catalyst Stage: [Early / Confirming / Mature / Played Out]

----------------------------------------
CATALYST STATUS: [CONFIRMING / STALLING / BROKEN / FULLY PRICED IN]

Growth trend: [X% current vs X% at entry] -- [accelerating/flat/decelerating]
Guidance: [Raised / Maintained / Cut] since entry
Insider activity since entry: [Net buy / Neutral / Net sell]
Competitive response: [None material / Emerging / Materialized]
New risk factors: [None / list]
Hard reject conditions: [None / flag]

----------------------------------------
RECOMMENDATION:
[3-5 sentences. Direct. What to do and why. If trim: how much. If sell: what broke.]

UPDATED MONITORING METRICS:
- [Metric to watch next quarter]
- [Metric to watch next quarter]
========================================
Disclaimer: This is not financial advice. All investing involves risk. Do your own due diligence before taking any position.
```

---

## Critical Rules

- **Never fabricate financial data or catalyst details.** If a claim can't be confirmed from a live source, flag as UNVERIFIED.
- **A company press release is not catalyst verification.** Confirm independently before this graduates past WATCH.
- **Hard reject rules have no exceptions.**
- **Insider selling is a real signal here, not noise.** Unlike a pure quality-compounder framework where founder diversification sales are routine, in a catalyst-growth thesis, net insider selling into the story undercuts the whole premise.
- **Reddit and social sentiment are discovery tools only.** Zero weight in any BUY/HOLD/SELL decision.
- **Be direct.** State the decision and the specific reason. No hedging.
- **Know the difference between this skill and the other two.** One-time pop with no durability -> swing-trade-scanner. Proven 10-year moat with no active catalyst -> longterm-quality-investor. Multi-quarter catalyst with growth to match -> here.
- **Prefer the tested scripts in `../../shared/` over web search wherever they cover the need.**

