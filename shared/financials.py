#!/usr/bin/env python3
"""
Structured financial statement extraction from SEC XBRL data via
edgartools -- backs longterm-quality-investor's Piotroski F-Score,
ROIC, margin, and valuation math. fetch_stock_data.py (Yahoo Finance)
only exposes summary ratios, not balance sheet / income statement /
cash flow line items or multi-period history, so anything requiring
those (F-Score, ROIC, gross/operating margin, EV/EBITDA, multi-year
trends) has to come from here instead.

Verified live against Company("GSAT").get_financials() -- period
columns are date-labeled (e.g. "2025-12-31 (FY)"), and standard_concept
values confirmed by direct inspection are:
  Income:  Revenue, OperatingIncomeLoss, NetIncome, DepreciationExpense
           (GrossProfit not always reported -- falls back to label search)
  Balance: Assets, CurrentAssetsTotal, CurrentLiabilitiesTotal,
           Liabilities, LongTermDebt, AllEquityBalance
  Cash flow / shares outstanding standard_concept names were not
  verified live -- both use a label-text fallback search rather than
  a hardcoded standard_concept, and return None (not a fabricated
  value) if nothing matches.

Input (stdin): JSON {
  "ticker": "GSAT",
  "periods": 3,
  "market_cap": 4900000000,
  "total_cash": 500000000,
  "total_debt": 200000000,
  "free_cashflow": 300000000,
  "identity": "Your Name your.email@example.com"
}
  identity can also come from env var EDGAR_IDENTITY instead.
  market_cap/total_cash/total_debt/free_cashflow are optional
  passthroughs from fetch_stock_data.py, used for EV/EV-EBITDA/
  FCF-conversion/cash-runway calcs that need a Yahoo-sourced figure
  alongside the filing data.

Requires: uv run --with edgartools python3 financials.py
"""
import json
import os
import sys

from edgar import Company, set_identity


def get_identity(payload: dict) -> str:
    identity = payload.get("identity") or os.environ.get("EDGAR_IDENTITY")
    if not identity:
        raise RuntimeError(
            "Missing SEC identity string. Provide via payload 'identity' "
            "or EDGAR_IDENTITY env var, e.g. 'Your Name your.email@example.com'."
        )
    return identity


def _num(x):
    try:
        if x is None:
            return None
        v = float(x)
        if v != v:  # NaN check without importing math -- NaN is the
            return None  # only float that doesn't equal itself
        return v
    except (TypeError, ValueError):
        return None


def _safe_df(fn):
    try:
        return fn()
    except Exception:
        return None


def _get_column_for_period(df, period_index: int):
    """Period columns are date-labeled, e.g. '2025-12-31 (FY)' -- pick
    the Nth most recent by column position, since edgartools already
    orders them most-recent-first."""
    meta_cols = {"concept", "label", "standard_concept", "level", "abstract",
                 "dimension", "is_breakdown", "dimension_axis", "dimension_member",
                 "dimension_member_label", "dimension_label", "balance", "weight",
                 "preferred_sign", "parent_concept", "parent_abstract_concept"}
    period_cols = [c for c in df.columns if c not in meta_cols]
    if period_index >= len(period_cols):
        return None
    return period_cols[period_index]


def _top_level_only(df):
    """Drop XBRL dimensional-breakdown rows (segment/member sub-lines)
    -- confirmed live that matching one of these instead of the
    consolidated total produces NaN/garbage for periods the segment
    wasn't separately broken out in. Keep only rows where is_breakdown
    is falsy (False, None, or missing)."""
    if "is_breakdown" not in df.columns:
        return df
    return df[df["is_breakdown"].fillna(False) == False]  # noqa: E712


def _find_by_standard_concept(df, concept_name: str, periods: int):
    if df is None or df.empty or "standard_concept" not in df.columns:
        return None
    candidates = _top_level_only(df)
    matches = candidates[candidates["standard_concept"] == concept_name]
    if not len(matches):
        return None
    row = matches.iloc[0]
    out = []
    for i in range(periods):
        col = _get_column_for_period(df, i)
        out.append(_num(row[col]) if col else None)
    return out


