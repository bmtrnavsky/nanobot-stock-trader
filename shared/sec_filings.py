#!/usr/bin/env python3
"""
SEC EDGAR filings/insider data via edgartools (free, MIT-licensed, no
API key -- requires only an identity string per SEC fair-access policy).

Input (stdin): JSON {
  "ticker": "GSAT",
  "checks": ["recent_filings", "insider_form4", "going_concern"],
  "identity": "Your Name your.email@example.com"
}
  identity can also come from env var EDGAR_IDENTITY instead.

Output (stdout): JSON with requested checks as top-level keys.

Requires: uv run --with edgartools python3 sec_filings.py
"""
import json
import os
import sys

from edgar import Company, set_identity

DEFAULT_CHECKS = ["recent_filings", "insider_form4"]


def get_identity(payload: dict) -> str:
    identity = payload.get("identity") or os.environ.get("EDGAR_IDENTITY")
    if not identity:
        raise RuntimeError(
            "Missing SEC identity string. SEC's fair-access policy "
            "requires a name+email in every request. Provide via "
            "payload 'identity' or EDGAR_IDENTITY env var, e.g. "
            "'Your Name your.email@example.com'."
        )
    return identity


def check_recent_filings(company, limit: int = 10) -> list:
    filings = company.get_filings().head(limit)
    return [
        {
            "form": f.form,
            "filed": str(f.filing_date),
            "accession_no": f.accession_no,
            "url": f.filing_url,
        }
        for f in filings
    ]


def check_insider_form4(company, limit: int = 10) -> list:
    filings = company.get_filings(form="4").head(limit)
    return [
        {
            "filed": str(f.filing_date),
            "url": f.filing_url,
            "accession_no": f.accession_no,
        }
        for f in filings
    ]


def check_going_concern(company) -> dict:
    """Cheap heuristic: grep the latest 10-K/10-Q for going-concern
    language via edgartools' built-in grep. Real hits are rare and
    material -- worth a manual read of the filing, not just trusting
    the keyword match. tenk.text() doesn't exist on TenK objects
    (tested); tenk.grep(pattern) is the real, working API."""
    latest = company.latest_tenk or company.latest_tenq
    if latest is None:
        return {"checked": False, "reason": "no 10-K/10-Q found"}
    try:
        gc_hit = latest.grep("going concern")
        doubt_hit = latest.grep("substantial doubt")
        flagged = bool(gc_hit) or bool(doubt_hit)
    except Exception as e:
        return {"checked": False, "reason": str(e)}
    return {
        "checked": True,
        "filing_form": latest.form,
        "filing_date": str(latest.filing_date),
        "going_concern_language_found": flagged,
    }


CHECK_FUNCS = {
    "recent_filings": check_recent_filings,
    "insider_form4": check_insider_form4,
}


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

    checks = payload.get("checks", DEFAULT_CHECKS)

    try:
        set_identity(get_identity(payload))
        company = Company(ticker)
        result = {"status": "ok", "ticker": ticker}
        for c in checks:
            if c == "going_concern":
                result[c] = check_going_concern(company)
            elif c in CHECK_FUNCS:
                result[c] = CHECK_FUNCS[c](company)
    except Exception as e:
        print(json.dumps({"status": "error", "reason": str(e)}))
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
