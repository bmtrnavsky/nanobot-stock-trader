---
name: longterm-quality-investor
description: "Long-term (10+ year) buy-and-hold evaluator for smaller U.S. public companies using the small-cap quality framework (Buffett, Akre, Terry Smith, Nick Sleep, Piotroski F-Score). Four modes: SCAN (pass/fail filter across multiple tickers), DEEP EVAL (full five-component analysis with live data, SEC 10-K/10-Q review, moat classification, F-Score, and composite scoring), HOLD/TRIM/SELL (re-underwrite an existing position after earnings or a material event), and DIVIDEND EVAL (quality-dividend screen for durable payers, not yield chasing). Always use this skill when evaluating any stock for a long-term hold, running fundamental analysis, reviewing a current position, or asking whether a small-cap company has durable compounding potential."
---

# Long-Term Quality Investor -- Small-Cap Buy-and-Hold Framework

## Purpose

Evaluate U.S. small- and mid-cap public companies for long-term (10-year) ownership. This is not a trading system. The question is always: **Is this a healthy, improving, competitively advantaged business I would be comfortable owning for 10 years?**

**Philosophy:** Think like a business owner, not a trader. Favor quality, durability, and reinvestment runway. Prefer a wonderful company at a fair price over a mediocre company that looks cheap. Treat drawdowns as noise; treat permanent business impairment as the real risk.

**Universe:** U.S.-listed public companies, $50M-$2B market cap, $5-$25 share price as a sourcing filter only (not a valuation signal). Dividend Eval mode relaxes the price filter -- see that section.

---

## Data Sources (Use in This Priority Order)

This skill has real, tested scripts in `../../shared/` (shared across swing-trade-scanner, longterm-quality-investor, and catalyst-growth-investor). Prefer these over web search wherever they cover the need -- faster, cheaper, structured data instead of parsed pages.

- **Live quote, summary ratios (P/E, price/sales, margins-as-reported-by-Yahoo), dividend history:**
  `uv run --with yfinance python3 ../../shared/fetch_stock_data.py`
  Note: this only exposes Yahoo's snapshot `info` fields -- no balance sheet, income statement, cash flow line items, or multi-period history. Use it for price/market cap/P-E/dividend data, not for F-Score or ROIC inputs.
- **Structured 10-K/10-Q financials -- balance sheet, income statement, cash flow, multi-year history, Piotroski F-Score, ROIC, EV/EBITDA, FCF conversion, cash runway:**
  `uv run --with edgartools python3 ../../shared/financials.py`
  This is the only source for F-Score inputs, ROIC, gross/operating margin, and multi-quarter trends -- fetch_stock_data.py cannot provide these. Every value it can't verify from the actual filing comes back `null` with a note, never estimated.
- **Candidate screening (market cap, price, sector, dividend yield filters):**
  `uv run --with yfinance python3 ../../shared/screen_stocks.py`
- **SEC filings (10-K, 10-Q, going concern, material weakness checks, recent filings list):**
  `uv run --with edgartools python3 ../../shared/sec_filings.py`
- **Independent catalyst / news verification:**
  `uv run --with requests python3 ../../shared/perplexity_verify.py`

If a script can't answer something (industry context, qualitative moat commentary, analyst notes, sector peer multiples for valuation comparison), fall back to web search:
- Macrotrends (`macrotrends.net`) -- sector peer multiples, qualitative context
- SEC EDGAR direct (`sec.gov/cgi-bin/browse-edgar`) if the script can't pull a specific filing
- IBISWorld summaries, Statista, industry association data cited in filings

**Critical rule:** Never fabricate financial data. If a figure cannot be confirmed from a live source, flag it as "UNVERIFIED -- confirm before acting."

---

## Mode Selection

Identify which mode applies from context:

- **SCAN MODE** -- you provide multiple tickers or ask for a pass/fail filter across a list.
- **DEEP EVAL MODE** -- you provide one ticker and want a full analysis or buy/watch/reject decision.
- **HOLD/TRIM/SELL MODE** -- you mention a ticker you own and ask whether to hold, trim, or exit.
- **DIVIDEND EVAL MODE** -- you ask about dividend income, yield, a payer's safety, or screening for dividend candidates.

If the mode is ambiguous, ask before proceeding.