def _find_by_label(df, *substrings, periods: int):
    """Fallback when standard_concept lookup misses or is unreliable
    for a given filer -- case-insensitive substring match on the
    human-readable label, first match wins. Dimensional-breakdown rows
    are excluded for the same reason as the standard_concept lookup."""
    if df is None or df.empty or "label" not in df.columns:
        return None
    candidates = _top_level_only(df)
    for s in substrings:
        mask = candidates["label"].astype(str).str.contains(s, case=False, na=False)
        matches = candidates[mask]
        if len(matches):
            row = matches.iloc[0]
            out = []
            for i in range(periods):
                col = _get_column_for_period(df, i)
                out.append(_num(row[col]) if col else None)
            return out
    return None


def _find_line(df, concept_name: str, *label_fallbacks, periods: int):
    result = _find_by_standard_concept(df, concept_name, periods)
    if result is not None:
        return result
    return _find_by_label(df, *label_fallbacks, periods=periods)


def get_statement_dataframes(ticker: str, periods: int):
    company = Company(ticker)
    financials = company.get_financials()
    if financials is None:
        raise RuntimeError(f"No financials available for {ticker}")

    income_df = _safe_df(lambda: financials.income_statement().to_dataframe())
    balance_df = _safe_df(lambda: financials.balance_sheet().to_dataframe())
    cashflow_df = _safe_df(lambda: financials.cash_flow_statement().to_dataframe())
    return income_df, balance_df, cashflow_df


def extract_line_items(income_df, balance_df, cashflow_df, periods: int) -> dict:
    """Every value is a list, most-recent-period first. A None entry
    means that line item genuinely wasn't found in the filing for that
    period -- never estimated."""
    return {
        "revenue": _find_line(income_df, "Revenue", "total revenue", "net revenue", periods=periods),
        "gross_profit": _find_line(income_df, "GrossProfit", "gross profit", periods=periods),
        "operating_income": _find_line(income_df, "OperatingIncomeLoss", "income (loss) from operations", "operating income", periods=periods),
        "net_income": _find_line(income_df, "NetIncome", "net income", "net loss", periods=periods),
        "depreciation_amortization": _find_line(income_df, "DepreciationExpense", "depreciation and amortization", periods=periods),
        "total_assets": _find_line(balance_df, "Assets", "total assets", periods=periods),
        "current_assets": _find_line(balance_df, "CurrentAssetsTotal", "total current assets", periods=periods),
        "current_liabilities": _find_line(balance_df, "CurrentLiabilitiesTotal", "total current liabilities", periods=periods),
        "total_liabilities": _find_line(balance_df, "Liabilities", "total liabilities", periods=periods),
        "long_term_debt": _find_line(balance_df, "LongTermDebt", "long-term debt", "long term debt", periods=periods),
        "stockholders_equity": _find_line(balance_df, "AllEquityBalance", "total stockholders", "total equity", periods=periods),
        "operating_cash_flow": _find_line(cashflow_df, "NetCashFromOperatingActivities", "net cash provided by operating activities", "net cash from operating", "cash provided by operating", periods=periods),
        "shares_outstanding": _find_line(balance_df, "CommonStockSharesOutstanding", "shares outstanding", "common shares outstanding", periods=periods),
    }


