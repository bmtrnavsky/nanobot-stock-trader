---
name: swing-trade-scanner
description: "Episodic pivot swing trade scanner and evaluator for 1-90 day holds. Three modes: (1) SCAN -- proactively scans market news and Reddit for EP setups, runs each candidate through the full 5-layer pipeline, and delivers a ranked shortlist -- use when you say what's popping, find me setups, anything worth looking at, scan for trades; (2) EVALUATE -- full 5-layer evaluation of a specific ticker plus news -- use when you say check this ticker, is X worth a trade, is this a good swing trade, analyze this stock, or provide a ticker with or without news; (3) EXIT MONITOR -- evaluates whether to hold, tighten, take partial profits, or exit an open position -- use when you say should I hold X, check my position in X, is it time to sell X. Built on Qullamaggie episodic pivot methodology for small-cap catalysts. Uses scripts/ for live data (yfinance, SEC EDGAR, Reddit) instead of web search where possible."
---

# Swing Trade Scanner -- Episodic Pivot Framework

## Purpose
Evaluate any ticker + news catalyst through a disciplined 5-layer pipeline and deliver a clear, actionable trade decision. No noise, no hedging. A grade and a plan or a hard pass with a reason.

**Holding window:** 1-90 days (swing, not day trade, not buy-and-hold)
**Primary setup:** Episodic Pivot (EP) -- gap up >= 8-10% on massive volume after a major catalyst, often after a period of neglect, with potential to drift higher for weeks/months.

## Data sources -- use these before web search

This skill has real, tested scripts in `../../shared/` (shared
across all three trading skills). Prefer these over web search for
anything they cover -- they're faster, cheaper, and give structured
data instead of parsed page text.

- **Price, volume, float, fundamentals, insiders, analyst actions:**
  `uv run --with yfinance python3 ../../shared/fetch_stock_data.py`
  (pipe `{"tickers": [...], "fields": ["price","fundamentals","insiders","analyst"]}` to stdin)
- **Candidate screening (market cap, price range):**
  `uv run --with yfinance python3 ../../shared/screen_stocks.py`
- **SEC filings, insider Form 4s, going-concern check:**
  `uv run --with edgartools python3 ../../shared/sec_filings.py`
  (needs an identity string -- set one up if not already configured)
- **Structured financials (balance sheet, income statement, cash flow, debt/equity, cash runway for actual burners):**
  `uv run --with edgartools python3 ../../shared/financials.py`
  (used sparingly here -- Layer 4 is a red-flag filter, not a deep dive; reach for this only for Debt/Equity and Cash runway, which `fetch_stock_data.py` can't provide)
- **VIX + Fear & Greed Index (Down Tape Protocol):**
  `uv run --with yfinance --with fear-and-greed python3 ../../shared/market_mood.py`
- **Reddit sentiment/discovery:**
  `uv run --with praw python3 ../../shared/reddit_sentiment.py`
  (needs Reddit app credentials -- currently unavailable; Reddit closed self-serve OAuth app creation in Nov 2025 and personal-use apps aren't getting approved under the new process. Treat this source as offline for now -- don't block a scan on it, just skip it and note fewer source types were checked for Cross-Source Confirmation.)
- **Independent catalyst verification (M&A, partnership claims):**
  `uv run --with requests python3 ../../shared/perplexity_verify.py`
  (needs a Perplexity API key -- set one up if not already configured)

Still use web search for: real-time chart/VWAP context, practitioner
blogs (Stockbee, TradeThatSwing), days to next earnings, and anything
the scripts don't cover.

---

## Input

Accept any of the following as a starting point:
- **Ticker + news** -- "GSAT just announced a deal with Apple, check it"
- **Ticker only** -- "is this a good swing trade on ACMR" / "analyze this stock: ACMR" -> search for recent news first
- **Evaluate request** -- "is X worth a trade" / "is this a good swing trade" / "analyze this stock" -> full 5-layer evaluation
- **News scan request** -- "what's popping" / "find me setups" / "scan for trades" / "anything worth looking at today" -> full proactive scan including Reddit
- **Watchlist review** -- "run through my watchlist" -> evaluate each ticker in sequence

If only a ticker is provided with no news, search for recent catalysts before evaluating. If no significant catalyst found in last 5-10 trading days, note that and default to WATCH or PASS.

---

## The 5-Layer Pipeline

Work through all 5 layers in order. Do not skip layers even if early layers look strong. Each layer gates the next.

---

## LAYER 1: News Quality (Weight ~35%) -- Gate Layer

**Definition of Episodic Pivot catalyst:** A major, valuable event that causes a gap up >= 8-10% on massive volume, often after a period of neglect, with the potential for continued repricing (drift) over weeks/months.

### Research the catalyst
Use `sec_filings.py` (recent_filings check) plus web search to retrieve:
- The original press release or SEC filing (8-K)
- Counterparty identity (Fortune 100? Government agency? Unknown microcap?)
- Dollar value of the deal/contract vs. company's trailing twelve-month revenue
- Whether guidance was raised
- Whether approval/award is final or preliminary
- If the catalyst claim needs independent corroboration beyond company PR, use `perplexity_verify.py`

### Score News Quality 1-5

**Score 5 -- Game-changing:**
- Major partnership where deal = >= 25-50% of annual revenue or funds majority of capex (GSAT-Apple type)
- Fortune 100 or large government agency as counterparty
- FDA approval or pivotal positive trial for lead drug (not Phase 1, not partial)
- Huge earnings surprise: triple-digit EPS growth OR first profitability
- Guidance raised materially alongside beat

**Score 4 -- Strong:**
- Big contract win (real revenue, but < 25% of annual revenue)
- Major analyst upgrade with significant price target increase (not routine coverage initiation) -- check via `fetch_stock_data.py` analyst field
- High-credibility M&A rumor or partial acquisition with named acquirer
- Secondary catalyst confirming a Score 5 from prior weeks (follow-through news)

**Score 3 -- Moderate:**
- Sector theme ignition -- sympathy move from a sector leader's news
- Incremental product news with real but small contract
- Positive data readout that isn't the primary endpoint
- Earnings beat with modest guidance raise

**Score <= 2 -- Weak (AUTO PASS):**
- Generic PR with no hard numbers
- Small analyst mention or price target change with no fundamental catalyst
- Social media buzz with no filing or press release
- Insider buy (positive but not an EP catalyst)
- Vague partnership "MOU" or LOI with no dollar figures

**AUTO PASS RULE: If News Quality < 3, stop here. Output: PASS -- Catalyst too weak for EP setup. Do not continue evaluation.**

**BUYOUT AUTO PASS RULE: If the catalyst is a confirmed buyout or full acquisition at a stated premium, stop here regardless of news score. Output: PASS -- Confirmed buyout. Stock is priced to the deal; no drift edge exists. The gap is the event, not the beginning of a drift.**

**Borderline tie-breaker (3 vs 4):** If a catalyst is genuinely ambiguous between two adjacent scores, use this additive check to break the tie rather than guessing -- M&A/takeover rumor: +5, insider buying cluster: +4, analyst upgrade/downgrade: +3, "hearing that/sources say" chatter: +2, unusually high engagement/volume on the news itself: +2 bonus. This is a tie-breaker only, not a parallel scoring system -- the qualitative examples above remain the primary judgment.

---

## LAYER 2: Volume & Liquidity (Weight ~25%)

### Pre-catalyst baseline (fetch via fetch_stock_data.py price fields)
- **Price range:** **$3-$15 HARD FILTER** -- this is the target trading range for this skill's default configuration. Adjust to your own range if different, but auto-pass anything outside your configured range before running any other layer. No exceptions, no "exceptional catalyst" flex outside the range.
- **Market cap:** $50M-$1B (small enough for news to matter, large enough to be tradeable)
- **Average daily volume (30-50 day):** Minimum 300K shares; preferred >= enough for $1M-$5M daily dollar volume

### Catalyst-day volume (the signal)
Use `fetch_stock_data.py` price fields plus web search for today's or event-day trading data:
- **Relative Volume (RVOL):** Today's volume divided by 30-50 day average volume (both available from the script's `volume`/`avg_volume_3m` fields)
  - RVOL >= 5x: exceptional EP-level participation
  - RVOL 2.5x-5x: strong, meets EP threshold
  - RVOL 2x-2.5x: borderline -- proceed with caution, note it
  - RVOL < 2x: news likely priced in or ignored -> WATCH or PASS
