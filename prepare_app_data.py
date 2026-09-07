"""
prepare_app_data.py — build the small data bundle the Streamlit app loads.

The cleaned dataset is ~76 MB and 99,898 rows. Streamlit Community Cloud gives
you limited memory and GitHub rejects files over 100 MB, so the app never loads
the full table. This script precomputes everything the app needs:

    flagged.parquet          1,060 flagged complaints, full detail
    company_summary.parquet  657 companies: totals, flagged, rate
    issue_summary.parquet    42 issues: volume and flagged count
    weekly.parquet           company x week counts, for the trend chart
    response_mix.parquet     company x company_response counts
    overview.json            the four headline figures

Total output is a couple of MB, which loads instantly and commits cleanly.

Usage
-----
    python pipeline.py --input data/complaints-2026-09-06_16_45.csv
    python prepare_app_data.py
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger("prepare")

# Columns the detail panel shows. Everything else is dropped from the app
# bundle — it would only inflate the repo.
DETAIL_COLS = [
    "complaint_id", "received_at", "company_name", "product_name",
    "sub_product", "issue_name", "sub_issue", "company_response",
    "state_code", "submitted_via", "narrative",
]


def build(clean: pd.DataFrame, outdir: Path) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    clean["received_at"] = pd.to_datetime(clean["received_at"], utc=True)

    # --- the flagged queue, in full -------------------------------------
    flagged = (
        clean[clean["escalation_flag"]][DETAIL_COLS]
        .sort_values("received_at", ascending=False)
        .reset_index(drop=True)
    )
    flagged.to_parquet(outdir / "flagged.parquet", index=False)

    # --- per-company summary --------------------------------------------
    company = (
        clean.groupby("company_name")
        .agg(
            complaints=("complaint_id", "size"),
            flagged=("escalation_flag", "sum"),
            in_progress=("is_in_progress", "sum"),
            with_narrative=("narrative", lambda s: s.notna().sum()),
        )
        .reset_index()
    )
    company["flagged_rate"] = (company["flagged"] / company["complaints"] * 100).round(2)
    company["share_of_flagged"] = (company["flagged"] / company["flagged"].sum() * 100).round(2)
    company = company.sort_values("complaints", ascending=False).reset_index(drop=True)
    company.to_parquet(outdir / "company_summary.parquet", index=False)

    # --- per-issue summary ----------------------------------------------
    issue = (
        clean.groupby(["issue_key", "issue_name", "product_name"])
        .agg(complaints=("complaint_id", "size"), flagged=("escalation_flag", "sum"))
        .reset_index()
        .sort_values("complaints", ascending=False)
    )
    issue.to_parquet(outdir / "issue_summary.parquet", index=False)

    # --- weekly volume, per company --------------------------------------
    wk = clean.copy()
    wk["week"] = wk["received_at"].dt.tz_localize(None).dt.to_period("W").dt.start_time
    weekly = (
        wk.groupby(["company_name", "week"])
        .agg(complaints=("complaint_id", "size"), flagged=("escalation_flag", "sum"))
        .reset_index()
    )
    weekly.to_parquet(outdir / "weekly.parquet", index=False)

    # --- response mix, per company ---------------------------------------
    mix = (
        clean.groupby(["company_name", "company_response"])
        .size().reset_index(name="complaints")
    )
    mix.to_parquet(outdir / "response_mix.parquet", index=False)

    # --- headline figures -------------------------------------------------
    overview = {
        "complaints": int(len(clean)),
        "companies": int(clean["company_name"].nunique()),
        "flagged": int(clean["escalation_flag"].sum()),
        "in_progress": int(clean["is_in_progress"].sum()),
        "with_narrative": int(clean["narrative"].notna().sum()),
        "flagged_rate": round(float(clean["escalation_flag"].mean() * 100), 2),
        "date_min": clean["received_at"].min().strftime("%Y-%m-%d"),
        "date_max": clean["received_at"].max().strftime("%Y-%m-%d"),
        "products": clean["product_name"].value_counts().to_dict(),
    }
    (outdir / "overview.json").write_text(json.dumps(overview, indent=2))
    return overview


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=Path("output/complaints_clean.csv"))
    ap.add_argument("--outdir", type=Path, default=Path("app_data"))
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    if not args.input.exists():
        log.error("run pipeline.py first — %s not found", args.input)
        return 2

    clean = pd.read_csv(args.input, low_memory=False)
    log.info("loaded %s rows", f"{len(clean):,}")
    ov = build(clean, args.outdir)
    for k, v in ov.items():
        if not isinstance(v, dict):
            log.info("  %-15s %s", k, v)

    total = sum(f.stat().st_size for f in args.outdir.iterdir())
    log.info("bundle: %s files, %.1f MB", len(list(args.outdir.iterdir())), total / 1e6)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