def compute_ratios(items: dict, periods: int) -> list:
    """Per-period ratio dicts, most recent first."""
    out = []
    for i in range(periods):
        def at(key):
            vals = items.get(key)
            if vals is None or i >= len(vals):
                return None
            return vals[i]

        revenue = at("revenue")
        gross_profit = at("gross_profit")
        operating_income = at("operating_income")
        net_income = at("net_income")
        total_assets = at("total_assets")
        current_assets = at("current_assets")
        current_liabilities = at("current_liabilities")
        long_term_debt = at("long_term_debt")
        operating_cash_flow = at("operating_cash_flow")

        out.append({
            "gross_margin": (gross_profit / revenue) if gross_profit is not None and revenue else None,
            "operating_margin": (operating_income / revenue) if operating_income is not None and revenue else None,
            "roa": (net_income / total_assets) if net_income is not None and total_assets else None,
            "current_ratio": (current_assets / current_liabilities) if current_assets is not None and current_liabilities else None,
            "cfo_to_assets": (operating_cash_flow / total_assets) if operating_cash_flow is not None and total_assets else None,
            "asset_turnover": (revenue / total_assets) if revenue is not None and total_assets else None,
            "debt_to_assets": (long_term_debt / total_assets) if long_term_debt is not None and total_assets else None,
        })
    return out


def _signal(value, test):
    if value is None:
        return None
    try:
        return 1 if test(value) else 0
    except Exception:
        return None


def _signal_pair(a, b, test):
    if a is None or b is None:
        return None
    try:
        return 1 if test(a, b) else 0
    except Exception:
        return None


def compute_piotroski(ratios: list, items: dict) -> dict:
    """9-point Piotroski F-Score. The 3 profitability signals (F1, F3,
    F4) only need the current period; the other 6 are YoY comparisons
    and need a second period. Any signal that can't be computed from
    what the filing actually reports is None, not guessed -- the total
    is scored out of however many signals resolved, with the rest
    listed explicitly so nothing is silently treated as a pass or fail."""
    if not ratios:
        return {"score": None, "signals": {}, "note": "no data"}

    cur = ratios[0]
    prev = ratios[1] if len(ratios) > 1 else None
    cfo_vals = items.get("operating_cash_flow") or []
    shares_vals = items.get("shares_outstanding") or []

    signals = {
        "f1_positive_roa": _signal(cur["roa"], lambda v: v > 0),
        "f2_roa_improved": _signal_pair(cur["roa"], prev["roa"] if prev else None, lambda a, b: a > b),
        "f3_positive_cfo": _signal(cfo_vals[0] if cfo_vals else None, lambda v: v > 0),
        "f4_accruals": _signal_pair(cur["cfo_to_assets"], cur["roa"], lambda a, b: a > b),
        "f5_leverage_decreased": _signal_pair(
            prev["debt_to_assets"] if prev else None, cur["debt_to_assets"],
            lambda p, c: c < p),
        "f6_liquidity_improved": _signal_pair(cur["current_ratio"], prev["current_ratio"] if prev else None, lambda a, b: a > b),
        "f7_no_dilution": None,
        "f8_gross_margin_improved": _signal_pair(cur["gross_margin"], prev["gross_margin"] if prev else None, lambda a, b: a > b),
        "f9_asset_turnover_improved": _signal_pair(cur["asset_turnover"], prev["asset_turnover"] if prev else None, lambda a, b: a > b),
    }
    if len(shares_vals) > 1 and shares_vals[0] is not None and shares_vals[1] is not None:
        signals["f7_no_dilution"] = 1 if shares_vals[0] <= shares_vals[1] * 1.005 else 0

    scored = [v for v in signals.values() if v is not None]
    missing = [k for k, v in signals.items() if v is None]

    return {
        "score": sum(scored) if scored else None,
        "max_possible": len(scored),
        "signals": signals,
        "missing_signals": missing,
        "note": (
            "Score is out of max_possible, not out of 9 -- missing_signals "
            "lists what this filing didn't let us compute. Treat a score "
            "with several missing signals as lower-confidence, not as a "
            "clean pass."
        ) if missing else None,
    }