---

## HARD REJECT RULES (Auto "No" for New Buys)

Check these FIRST. Any hit = reject for new buys. For existing positions, these trigger immediate high-priority sell review.

| # | Rule | Rationale |
|---|---|---|
| 1 | Reverse stock split within 24 months | 3-year abnormal return avg -33.9% (Desai & Jain 1997) |
| 2 | Going concern language in latest 10-K or 10-Q | 85% correlation with eventual bankruptcy |
| 3 | Repeated material weaknesses in internal controls | 2.7x higher fraud rate vs matched firms |
| 4 | Chronic negative FCF with no credible time-bounded path to positivity | Business model is not viable at scale |
| 5 | Chronic equity dilution to fund operations (>5% annual share count increase, recurring) | 10-year dilution destroys ownership value |
| 6 | Average daily dollar volume < $1M | Execution risk and price distortion |
| 7 | Beneish M-Score above -1.78 (if calculable) | Statistical earnings manipulation signal |
| 8 | Active disclosed SEC or DOJ investigation | Credible threat to business continuity |
| 9 | Auditor resignation outside normal rotation | Signals unresolvable accounting disagreement |
| 10 | Meme/squeeze episode as primary price driver within 18 months | Price discovery is unreliable |

---

## HARD INCLUSION RULES (Minimum to Proceed)

All must pass for a SCAN MODE "Pass" or DEEP EVAL entry. Any failure = "Watch" or "Reject" -- never "Buy."

- Revenue TTM >= $30M (or >=$10M/quarter for 2+ consecutive quarters, clearly accelerating)
- Revenue growth >= 10% YoY
- Gross margin at or above sector median, stable or improving over 4+ quarters
- Positive operating cash flow in at least 2 of last 4 quarters (or credible, accelerating path if reinvesting)
- Net debt/EBITDA <= 3.0x (or net cash positive)
- Current ratio >= 1.0x
- No covenant violations flagged in most recent 10-Q
- Piotroski F-Score >= 5
- Market cap >= $50M
- Average daily dollar volume >= $1M
- No hard reject conditions present

---

## MODE 1: SCAN MODE

**Goal:** Rapidly pass/fail a list of tickers using the hard reject and hard inclusion gates. Output a ranked watchlist. No deep work here -- this surfaces candidates for Deep Eval.

### Scan Process

For each ticker:
1. Pull live data via `fetch_stock_data.py`: price, market cap, volume, revenue (TTM), revenue growth, gross margin, operating cash flow, net debt, current ratio
2. Check all 10 hard reject rules (keyword search for going concern, reverse split history, SEC actions -- use `sec_filings.py` for the going-concern check)
3. Check all hard inclusion rules
4. Assign status: **PASS TO DEEP EVAL** / **WATCH (specify what needs to improve)** / **REJECT (specify rule that failed)**

To source a candidate list rather than working from tickers you already gave it, call `screen_stocks.py` with `market_cap_min: 50000000, market_cap_max: 2000000000, price_min: 5, price_max: 25`.

### Scan Output Format

```
SCAN RESULTS -- [DATE]
========================================

PASS TO DEEP EVAL:
- [TICKER]: $[mkt cap] | Rev TTM $[X]M | Growth [X%] | GM [X%] | OCF [pos/neg] | Debt/EBITDA [X]x | Vol $[X]M/day
  Why it passes: [One sentence on the most compelling characteristic]

WATCH (specify condition):
- [TICKER]: [The one thing blocking it from Deep Eval]
  Check back when: [Specific metric or milestone]

REJECT:
- [TICKER]: [Specific hard reject or hard inclusion rule that failed -- one sentence, no hedging]

========================================
```

After output, ask: "Want the full Deep Eval on any of the passes?"

---

## MODE 2: DEEP EVALUATION MODE

**Goal:** Produce a structured BUY / WATCH / REJECT decision with a thesis, key monitoring metrics, and approximate valuation range.

**Time investment:** This is a 6-component evaluation (six scored components plus a pass/fail SEC filing gate). Work through all of it in order. Do not skip components.

### Step 0: Data Pull