- **Record/near-record volume:** Is today's volume among the highest in the last 6-12 months? EP setups often trade average daily volume in the first 15-30 minutes.
- **Dollar volume:** Price x volume on catalyst day should be >= $5M for adequate liquidity

### Confidence builders -- Layer 2 (these add conviction, not filters)

**Float size:**
Fetch the stock's float via `fetch_stock_data.py` (`float_shares` field) -- shares available for public trading, not total shares outstanding.
- Float < 10M shares: very low float -- small buy pressure moves price significantly, adds explosive upside potential. Flag as "Low float amplifier."
- Float 10M-20M shares: favorable -- still responsive to volume.
- Float 20M-50M shares: neutral -- standard small cap.
- Float > 50M shares: note it -- higher float means the catalyst needs to be proportionally stronger to move price.
Low float + high RVOL is one of the most powerful EP amplifiers. Always note the combination.

**ADV trend (pre-catalyst volume buildup):**
Check whether average daily volume was quietly increasing in the 10 days BEFORE the catalyst. Cross-reference with `fetch_stock_data.py` insiders field -- accumulation ahead of news sometimes shows in insider buying too.
- Volume gradually building before the news -> smart money was accumulating; they knew or suspected something. Strong confidence booster.
- Volume flat or declining before the catalyst, then explosive on the news day -> cleaner surprise EP; retail-driven. Still valid but different character.
- Note in the output: "Pre-catalyst volume: building / flat / declining"