def compute_roic(items: dict) -> dict:
    """NOPAT / invested capital. NOPAT uses an assumed 21% effective
    tax rate (US federal statutory) since the filing's actual effective
    rate isn't broken out here -- flagged as an estimate, not a filed
    figure. Invested capital = total assets - current liabilities,
    a standard simplification (excludes non-interest-bearing current
    liabilities from the capital base)."""
    oi = (items.get("operating_income") or [None])[0]
    assets = (items.get("total_assets") or [None])[0]
    cur_liab = (items.get("current_liabilities") or [None])[0]

    if oi is None:
        return {"roic": None, "note": "no operating income available"}
    nopat = oi * (1 - 0.21)
    if assets is None or cur_liab is None:
        return {"roic": None, "nopat": round(nopat, 2), "note": "insufficient balance sheet data for invested capital"}
    invested_capital = assets - cur_liab
    if invested_capital <= 0:
        return {"roic": None, "nopat": round(nopat, 2), "note": "non-positive invested capital"}
    return {
        "roic": round(nopat / invested_capital, 4),
        "nopat": round(nopat, 2),
        "invested_capital": round(invested_capital, 2),
        "note": "NOPAT assumes a 21% effective tax rate, not the filer's actual rate -- treat as an estimate.",
    }


def compute_fcf_conversion(net_income, free_cashflow) -> dict:
    if net_income is None or free_cashflow is None or net_income == 0:
        return {"fcf_conversion": None}
    return {"fcf_conversion": round(free_cashflow / net_income, 4)}


def compute_ev(market_cap, total_debt, total_cash) -> dict:
    if market_cap is None:
        return {"ev": None, "note": "market_cap not provided in payload"}
    return {"ev": market_cap + (total_debt or 0) - (total_cash or 0)}


def compute_cash_runway_months(cash, net_income_ttm) -> dict:
    if cash is None or net_income_ttm is None:
        return {"cash_runway_months": None}
    if net_income_ttm >= 0:
        return {"cash_runway_months": None, "note": "net income is positive -- runway only applies to cash-burning companies"}
    monthly_burn = abs(net_income_ttm) / 12
    if monthly_burn == 0:
        return {"cash_runway_months": None}
    return {"cash_runway_months": round(cash / monthly_burn, 1)}


def main():
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "reason": f"invalid JSON input: {e}"}))
        sys.exit(1)

    ticker = payload.get("ticker")
    if not ticker:
        print(json.dumps({"status": "error", "reason": "no ticker provided"}))
        sys.exit(1)

    periods = payload.get("periods", 3)
    market_cap = payload.get("market_cap")
    total_cash = payload.get("total_cash")
    total_debt = payload.get("total_debt")
    free_cashflow = payload.get("free_cashflow")

    try:
        set_identity(get_identity(payload))
        income_df, balance_df, cashflow_df = get_statement_dataframes(ticker, periods)
        items = extract_line_items(income_df, balance_df, cashflow_df, periods)
        ratios = compute_ratios(items, periods)
        piotroski = compute_piotroski(ratios, items)
        roic = compute_roic(items)

        net_income_latest = (items.get("net_income") or [None])[0]
        fcf_conv = compute_fcf_conversion(net_income_latest, free_cashflow)
        ev = compute_ev(market_cap, total_debt, total_cash)

        oi = (items.get("operating_income") or [None])[0]
        da = (items.get("depreciation_amortization") or [None])[0]
        ebitda = (oi + da) if (oi is not None and da is not None) else None
        ev_ebitda = round(ev["ev"] / ebitda, 2) if (ev.get("ev") is not None and ebitda) else None

        runway = compute_cash_runway_months(total_cash, net_income_latest)

        result = {
            "status": "ok",
            "ticker": ticker,
            "periods_returned": len(items.get("revenue") or []),
            "line_items": items,
            "ratios_by_period": ratios,
            "piotroski_f_score": piotroski,
            "roic": roic,
            "fcf_conversion": fcf_conv,
            "ebitda": ebitda,
            "ev": ev,
            "ev_ebitda": ev_ebitda,
            "cash_runway": runway,
        }
    except Exception as e:
        print(json.dumps({"status": "error", "reason": str(e), "ticker": ticker}))
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