Before any analysis, pull and document from both scripts:
- **From `fetch_stock_data.py`:** price, market cap, P/E, forward P/E, price/sales, total cash, total debt, free cash flow, shares outstanding, avg volume, 52-week range, beta, dividend history
- **From `financials.py`:** balance sheet / income statement / cash flow line items (2-3 annual periods), the full 9-point Piotroski F-Score (pre-computed, with per-signal detail and honest nulls for anything the filing didn't support), ROIC, gross margin, operating margin, EV, EV/EBITDA, FCF conversion, cash runway. Pass `market_cap`, `total_cash`, `total_debt`, and `free_cashflow` from the `fetch_stock_data.py` call into `financials.py`'s payload so it can compute EV/EV-EBITDA/cash-runway using the Yahoo-sourced figures alongside the filing data.

Flag any figure that cannot be confirmed from a live source as **UNVERIFIED** -- `financials.py` already does this itself (returns `null` with a note rather than a guess), so pass those nulls through rather than filling them in.

### Component A: Business Quality (30% weight)

1. **ROIC:** From `financials.py`'s `roic` field (NOPAT / invested capital -- note it assumes a 21% effective tax rate, not the filer's actual rate, so treat it as an estimate, not a filed figure). Score: >=15% = strong; 10-14% = acceptable; <10% = zero credit. For early-stage: is trajectory toward 15%+ within 2-3 years credible? If `financials.py` returns `null` for ROIC (missing operating income or balance sheet data), flag as UNVERIFIED rather than estimating.
2. **Gross margin trend:** From `financials.py`'s `ratios_by_period` across however many periods it returned (2-3 annual, filer-dependent). Stable or improving = pass. Eroding at scale = red flag. Not every filer reports a distinct gross profit line (services/subscription businesses often don't) -- if `gross_margin` comes back `null` across all periods, say so explicitly rather than treating it as a red flag.
3. **FCF conversion:** From `financials.py`'s `fcf_conversion` field (FCF from Yahoo / Net Income from the filing). >=70% = excellent; 60-70% = acceptable; <50% = examine working capital and capex. `null` if net income is missing or zero -- don't estimate.
4. **Moat classification:**
   - Explicitly identify the source: switching costs, network effects, scale economics, brand, regulatory barriers, proprietary data/patents, niche dominance, operational culture
   - Classify as: **Built** (proven 5+ years stable/rising ROIC) / **Building** (structurally identifiable, early) / **Speculative** (narrative only)
   - "First mover" alone is NOT sufficient for Built or Building.
5. **Business model clarity:** Can the business be explained in one paragraph? If not, flag complexity.

### Component B: Financial Strength (20% weight)

1. **Piotroski F-Score:** Use `financials.py`'s `piotroski_f_score` output directly -- it's already computed (all 9 signals, or as many as the filing supports). Read the `score`, `max_possible`, and `missing_signals` fields rather than re-deriving from raw numbers.

| Signal | Condition |
|---|---|
| F1 ROA | Net income / total assets > 0 |
| F2 ROA change | This year ROA > last year ROA |
| F3 CFO | Operating cash flow > 0 |
| F4 Accrual | CFO/Assets > ROA (cash earnings > accounting earnings) |
| F5 Leverage | Long-term debt/assets decreased YoY |
| F6 Liquidity | Current ratio improved YoY |
| F7 Dilution | No new common shares issued in past year |
| F8 Gross margin | Gross margin improved YoY |
| F9 Asset turnover | Revenue/assets improved YoY |

Minimum for Deep Eval BUY consideration: **F-Score >= 6 out of the score's own `max_possible`** (not always out of 9 -- some filers don't report every line item, e.g. no separate gross profit or no historical share count). If `max_possible` is 5 or fewer (more than 4 signals missing), treat the whole Financial Strength component as lower-confidence and say so in the output -- don't silently treat a 3/4 as equivalent to a 6/9. Score at or above 6/max = pass. 5/max = Watch. 4 or below = financial strength concern, likely reject.

