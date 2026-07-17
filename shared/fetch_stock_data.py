#!/usr/bin/env python3
"""
Shared stock/fundamentals/ownership data fetcher, backing
swing-trade-scanner, longterm-quality-investor, and
catalyst-growth-investor.

Input (stdin): JSON {"tickers": ["AAPL", "GSAT"], "fields": [...]}
  fields is optional -- omit for the default full bundle.
  Valid field group names: "price", "fundamentals", "dividends",
  "insiders", "institutional", "analyst"

Output (stdout): JSON {ticker: {...fetched fields...}, ...}
  On a per-ticker failure, that ticker's value is
  {"error": "..."} rather than failing the whole batch.

Data lag caveats (from Yahoo Finance, not this script's fault):
  price/volume ~15-20 min delayed; insider trades ~2-3 days;
  short interest ~2 weeks (FINRA reporting cycle).

Requires: uv run --with yfinance python3 fetch_stock_data.py
"""
import json
import sys

import yfinance as yf

DEFAULT_FIELDS = ["price", "fundamentals", "dividends", "insiders",
                   "institutional", "analyst"]


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def fetch_price(t: yf.Ticker) -> dict:
    info = t.info
    return {
        "price": info.get("currentPrice"),
        "market_cap": info.get("marketCap"),
        "volume": info.get("volume"),
        "avg_volume_3m": info.get("averageVolume"),
        "float_shares": info.get("floatShares"),
        "shares_outstanding": info.get("sharesOutstanding"),
        "fifty_two_wk_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_wk_low": info.get("fiftyTwoWeekLow"),
        "short_pct_of_float": info.get("shortPercentOfFloat"),
        "beta": info.get("beta"),
    }


def fetch_fundamentals(t: yf.Ticker) -> dict:
    info = t.info
    return {
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "price_to_sales": info.get("priceToSalesTrailing12Months"),
        "profit_margin": info.get("profitMargins"),
        "revenue_growth": info.get("revenueGrowth"),
        "earnings_growth": info.get("earningsGrowth"),
        "total_cash": info.get("totalCash"),
        "total_debt": info.get("totalDebt"),
        "free_cashflow": info.get("freeCashflow"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
    }


def fetch_dividends(t: yf.Ticker) -> dict:
    info = t.info
    # Pull enough history to span ~6 years of quarterly payments even
    # with a partial current year; resampling into calendar years was
    # tested and rejected -- it distorts partial first/last years and
    # produces false "decreases". Compare same-period year-over-year
    # on the raw payment series instead.
    hist = _safe(lambda: t.dividends.tail(24), default=None)
    cagr_5y = None
    consecutive_increases = None
    if hist is not None and len(hist) >= 8:
        try:
            vals = hist.tolist()
            n_per_year = _infer_payments_per_year(hist)
            if n_per_year and len(vals) > n_per_year:
                # True 5-year CAGR: compare latest payment against the
                # payment from ~5 years back (5 * n_per_year positions
                # earlier), not against last year -- a 1-year gap raised
                # to the (1/years) power with years=span-of-whole-window
                # was the earlier bug (produced ~0.25-0.45% instead of
                # the real multi-percent annual raise).
                lookback = min(5 * n_per_year, len(vals) - 1)
                actual_years = lookback / n_per_year
                base = vals[-1 - lookback]
                if base > 0 and actual_years >= 1:
                    cagr_5y = round(
                        ((vals[-1] / base) ** (1 / actual_years) - 1) * 100, 2
                    )
                increases = 0
                i = len(vals) - 1
                while i - n_per_year >= 0:
                    if vals[i] > vals[i - n_per_year]:
                        increases += 1
                        i -= n_per_year
                    else:
                        break
                consecutive_increases = increases
        except Exception:
            pass
    return {
        "dividend_yield_pct": info.get("dividendYield"),
        "dividend_rate": info.get("dividendRate"),
        "payout_ratio": info.get("payoutRatio"),
        "five_year_avg_yield": info.get("fiveYearAvgDividendYield"),
        "ex_dividend_date": info.get("exDividendDate"),
        "dividend_cagr_est_pct": cagr_5y,
        "consecutive_annual_increases_est": consecutive_increases,
    }


def _infer_payments_per_year(hist) -> int:
    """Guess payment frequency (4=quarterly, 12=monthly, 1=annual) from
    the average gap between the last several payment dates."""
    try:
        recent = hist.tail(8).index
        if len(recent) < 2:
            return 4
        gaps_days = [(recent[i] - recent[i - 1]).days for i in range(1, len(recent))]
        avg_gap = sum(gaps_days) / len(gaps_days)
        if avg_gap < 45:
            return 12
        if avg_gap < 200:
            return 4
        return 1
    except Exception:
        return 4


def fetch_insiders(t: yf.Ticker) -> dict:
    purchases = _safe(lambda: t.insider_purchases)
    transactions = _safe(lambda: t.insider_transactions)
    recent = None
    if transactions is not None and len(transactions):
        try:
            recent = transactions.head(10).to_dict(orient="records")
        except Exception:
            recent = None
    summary = None
    if purchases is not None and len(purchases):
        try:
            summary = purchases.to_dict(orient="records")
        except Exception:
            summary = None
    return {
        "insider_purchase_summary": summary,
        "recent_insider_transactions": recent,
    }


def fetch_institutional(t: yf.Ticker) -> dict:
    inst = _safe(lambda: t.institutional_holders)
    major = _safe(lambda: t.major_holders)
    info = t.info
    return {
        "pct_held_institutions": info.get("heldPercentInstitutions"),
        "pct_held_insiders": info.get("heldPercentInsiders"),
        "top_institutional_holders": (
            inst.head(5).to_dict(orient="records") if inst is not None and len(inst) else None
        ),
        "major_holders_summary": (
            major.to_dict() if major is not None else None
        ),
    }


def fetch_analyst(t: yf.Ticker) -> dict:
    info = t.info
    upgrades = _safe(lambda: t.upgrades_downgrades)
    recent_actions = None
    if upgrades is not None and len(upgrades):
        try:
            recent_actions = upgrades.head(10).reset_index().to_dict(orient="records")
        except Exception:
            recent_actions = None
    return {
        "recommendation_key": info.get("recommendationKey"),
        "target_mean_price": info.get("targetMeanPrice"),
        "target_high_price": info.get("targetHighPrice"),
        "target_low_price": info.get("targetLowPrice"),
        "number_of_analysts": info.get("numberOfAnalystOpinions"),
        "recent_upgrades_downgrades": recent_actions,
    }


FIELD_FUNCS = {
    "price": fetch_price,
    "fundamentals": fetch_fundamentals,
    "dividends": fetch_dividends,
    "insiders": fetch_insiders,
    "institutional": fetch_institutional,
    "analyst": fetch_analyst,
}


def fetch_one(ticker: str, fields: list) -> dict:
    try:
        t = yf.Ticker(ticker)
        result = {}
        for f in fields:
            fn = FIELD_FUNCS.get(f)
            if fn:
                result.update(fn(t))
        return result
    except Exception as e:
        return {"error": str(e)}


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "reason": f"invalid JSON input: {e}"}))
        sys.exit(1)

    tickers = payload.get("tickers", [])
    fields = payload.get("fields", DEFAULT_FIELDS)

    if not tickers:
        print(json.dumps({"status": "error", "reason": "no tickers provided"}))
        sys.exit(1)

    output = {tk: fetch_one(tk, fields) for tk in tickers}
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