### Liquidity red flags (auto-disqualifiers)
- Price < $3 or > $15 (outside your configured trading range -- hard stop, do not evaluate)
- Market cap > $5B (news won't move it enough for a swing)
- Average daily volume < 100K shares (can't get in/out cleanly)
- Bid/ask spread > 2% (slippage kills the trade)

---

## LAYER 3: Chart Behavior (Weight ~25%)

Search for chart data and recent price history. Look at both daily and weekly charts.

### A. Pre-catalyst structure (last 3-12 months, weekly + daily)

**Ideal EP structure:**
- Price was **flat, neglected, or in a long base** before the catalyst -> high EP potential, news reprices a neglected stock
- Multi-month consolidation or downtrend that "reset" the stock -> fresh buyers, no overhead resistance from recent buyers trapped above

**Warning signs:**
- Stock already in a **strong sustained uptrend** making runaway gaps late in the move -> exhaustion gap risk, not a breakaway
- Recent 100%+ move before the catalyst -> likely over-extended, drift edge weak
- Stock already near 52-week highs before the catalyst on no prior catalyst -> already discovered

### B. The gap day / first thrust

- **Gap size:** >= 8% for EP-tier consideration; >= 10% for strong EP
- **Day-1 close location:**
  - Bullish (gap-and-go): closes in **top half or top third** of the day's range
  - Bearish signal: closes at or near the bottom of the day's range -> buyers not in control
- **Volume:** Already checked in Layer 2 -- confirm it's meeting RVOL threshold

### C. Post-catalyst behavior (days 2-10 if evaluating after day 1)

**Bullish drift setup (news NOT fully priced in):**
- Price holds **above the top of the old range** (gap low)
- Tight flag or base forming -- low volatility, declining volume consolidation
- Each pullback finds support at or above gap-fill level
- Weekly: breakout from a multi-month base that is now holding

**Bearish (news fully priced in):**
- Price quickly fills most or all of the gap and sits back inside prior range
- High volume on down days after the catalyst (distribution)
- Failed to close above key resistance despite the catalyst

### Gap Classification (required output)
Classify as one of three types:
- **Breakaway from base** -- A+ setup, best for 3-90 day swings
- **Runaway mid-trend** -- B setup, shorter hold, tighter stop
- **Exhaustion gap** -- C/PASS, avoid or short side only

**Only Breakaway with hold above gap gets top priority for 3-90 day swings.**

### Confidence builders -- Layer 3 (these add conviction, not filters)

**VWAP hold on catalyst day:**
VWAP (Volume Weighted Average Price) represents the average price paid by everyone who traded that day, weighted by volume. If the stock closes above VWAP on the catalyst day, buyers who drove the volume are sitting on a profit -- they have no pressure to sell immediately, which supports continued drift.

- Close above VWAP at end of catalyst day -> buyers in control, thesis intact. Flag as "VWAP hold -- bullish."
- Close at or near VWAP -> neutral, watch next day.
- Close below VWAP -> sellers took over during the session. Warning sign even if price is still up on the day. Flag as "Below VWAP -- monitor carefully."
- Price reclaiming VWAP the day after a below-VWAP close -> recovery signal, can upgrade conviction.

Check by searching: "[ticker] VWAP [date]" or look at intraday chart context in financial data sources.

**Relative Strength vs. sector (pre-catalyst RS):**
Was the stock already outperforming its sector or the broader market in the 10-20 trading days BEFORE the catalyst? Pre-catalyst RS means institutional money was already accumulating -- the catalyst didn't create the interest, it confirmed it.

- Stock was quietly outperforming its sector for 2-4 weeks before the catalyst -> strong institutional backing. Flag as "Pre-catalyst RS -- institutional accumulation likely."
- Stock was in line with sector -> neutral.
- Stock was underperforming its sector before the catalyst -> the move is less likely to have institutional follow-through. Note it.

Check by searching recent price action relative to sector ETF or comparing chart to SPY/IWM.

**Combining the confidence builders:**
When multiple confidence signals align, they compound:
- Low float + RVOL 5x+ + VWAP hold + pre-catalyst RS = maximum conviction setup
- Missing one is fine -- missing two or more, grade accordingly
- Always note which confidence builders are present in the output, not just which are absent

---
## LAYER 4: Fundamentals / Ratio Filters (Weight ~10-15%)

This is a **red flag filter only** -- not a primary trigger. The goal is to avoid blowing up on a garbage balance sheet, not to find a value stock.

Pull via `fetch_stock_data.py`: P/E, forward P/E, price/sales, profit margin, revenue growth, cash, debt, free cash flow, short interest (`price` field group). Insider ownership % comes from the `institutional` field group (`pct_held_insiders`), not `insiders` -- the `insiders` field only returns transaction records, not an ownership percentage. Cash runway needs a burn-rate figure `fetch_stock_data.py` doesn't provide for profitable-adjacent companies; for clear cash-burners, pull `financials.py`'s `cash_runway` field instead (uses net income from the actual filing, not an estimate). Days to next earnings has no script source -- web search it, and don't present it next to the script-backed rows as if it came from the same place.

| Metric | Green | Yellow | Red Flag | Source |
|---|---|---|---|---|
| P/E (if profitable) | < 25 | 25-50 | > 100 or deeply negative | `fetch_stock_data.py` |
| Price/Sales | < 3 | 3-10 | > 15 (unless transformational catalyst) | `fetch_stock_data.py` |
| Debt/Equity | < 1.0 | 1.0-1.5 | > 1.5 | `financials.py` (`total_liabilities` / `stockholders_equity` -- `fetch_stock_data.py` has no equity field) |
| Revenue growth (YoY) | Positive + accelerating | Flat | Declining | `fetch_stock_data.py` |
| EPS trend | Growing or first profitability | Mixed | Deeply negative with no path | `fetch_stock_data.py` |
| Short interest | 5-30% (squeeze fuel) | < 5% (no squeeze) | > 35% (violent reversal risk) | `fetch_stock_data.py` |
| Cash runway (biotech/unprofitable) | >= 18 months | 12-18 months | < 12 months | `financials.py` `cash_runway` (null if company isn't burning cash) |
| Insider ownership | >= 10% (aligned) | 5-10% | < 3% | `fetch_stock_data.py` `institutional` field |
| Days to next earnings | > 14 days out | 7-14 days out | < 7 days out (binary event risk stacks on catalyst risk) | web search -- no script source |
| Recent price spike (prior 5 days) | Flat/normal | Up 5-15% | Up > 15% (catalyst may be chasing an already-extended move -- cross-reference Layer 3's "100%+ move = over-extended" warning) | web search / chart data |

**Flag red flags explicitly. Flag strong tailwinds (e.g., huge earnings beat + solid balance sheet) explicitly.**

One red flag doesn't auto-kill a trade if the catalyst is a 5 and chart is Breakaway. Multiple red flags = PASS regardless of catalyst quality.

---

## LAYER 5: Risk Management & Trade Plan (Weight ~5-10%)

Only reach this layer if the setup has passed layers 1-4 sufficiently.

### Position sizing
- Risk per trade: **1-2% of account** maximum
- No single position > **10% of portfolio**
- You do not need to specify your account size -- the skill outputs the framework and you apply it
- **ATR-based sizing (use this, not a fixed percentage stop):** Position Size = (Account x 1-2%) / (1.5-2x ATR). This normalizes risk across setups with very different volatility profiles -- a $7 stock with ATR of $1.50 requires a very different size than one with ATR of $0.40, even if the stop levels look similar on a chart. Always calculate and state ATR in the trade plan output.
## Cross-Source Confirmation

When the same ticker surfaces across multiple sources during a scan or evaluation, treat it as a meaningful signal -- not noise to deduplicate. Cross-source confirmation indicates multiple independent participant types are discovering the same setup, which is drift fuel for EP setups.

### What counts as independent confirmation

Source TYPE matters more than source COUNT. The same ticker appearing in five Reddit subs is one crowd echoing itself -- not five confirmations. True confirmation requires different participant types finding it independently.

**Counts as a separate source type:**
- SEC filing or verified press release (hard catalyst) -- check via `sec_filings.py`
- Practitioner blog (Stockbee, TradeThatSwing, SharePlanner)
- Forum with methodology focus (BearBullTraders, EliteTrader, r/RealDayTrading, r/SwingTrading) -- check via `reddit_sentiment.py`
- Retail momentum community (r/wallstreetbets, r/smallstreetbets, r/Daytrading) -- check via `reddit_sentiment.py`
- Traditional financial news (Benzinga, MarketBeat, financial wire services)
- Volume/RVOL data independently confirming unusual activity -- check via `fetch_stock_data.py`

**Does NOT count as separate confirmation:**
- Same news story syndicated across multiple financial sites (one catalyst, many publishers)
- Multiple Reddit subs discussing the same original WSB post (echo, not independent)
- Blog post that just summarizes the same press release already in the pipeline

### Scoring

| Unique source types | Label | Effect on grade/confidence |
|---|---|---|
| 1 | Single source | No adjustment |
| 2 | **Confirmed** | +5% confidence, note it |
| 3+ | **MULTI-SOURCE CONVERGENCE** | +10-15% confidence, flag prominently in output, elevate WATCH to BUY if other layers hold |

### Special case: Stockbee EP callout
If Stockbee (Pradeep Bonde) specifically names a ticker as an EP setup, treat it as equivalent to two independent confirmations on its own. He is the primary source of the methodology this skill is built on -- his callouts carry practitioner authority that Reddit mentions do not.

### Echo chamber warning
If a ticker is trending heavily across Reddit with no SEC filing, no practitioner blog mention, and no RVOL confirmation from a financial data source -- flag it explicitly as "Echo risk: retail-only signal, no independent confirmation." Do not boost confidence for echo activity. This is the pump risk pattern.

---
## Down Tape Protocol

Before running any scan or evaluation, check the broad market context for the day.

**Check market conditions:**
Search: `S&P 500 Nasdaq market today [current date]`

**If the broad market is down 2% or more:**

Activate Down Tape Mode:
- Suppress all B and C grade setups entirely -- do not surface them, do not mention them
- Surface **A+ grade setups only** -- stocks with a Score 5 catalyst, RVOL 5x+, gap >= 10%, Breakaway classification, and price bucking the tape
- If no A+ setups exist, deliver the "Today is not the day" output immediately

**VIX Elevated Mode (secondary filter -- check alongside tape direction):**
Pull current VIX via `uv run --with yfinance --with fear-and-greed python3 ../../shared/market_mood.py` whenever running a scan or evaluation -- more reliable than parsing search results for a number that drives hard gating rules.
- **VIX > 25:** Treat all B-grade setups as PASS regardless of tape direction. Require full A+ criteria for any trade. Institutional risk-off collapses the drift mechanism even on technically strong setups.
- **VIX > 30:** Down Tape Mode rules apply regardless of whether the broad market is up or down on the day. Fear at this level means even A-grade setups carry elevated failure risk -- flag this explicitly in the output.
- **VIX <= 25:** Normal grading rules apply.

Flag the VIX level in every scan output header.

**Fear & Greed Index (secondary sentiment check -- same `market_mood.py` call returns both VIX and this in one shot):**
Check alongside VIX, not as a replacement for it. This is a contrarian signal, unlike VIX.
- **Extreme Fear (0-25):** Genuinely bucking a fearful tape is a rarer, more credible signal than the same setup on a euphoric day -- treat as a confidence builder on an otherwise-qualifying A/A+ setup, note it explicitly: "Extreme Fear + qualifying setup -- contrarian tailwind."
- **Extreme Greed (75-100):** Everything looks like a setup when the market is euphoric -- raise the bar the same way elevated VIX does. Require full A+ criteria; treat B-grade setups with extra skepticism even if VIX itself is calm.
- **Neutral/Fear/Greed (25-75):** No adjustment, normal grading rules apply.

**Down tape A+ criteria (all must be met, no partial credit):**
- News Quality: Score 5 only (game-changing catalyst -- FDA approval, Fortune 100 deal, triple-digit earnings surprise)
- Price: Up on the day while broad market is down (bucking the tape is itself a signal)
- RVOL: 5x or higher (institutional participation confirmed despite market conditions)
- Gap: >= 10% (big enough to overcome market headwind)
- Chart: Breakaway from base only -- no runaway, no exhaustion

---
## "Today Is Not the Day" Output

Deliver this when the scan finds nothing that qualifies -- either because the market is down and no A+ setups exist, or because every candidate failed the pipeline:

```
SCAN RESULT -- [Date]
========================================
TODAY IS NOT THE DAY.

[If down tape:]
Market conditions: Broad market down [X]% today.
Down Tape Mode active -- A+ setups only.
Result: Nothing in the $3-$15 range is bucking the
tape with a Score 5 catalyst and RVOL 5x+ today.

[If flat/up tape with no setups:]
Market conditions: [Brief -- e.g., "flat tape, low volatility day"]
Candidates screened: [N]
Qualified after news filter: [N]
Result: Nothing passed the full pipeline today.

What failed:
- [TICKER]: [One sentence -- e.g., "Price $47, outside $3-$15 range"]
- [TICKER]: [One sentence -- e.g., "News score 2, generic PR with no hard numbers"]
- [TICKER]: [One sentence -- e.g., "RVOL 1.3x, already priced in"]

What to watch instead:
[1-2 names that came close -- not actionable today but worth
monitoring if conditions improve. Include why and what would
flip them to a BUY. Or "Nothing worth monitoring" if
everything was far off.]

Check back: [Suggest when -- e.g., "tomorrow morning after
tape stabilizes" or "watch for FDA announcement Thursday"]
========================================
```

The "Today is not the day" output is **never a failure** -- it's the skill doing its job. A day with no qualified setups is a day you didn't lose money on a bad trade.

---
## Final Output Format

Deliver this structured summary for every evaluation:

```
SWING TRADE EVALUATION -- [TICKER]
========================================

FINAL GRADE:     [A+ / A / B / C / PASS]
DECISION:        [BUY / WATCH / PASS]
CONFIDENCE:      [XX%]
HOLD WINDOW:     [X-XX days]
CROSS-SOURCE:    [Single source / Confirmed (2 source types) / MULTI-SOURCE CONVERGENCE (3+ types)]
Sources:         [List each source that flagged this ticker -- e.g., "SEC 8-K + Stockbee EP callout + r/SwingTrading"]
Market context:  [VIX level] | Fear & Greed: [value/label] | [Normal / Down Tape / Elevated VIX / Extreme Fear tailwind / Extreme Greed caution]

----------------------------------------
LAYER 1 -- NEWS QUALITY
Score: [X/5]
Catalyst: [type -- e.g., FDA approval, contract win, earnings]
Counterparty: [name + quality]
Deal size vs revenue: [X% of TTM revenue]
Guidance raised: [Yes / No / N/A]
Approval status: [Final / Preliminary / N/A]
Verdict: [One sentence summary]

----------------------------------------
LAYER 2 -- VOLUME & LIQUIDITY
Price: $[X] | Market cap: $[X]M
Avg daily volume (30d): [X]K shares
Catalyst-day volume: [X]M shares
RVOL: [X]x
Record volume: [Yes / No / Near-record]
Dollar volume (catalyst day): $[X]M
Float: [X]M shares | [Low float amplifier / Favorable / Neutral / High float]
Pre-catalyst ADV trend: [Building / Flat / Declining]
Liquidity: [Clean / Borderline / Red flag]
Verdict: [One sentence]

----------------------------------------
LAYER 3 -- CHART BEHAVIOR
Pre-catalyst structure: [Flat base / Neglected / Uptrend / Extended]
Gap size: [X%]
Day-1 close: [Top third / Middle / Bottom -- bullish/bearish]
VWAP hold (catalyst day): [Above VWAP / Neutral / Below VWAP]
Pre-catalyst RS vs sector: [Outperforming / Neutral / Underperforming]
Post-catalyst behavior: [Holding / Filling / Unknown -- if same day]
Gap classification: [Breakaway / Runaway / Exhaustion]
Confidence builders present: [List -- e.g., "Low float + VWAP hold + pre-catalyst RS"]
Verdict: [One sentence]

----------------------------------------
LAYER 4 -- FUNDAMENTALS
P/E: [X] | P/S: [X] | D/E: [X]
Revenue growth: [X% YoY]
Short interest: [X%]
Cash runway: [X months / N/A]
Days to earnings: [X days -- Green/Yellow/Red]
Recent 5-day spike: [X% -- Green/Yellow/Red]
Red flags: [List or "None"]
Tailwinds: [List or "None"]
Verdict: [One sentence]

----------------------------------------
LAYER 5 -- TRADE PLAN
Entry type: [Day 1 Confirmation / DRE / Intraday Retest]
Entry zone: $[X]-$[X]
ATR: $[X] | Position size per $10K: [X] shares at 1% risk / [X] shares at 2% risk
Stop: $[X] ([X]% below entry / [X]x ATR)
Trim 1 (1/3 at +10-15%): $[X]
Trim 2 (1/3 at +25-30%): $[X]
Trail remainder: below 10-day MA swing lows
Target 1: $[X] ([X]% gain, [X]:1 R:R)
Target 2: $[X] ([X]% gain, [X]:1 R:R)
Hold window: [X-XX days | Peak PEAD zone: 15-45 days | Re-evaluate at 60 days]
Key invalidation: [What kills the thesis -- e.g., gap fill + no reclaim]

========================================
WHY [BUY/WATCH/PASS]:
[2-4 sentences -- plain language, direct. State the strongest reason for
the decision and the biggest risk. No hedging. No "it depends."]
========================================
```
## SCAN MODE -- "What's Popping / Find Me Setups"

When you ask "what's popping," "scan for setups," "anything worth looking at today," or similar -- run a full proactive scan, evaluate each candidate through the 5-layer pipeline, and deliver a ranked shortlist. Don't just hand back a list of tickers to evaluate yourself.

### Step 1: Surface candidates

**Structured screen first:** run `screen_stocks.py` with `market_cap_min: 50000000, market_cap_max: 1000000000, price_min: 3, price_max: 15, predefined: "small_cap_gainers"` (or `day_gainers`, `most_actives`) to get a real, live, pre-filtered candidate pool inside your configured universe before any web search -- faster and cleaner than searching blind.

**Traditional news sources (fill gaps the screen doesn't cover -- FDA/contract catalysts don't always show up as "gainers" yet):**
```
Search 1: small cap stock gap up catalyst today 2026
Search 2: biotech FDA approval announcement today 2026
Search 3: earnings surprise gap up small cap today 2026
Search 4: small cap contract win partnership announcement today 2026
Search 5: short squeeze unusual volume small cap today 2026
```

**Reddit scan (run via `reddit_sentiment.py` alongside news searches):**
Query the shared script with subreddits `["wallstreetbets","swingtrading","smallcapstocks","pennystocks"]` for general discovery, and `["stocks"]` for broader DD.

**Swing trading blogs and forums (run alongside Reddit):**
```
Search 11: site:stockbee.blogspot.com episodic pivot setup 2026
Search 12: site:tradethatswing.com best stocks swing trade this week
Search 13: site:shareplanner.com stock market analysis setup today
Search 14: site:forums.bearbulltraders.com swing trade watchlist today
Search 15: site:elitetrader.com swing trade catalyst setup today
```

**Blog/forum signal quality (for weighting findings):**
- **Stockbee (stockbee.blogspot.com)** -- Highest priority. Pradeep Bonde's blog -- the source of the EP methodology this skill is built on. Any ticker he names is worth evaluating.
- **TradeThatSwing (tradethatswing.com)** -- High signal. Publishes a weekly best stocks list updated before Monday open. Check for current week's list on every scan.
- **SharePlanner (shareplanner.com)** -- Medium-high signal. Regular market analysis and swing trade setups from an active practitioner.
- **BearBullTraders forum (forums.bearbulltraders.com)** -- Medium signal. Large active community with dedicated swing trade watchlist threads.
- **EliteTrader (elitetrader.com)** -- Medium signal. Experienced crowd, lower noise than Reddit, good for confirming setups already on the radar.

**Blog/forum filter -- same standard as Reddit:**
- Blog/forum mention + SEC filing or verified press release (check `sec_filings.py`) -> valid candidate, proceed
- Blog/forum mention + RVOL confirmation (check `fetch_stock_data.py`) -> valid candidate, proceed
- Blog/forum mention only, no filing, no data -> treat as idea only, still must pass 5-layer pipeline
- Stockbee EP mention specifically -> elevate to priority candidate, run full evaluation immediately

If you specify a sector (biotech, energy, defense, tech), add a `sector`-filtered `screen_stocks.py` query plus:
```
Search 16: [sector] stock catalyst news today 2026
Search 17: reddit.com wallstreetbets [sector] today
Search 18: stockbee [sector] episodic pivot today
```

**Reddit hype filter -- apply before any ticker enters the pipeline:**
- Reddit mention + linked SEC filing (8-K) or verified press release -> valid candidate, proceed
- Reddit mention + RVOL confirmation from `fetch_stock_data.py` -> valid candidate, proceed
- Reddit mention only, no filing, no press release, no RVOL data -> News Quality <= 2, auto-pass immediately
- Reddit as a confirming signal for a ticker already scoring 4-5 on news quality -> flag as "Reddit tailwind -- retail FOMO may fuel drift"
- High short interest + Reddit buzz + volume spike -> flag as "Squeeze candidate" and note it separately

**Subreddit signal quality (for weighting Reddit findings):**
- r/SwingTrading -- Highest signal for EP setups
- r/RealDayTrading -- High signal; disciplined, strategy-driven posts
- r/wallstreetbets -- High noise, catches squeezes early; filter hard
- r/Daytrading -- Medium signal; good for unusual volume mentions
- r/smallstreetbets -- Medium signal; small cap specific, less noise than WSB
- r/stocks -- Lower signal; use only if ticker has multiple detailed mentions

From all searches, identify 4-8 tickers with potential EP catalysts. Discard anything that is:
- Clearly a large cap (market cap > $5B)
- A generic PR with no hard numbers and no Reddit or blog volume confirmation
- Reddit/blog mention only with no filing, press release, or RVOL data
- Already fully covered mainstream news with no fresh angle, Reddit tailwind, or practitioner blog coverage
### Step 2: Quick filter -- News Quality pass/fail

For each candidate, score News Quality (Layer 1) first. Takes 60 seconds per ticker.
- Score 3+ -> proceed to full evaluation
- Score < 3 -> PASS immediately, don't waste time on layers 2-5

### Step 2b: Sector Theme Ignition -- Find the Best Name in a Hot Sector

When a macro catalyst (policy news, regulatory shift, geopolitical event, commodity spike) is moving an entire sector without a specific company catalyst -- like a cannabis reclassification headline, an FDA fast-track announcement, a defense budget expansion, or an energy supply shock -- do NOT evaluate the theme play ticker (the most obvious one that already ran). Instead, run the Sector Ignition Protocol:

**Trigger conditions:**
- Multiple tickers in the same sector are up 10%+ on the same day with no individual company catalysts
- A macro/policy event is clearly driving sector-wide movement
- The scan surfaces 3+ tickers from the same sector in the same session

**Sector Ignition Protocol:**

1. **Identify the theme** -- name the macro catalyst driving the sector (e.g., "cannabis reclassification speculation," "defense budget expansion," "GLP-1 drug patent expiry")

2. **Flag the obvious play as potentially over-extended** -- the ticker that ran first and hardest is usually already priced in by the time the scan surfaces it. Flag it explicitly: "Theme leader -- may be over-extended. Check gap fill status before evaluating."

3. **Search for the better setup within the sector:**
```
Search: [sector theme] small cap stock catalyst individual news [current week] 2026
Search: [sector] stock gap up SEC filing 8-K [current week] 2026
Search: [sector theme] company contract OR approval OR earnings [current week] 2026
```
Goal: Find a name in the same sector with BOTH the macro tailwind AND a specific individual catalyst (contract win, FDA approval, earnings beat). That's the A+ setup -- sector ignition + individual EP.

4. **Classify each sector name by catalyst type:**
- **Individual catalyst + sector tailwind** -> A+ candidate, run full pipeline
- **Sector tailwind only, early mover** -> B candidate at best, check chart carefully for breakaway vs exhaustion
- **Sector tailwind only, late mover / sympathy play** -> C/PASS, momentum already priced

5. **Output a sector summary before individual evaluations:**
```
SECTOR IGNITION DETECTED -- [Sector Name]
Macro catalyst: [One sentence description]
Catalyst quality: [Hard policy change / Speculation / Data event]
Individual names identified: [List]
Best setup: [Ticker -- Individual catalyst + sector tailwind / or "None found, sector plays only"]
Speculation warning: [Yes/No -- flag if the macro catalyst has no hard filing or regulatory decision]
```

**Cautionary lesson baked into this rule:** Sector-wide speculation with no SEC filing, no regulatory action, and no hard catalyst -- like cannabis stocks running 65%+ purely on reclassification speculation -- is a Score 2 under the News Quality rule. The correct output in that scenario is not "evaluate the theme leader" -- it's "flag sector speculation, search for any name in the sector with an INDIVIDUAL catalyst this week." If no individual catalyst exists, the entire sector move auto-passes.

### Step 3: Full pipeline on qualifying candidates

Run each ticker that passed the news filter through all 5 layers. Be efficient -- you're evaluating multiple names, not writing a novel per ticker. Use the structured output format but keep layer summaries tight (1-2 sentences each) unless a layer has a critical finding.
### Step 4: Deliver ranked shortlist

Rank by overall grade (A+ -> A -> B) and present as a scannable list:

```
DAILY SCAN -- [Date]
========================================
Market: [S&P 500 +/-X% | Nasdaq +/-X%] | VIX: [X] [Normal / Elevated >25 / Fear Mode >30] | Fear & Greed: [value/label]
[N] candidates screened | [N] qualified | [N] worth evaluating

-----------------------------
#1 -- [TICKER] | Grade: A+ | BUY
Catalyst: [One sentence]
RVOL: [X]x | Gap: [X]% | Chart: Breakaway | Float: [X]M
Confidence: [List builders present -- e.g., "Low float + VWAP hold + pre-catalyst RS"]
Cross-source: [Single / Confirmed / MULTI-SOURCE CONVERGENCE -- list types]
Key risk: [One sentence]
Trade: Entry $[X]-$[X] | Stop $[X] | T1 $[X] | T2 $[X]

#2 -- [TICKER] | Grade: A | WATCH
Catalyst: [One sentence]
RVOL: [X]x | Gap: [X]% | Chart: Breakaway -- early | Float: [X]M
Confidence: [List builders present or "Limited -- verify before entry"]
Cross-source: [Single / Confirmed / MULTI-SOURCE CONVERGENCE -- list types]
Key risk: [One sentence]
Trade: Entry $[X]-$[X] | Stop $[X] | T1 $[X] | T2 $[X]
Why WATCH not BUY: [One sentence -- e.g., "Day 1, confirm gap holds tomorrow before entry"]

#3 -- [TICKER] | Grade: B | WATCH
[Same format]

PASSED (not worth your time):
- [TICKER]: [One sentence reason] (News score 2, generic PR)
- [TICKER]: [One sentence reason] (RVOL 1.1x, already priced in)
========================================
```

After the shortlist, ask: "Want the full evaluation on any of these?"

---
## EXIT MONITOR MODE -- "Should I Hold or Sell [TICKER]?"

When you provide a ticker you're already in with entry price and date, run the exit monitor. This mode evaluates whether the original thesis is still intact and whether it's time to hold, tighten the stop, take partial profits, or exit.

### Inputs needed
- Ticker
- Entry price and date
- Original catalyst (if known)
- Current stop level (if set)
- Account for partial profits already taken (if any)

If you don't provide all of these, ask for what's missing before running the evaluation.

### Exit monitor pipeline

**A. Thesis check -- is the original EP thesis still intact?**
- Is price still above the gap low / original support level? (Yes = thesis intact / No = thesis broken)
- Has the gap been fully filled? (Partial fill can be normal; full fill + failure to reclaim = exit signal)
- Any news since entry that changes the original catalyst? Check `fetch_stock_data.py` analyst field and `sec_filings.py` recent_filings for anything new. (Positive, negative, or none)

**B. Price action vs. expected drift**
- Where is price relative to entry? (+X% / -X%)
- Where is price relative to Target 1 and Target 2?
- Is price extended from the 20-day moving average? (> 20% above = consider taking profits)
- Has price formed a new base / flag (bullish continuation) or is it extended and parabolic (caution)?

**C. Volume behavior since entry**
- Are up days showing higher volume than down days? (Accumulation = bullish)
- Are down days showing heavy volume? (Distribution = warning)
- Has volume dried up entirely? (Neutral -- could mean either digestion or loss of interest)

**D. Days held vs. hold window**
- Days in trade: [X]
- Expected hold window for this setup: [X-XX days]
- If approaching or past the outer edge of the hold window, flag it

**E. Technical signals to exit or tighten**
- Price extended > 20% above 20-day MA -> take Trim 1 or Trim 2 per the three-tranche structure, or tighten stop significantly
- Failed breakout above prior resistance on volume -> consider exiting
- Bearish reversal candle on high volume after a strong run -> warning
- Price closing below the 10-day MA after a sustained run -> consider tightening
- Gap fill + failure to reclaim within 2 sessions -> thesis broken, exit

**F. R:R check at current price**
- Recalculate R:R from current price to stop vs. remaining upside to Target 2
- If R:R has collapsed below 1:1 -> no reason to hold the full position
- If R:R is still 2:1+ -> thesis intact, hold
### Exit monitor output format

```
EXIT MONITOR -- [TICKER]
========================================
Entry: $[X] on [date] | Days held: [X]
Current price: $[X] | P&L: [+/-X%]
Original catalyst: [one sentence]

DECISION: [HOLD / TIGHTEN STOP / TAKE PARTIAL / EXIT]
Confidence: [XX%]

----------------------------------------
THESIS STATUS: [INTACT / WEAKENING / BROKEN]
Gap low holding: [Yes / No]
Gap fill: [No fill / Partial / Full + reclaim / Full + failed]
News since entry: [None / Positive / Negative -- detail]

PRICE ACTION: [Healthy / Extended / Stalling / Breaking down]
vs. 20-day MA: [+/-X% -- normal / extended / far extended]
Pattern: [Flag/base (bullish) / Extended (caution) / Breakdown]
Days in trade vs. window: [X days / window was X-XX days]

VOLUME BEHAVIOR: [Accumulating / Neutral / Distributing]
Up day volume vs. down day volume: [Up days heavier / Even / Down days heavier]

R:R FROM HERE:
Current stop: $[X] | Risk from here: [X%]
Trim 1 ($[X] / +10-15%): [Hit and taken / Hit, not yet taken / Not yet reached]
Trim 2 ($[X] / +25-30%): [Hit and taken / Hit, not yet taken / Not yet reached]
Trailing remainder: [Stop level if riding / N/A]
Target 1: $[X] ([X]% remaining) | R:R: [X:1]
Target 2: $[X] ([X]% remaining) | R:R: [X:1]

EXIT SIGNALS TRIGGERED: [List or "None"]
HOLD SIGNALS INTACT: [List or "None"]

----------------------------------------
RECOMMENDATION:
[3-5 sentences. Direct. State clearly what to do and why.
If partial exit: specify how much (e.g., "sell half here, trail stop on remainder").
If tighten: specify new stop level.
If exit: state why thesis is broken or R:R no longer justifies holding.
No hedging.]
========================================
```

---
## Data Sources Priority

**Prefer the tested scripts in `../../shared/` over web search wherever they cover the need -- faster, cheaper, structured data instead of parsed pages.**

**Catalyst and news quality:**
1. **`sec_filings.py`** -- primary source for catalyst verification (8-K, 10-Q, 10-K, Form 4 insider transactions, going-concern check)
2. **`perplexity_verify.py`** -- independent corroboration of a specific catalyst claim beyond company PR
3. **Benzinga / MarketBeat** (web search) -- catalyst quality, analyst reaction, RVOL data
4. **Company investor relations page** (web search) -- press releases and guidance

**Chart and volume data:**
5. **`fetch_stock_data.py`** -- price, volume, float, fundamentals, insider/institutional/analyst data
6. **`screen_stocks.py`** -- candidate discovery within your configured universe
7. **StockCharts / TradingView descriptions** (web search) -- chart structure context, VWAP, intraday behavior

**Practitioner setup sources (scan for candidates, web search):**
8. **Stockbee (stockbee.blogspot.com)** -- EP-specific setups from the methodology's originator; highest trust
9. **TradeThatSwing (tradethatswing.com)** -- weekly best stocks list; check every scan
10. **SharePlanner (shareplanner.com)** -- active swing trade analysis and setups
11. **BearBullTraders forum** -- community watchlists and swing trade discussion
12. **EliteTrader (elitetrader.com)** -- experienced practitioner discussion

**Sentiment and momentum sources:**
13. **`reddit_sentiment.py`** -- r/SwingTrading, r/RealDayTrading, r/wallstreetbets, r/smallstreetbets, r/Daytrading, r/stocks
14. **`market_mood.py`** (VIX + CNN Fear & Greed Index, via the Down Tape Protocol)

---

## Critical Rules

- **Never fabricate financial data.** If a script returns null/error or you can't find a ratio or volume figure, say so and flag it as "unverified."
- **Never upgrade a PASS based on vibes.** If Layer 1 scores < 3 or a liquidity red flag triggers, the skip rule is hard.
- **Be direct.** "This is a PASS because the catalyst is a PR with no hard numbers and RVOL is 1.2x" is the right output. Not "this could be interesting but there are risks to consider."
- **Account size agnostic.** Output the risk framework (1-2% rule, 1:2 R:R) so you can apply it to your actual account size.
- **Disclaimer at the bottom of every evaluation:** "This is not financial advice. All trading involves risk. Do your own due diligence before entering any position."