2. **Interest coverage:** EBIT (`operating_income` from `financials.py`) / interest expense. Must be >=3x. Below 2x = reject. If interest expense isn't broken out as its own line, flag as UNVERIFIED rather than skip the check silently.
3. **Dilution rate:** From `financials.py`'s `shares_outstanding` history if available (often isn't -- many filers don't carry a multi-period share count on the balance sheet itself). <2% = excellent; 2-3% = acceptable; >3% = yellow flag; >5% recurring = hard reject. If unavailable, note it and rely on F7's dilution signal instead where it resolved.
4. **Covenant check:** Any violations or waivers flagged in 10-Q? Yes = red flag. (Web search or `sec_filings.py` recent_filings -- not something `financials.py`'s structured pull surfaces.)

### Component C: Growth Durability (20% weight)

1. **Revenue growth decomposition:** Organic (new customers + pricing + expansion) vs. acquisition-driven. Organic is worth more.
2. **Product-market fit evidence:** Customer count growth, retention rates, NRR >100% (SaaS), cohort data, any metric in filings showing customers buy more over time.
3. **Customer concentration:** >20% from single customer = yellow flag. >30% = red flag. Check 10-K risk factors explicitly.

### Component D: Industry Structure (15% weight)

1. **TAM assessment:** Is the addressable market growing or shrinking? Does company have <=20% share (room to grow) or >=50% share in a mature market (limited runway)?
2. **Competitive position:** Is market share stable or growing? Evidence from MD&A, industry reports cited in filings.
3. **Competitive intensity:** How many credible competitors, how differentiated is pricing, is the industry consolidating or fragmenting? Web search sector reports or peer 10-Ks if the target's own filing doesn't say enough.

### Component E: Valuation (10% weight)

1. **EV/FCF and EV/EBIT vs. sector peers:** Pull the target's `ev` and `ev_ebitda` from `financials.py` (EV/EBIT needs EV / `operating_income`, both already in the data pulled). Web search 2-4 direct peers' equivalent multiples for comparison -- `financials.py` doesn't have peer data, only the target.
2. **FCF yield + growth = approximate expected annual return.** FCF yield = FCF / EV (or FCF / market cap if EV isn't available). Add the credible forward revenue growth rate for a rough expected-return estimate.
3. **Scoring:** Current multiple at or below the low end of the peer range, with FCF yield + growth implying >=12% expected return = full 10 points. Multiple in line with peers, expected return 8-12% = 6-8 points. Multiple at or above the peer high end, expected return 5-8% = 2-5 points. Paying more than 1.5x the peer high end, or expected return under 5% = 0-2 points regardless of how good the business is -- quality doesn't override a genuinely bad entry price, it just means "wait for a better price," not "buy anyway."
4. **If peer data can't be found:** score on FCF yield + growth alone against a market-average expected-return benchmark of roughly 8-10%, and flag that the peer comparison step was skipped.

### Component F: Management and Capital Allocation (5% weight)

1. **Insider ownership:** Pull from most recent proxy or `fetch_stock_data.py` holder stats. Founders/CEO owning >=5% actual shares (not just options) = strongly positive. >=3% = acceptable baseline.
2. **Compensation structure:** Tied to multi-year ROIC or FCF/share = aligned. Tied purely to short-term EPS/revenue = misaligned.
3. **Capital allocation history (3-5 years):** Review acquisitions (multiples paid, performance), buybacks (price discipline), equity raises (rational or distressed?).
4. **Communication quality:** Specific, quantified, consistent language about reinvestment opportunities = positive. Vague transformational language without milestones = caution flag.

### Component G: SEC Filing Deep Dive (Gate -- Must Pass, Not Scored)

**Pull via `sec_filings.py`, or fetch directly from EDGAR if the script doesn't cover it:**
- Most recent 10-K (annual)
- Most recent 10-Q (quarterly)
- Any material 8-Ks from last 90 days

Key gates:

- **Going concern:** Any audit qualification language = AUTOMATIC REJECT at this stage
- **MD&A vs. financials consistency:** Management narrative should match what the numbers actually show. Discrepancy = red flag.
- **New or expanded risk factors:** Document any new items vs. prior period filing
- **Related party transactions:** Flag and explain any unusual amounts
- **Revenue recognition policy:** Has it changed? Any aggressive recognition signals?
- **For healthcare/FDA companies:** Any CRLs, warning letters, clinical failures, manufacturing inspection issues disclosed?

### Composite Scoring

Weight the six components as: Business Quality 30, Financial Strength 20, Growth Durability 20, Industry Structure 15, Valuation 10, Management 5 (100 total). The SEC Filing Deep Dive is a gate, not part of the 100 -- it can veto a BUY regardless of composite score, but a clean gate result doesn't add points.

**Score interpretation:**
- >=65: Strong BUY candidate (if no hard reject conditions)
- 50-64: WATCH (specify which category needs improvement)
- <50: REJECT

### Deep Eval Output Format

```
DEEP EVALUATION -- [TICKER] | [COMPANY NAME]
========================================
Date: [DATE] | Price: $[X] | Market Cap: $[X]M | EV: $[X]M

DECISION: [BUY / WATCH / REJECT]
Composite Score: [X/100]
Confidence: [High / Medium / Low]

----------------------------------------
COMPONENT SCORES:
Business Quality:        [X/30] -- [ROIC X%, GM trend: up/flat/down, FCF conv X%, Moat: Built/Building/Speculative]
Financial Strength:      [X/20] -- [F-Score: X/max_possible, Interest cov: Xx, Dilution: X%/yr]
Growth Durability:       [X/20] -- [Rev growth: X% organic/acquired, Customer conc: OK/flag]
Industry Structure:      [X/15] -- [TAM trajectory, competitive intensity, market share trend]
Valuation:               [X/10] -- [EV/FCF: Xx, EV/EBIT: Xx, FCF yield + growth: X%]
Management:              [X/5]  -- [Insider own: X%, comp alignment: yes/no, cap alloc: disciplined/mixed]

----------------------------------------
BUSINESS QUALITY:
[3-5 sentences. ROIC, gross margin trend, FCF conversion, moat classification with explicit source, business model clarity]

FINANCIAL STRENGTH:
F-Score: [X/max_possible] (note if max_possible < 9 and why -- e.g. "no historical share count on the balance sheet")
[List each resolved signal with its 0/1, and list missing_signals separately]
[Interest coverage, dilution rate, covenant status]

GROWTH DURABILITY:
[2-3 sentences. Organic vs acquired, customer concentration]

INDUSTRY STRUCTURE:
[2-3 sentences. TAM size and trajectory, market share, competitive intensity]

MANAGEMENT:
[2-3 sentences. Insider ownership %, comp structure, capital allocation track record]

SEC FILING FINDINGS:
10-K reviewed: [Date of filing]
10-Q reviewed: [Date of filing]
Going concern: CLEAR / FLAG
Material weaknesses: NONE / FLAG
MD&A vs financials: CONSISTENT / DISCREPANCY NOTED
New risk factors: [None / List new items]
Revenue recognition: STANDARD / FLAG
Auditor: [Name] | Opinion: CLEAN / QUALIFIED
Litigation: [Material / None disclosed]
[For FDA companies: regulatory status]

VALUATION:
EV/FCF: [X]x (sector peers: [X]-[X]x)
EV/EBIT: [X]x (sector peers: [X]-[X]x)
FCF yield + growth rate = approx [X%] expected annual return
Reasonable entry range: $[X] -- $[X] (based on [X]x EV/FCF on current FCF, implying [X%] return)
Current price vs reasonable range: [At/Below/Above] reasonable zone

----------------------------------------
THESIS (if BUY or WATCH):
[3-5 sentences. Why this business could compound at above-market rates for 10 years. What moat, what runway, what management, what price discipline.]

KEY RISKS:
1. [Most important risk -- be specific]
2. [Second risk]
3. [Third risk]

METRICS TO MONITOR (quarterly):
- [Specific metric #1 -- what direction is healthy, what triggers a review]
- [Specific metric #2]
- [Specific metric #3]

If WATCH: [Exactly what condition upgrades this to BUY]
If REJECT: [The specific durable reason this is a no -- no hedging]

========================================
Disclaimer: This is not financial advice. All investing involves risk. Do your own due diligence before taking any position.
```

---

## MODE 3: HOLD / TRIM / SELL MODE

**Goal:** Re-underwrite an existing position after earnings, a material event, or on your own schedule. The question is never "has the stock dropped?" -- it is "has the thesis changed?"

**Trigger:** After each 10-K and 10-Q cycle, after any material 8-K, after a price move >20% in either direction, or when you ask.

### Inputs Needed

- Ticker
- Entry price and date
- Original thesis (brief)
- Current position size / any prior trims
- Most recent quarterly filing date

If these aren't provided, ask before running.

### Re-Underwriting Checklist

Run each of these:

1. **Moat intact?** Gross margin trend, ROIC trend, competitive win/loss language in MD&A, customer retention signals. Weakening = yellow flag.
2. **F-Score stable or improving?** Declining F-Score for 2 consecutive annual periods = yellow flag.
3. **Management executing?** Acquisitions performing? Organic growth continuing? Capital allocation rational?
4. **Leverage changed materially?** Significant new debt without corresponding earnings improvement = examine closely.
5. **Valuation re-rated?** EV/FCF + growth still implies acceptable return? If stock has re-rated to >3x warranted multiple, trim signal.
6. **Any new hard reject conditions triggered?** Going concern, material weakness, auditor resignation, SEC investigation = sell review.
7. **Any thesis-breaking events?** Moat clearly eroding, major customer loss, structural profitability decline = sell.

### Decision Table

| Signal | Action |
|---|---|
| Thesis intact, drawdown from market noise | Hold; consider adding if valuation improved |
| Single-quarter weakness, fundamentals intact | Hold; monitor next quarter |
| Competitive erosion emerging in margins | Trim to half position; set watchlist criteria |
| Thesis-breaking event (moat clearly compromised) | Sell regardless of price |
| Going concern, restatement, auditor resignation | Sell immediately |
| Valuation at >3x warranted multiple | Trim significantly; keep residual if growth durable |
| Management fraud or misrepresentation | Sell immediately |
| Price up significantly, thesis unchanged | DO NOT SELL. Price gain is not a thesis break. |

**On selling winners:** The disposition effect costs average investors 3.2-5.7% annually. Sell when the thesis breaks, not when the price rises. As long as ROIC is high, reinvestment runway is long, and management is allocating well, price appreciation is validation -- not a sell signal.

### Hold/Trim/Sell Output Format

```
POSITION REVIEW -- [TICKER] | [COMPANY NAME]
========================================
Entry: $[X] on [date] | Days held: [X] | Current: $[X] | P&L: [+/-X%]
Filings reviewed: 10-K [date], 10-Q [date]

DECISION: [HOLD / ADD / TRIM / SELL]
Confidence: [High / Medium / Low]

----------------------------------------
THESIS STATUS: [INTACT / WEAKENING / BROKEN]

Moat: [Strengthening / Stable / Weakening] -- [evidence]
F-Score: [X/max_possible current vs X/max_possible last year] -- [trend]
ROIC: [X% current vs X% prior] -- [trend]
Gross margin: [X% current vs X% prior] -- [trend]
Revenue growth: [X% current vs X% prior] -- [trend]
FCF conversion: [X%] -- [trend]
Leverage: [Net debt/EBITDA X]x -- [changed materially? yes/no]
Management: [Executing / Mixed / Concerning]
New risk factors: [None / list]
Hard reject conditions: [None / flag]

Valuation check:
Current EV/FCF: [X]x | Warranted multiple: ~[X]x | FCF yield + growth: [X%]
At/below/above reasonable range: [status]

----------------------------------------
RECOMMENDATION:
[3-5 sentences. Direct. State clearly what to do and why. If trim: specify how much. If sell: state exactly what broke. No hedging.]

UPDATED MONITORING METRICS:
- [Metric to watch next quarter]
- [Metric to watch next quarter]
========================================
Disclaimer: This is not financial advice. All investing involves risk. Do your own due diligence before taking any position.
```

---

## MODE 4: DIVIDEND EVAL MODE

**Goal:** Screen for or evaluate durable dividend payers. This is a quality-first filter, not a yield-chasing tool. A 3% yield from a compounding business beats an 8% yield about to be cut.

**Universe:** Relax the price filter used elsewhere in this skill -- dividend payers commonly trade well above $25/share. Keep market cap $50M-$2B unless you ask for large caps specifically. Utilities and REITs get their own inclusion logic below since standard FCF/growth gates don't fit their capital structures.

### Dividend-Specific Hard Reject Rules

Any hit = reject, in addition to the standard hard reject rules above.

| # | Rule | Rationale |
|---|---|---|
| 1 | Payout ratio > 90% of FCF (non-REIT) or > 95% of AFFO (REIT) | No cushion; next bad quarter cuts the dividend |
| 2 | Dividend cut or suspension within trailing 5 years | Track record of unreliability |
| 3 | Yield > 2x sector median with no explained catalyst | Market is pricing in a cut the payout ratio hasn't caught yet |
| 4 | Debt-funded dividend (borrowing to pay, not from operations) | Structurally unsustainable |

### Dividend-Specific Inclusion Criteria

- Dividend growth streak: prioritize 5+ consecutive years of increases (use `fetch_stock_data.py` dividend history, same-quarter YoY comparison to avoid partial-year distortion)
- Payout ratio: <=60% of FCF (non-REIT) is the target zone; 60-75% acceptable if growth is durable; >75% needs a clear explanation
- FCF covers the dividend with room to spare in at least 3 of last 4 quarters
- Net debt/EBITDA <=3.5x (REITs and utilities: <=6.0x given their capital structure, but check coverage ratios instead of leaning on this alone)
- Piotroski F-Score >=5

### Screening for Candidates

Call `screen_stocks.py` with a `min_dividend_yield` filter and, if you want a sector focus, a `sector` filter (e.g. `"Utilities"`). Example payload: `{"market_cap_min": 50000000, "market_cap_max": 2000000000, "min_dividend_yield": 2.5, "sector": "Utilities", "count": 25}`.

### Dividend Eval Process

1. Pull dividend history, payout ratio, FCF, and debt metrics via `fetch_stock_data.py`
2. Check dividend-specific hard reject rules first
3. Check dividend-specific inclusion criteria
4. Run the standard Business Quality and Financial Strength components (abbreviated -- moat and F-Score still matter for durability) unless this is a fast SCAN pass across many tickers, in which case gate-only is fine
5. Classify: **QUALITY PAYER** (durable, growing, well-covered) / **WATCH** (yield attractive but coverage or growth thin) / **AVOID** (yield trap)

### Dividend Eval Output Format

```
DIVIDEND EVALUATION -- [TICKER] | [COMPANY NAME]
========================================
Date: [DATE] | Price: $[X] | Yield: [X%] | Market Cap: $[X]M

CLASSIFICATION: [QUALITY PAYER / WATCH / AVOID]

----------------------------------------
DIVIDEND PROFILE:
Current yield: [X%] | Sector median yield: [X%]
Consecutive years of increases: [X]
5-yr dividend CAGR: [X%]
Payout ratio (FCF basis): [X%]
FCF coverage (last 4 quarters): [covered / X of 4 quarters]

FINANCIAL STRENGTH:
Net debt/EBITDA: [X]x
F-Score: [X/max_possible]
Debt-funded dividend risk: [None / Flag]

----------------------------------------
WHY [QUALITY PAYER / WATCH / AVOID]:
[3-5 sentences. Be direct about payout sustainability, growth trajectory, and any yield-trap signals.]

RISKS TO THE DIVIDEND:
1. [Specific risk]
2. [Specific risk]

========================================
Disclaimer: This is not financial advice. All investing involves risk. Do your own due diligence before taking any position.
```

---

## Critical Rules

- **Never fabricate financial data.** If a figure can't be confirmed from a live source, flag as UNVERIFIED.
- **Hard reject rules have no exceptions.** Do not rationalize around them. If one applies, apply it.
- **Sell when the thesis breaks, not when the price rises.** Price gains confirm the thesis; they don't end it.
- **Social media, Reddit, newsletters are discovery tools only.** Zero weight in any BUY/HOLD/SELL decision.
- **Be direct.** "This is a REJECT because gross margins have eroded 400bps in three consecutive quarters while the narrative claims pricing power" is the right output. Not "there are some concerns to consider."
- **Boring businesses can be hidden compounders.** Do not penalize unglamorous industries. Evaluate economics, not aesthetics.
- **Quality beats cheap.** A 20x EV/FCF business compounding ROIC at 20% beats a 10x business with 8% ROIC over 10 years. Do not reflexively favor low multiples.
- **In Dividend Eval mode specifically: yield alone is never the decision.** A high yield with a shaky payout ratio is a warning sign, not a bonus.
- **Prefer the tested scripts in `../../shared/` over web search wherever they cover the need.**
