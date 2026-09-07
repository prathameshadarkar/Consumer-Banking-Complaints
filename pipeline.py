"""
pipeline.py — reproduces the Foundry data preparation in pandas.

The Complaint Operations Console was built inside Palantir Foundry: the
transforms below were authored in Pipeline Builder and the outputs backed
three ontology object types. Foundry pipelines are platform configuration,
not files, so this script re-implements the same logic locally. Running it
against the same CFPB export produces the same three tables Foundry does.

    Prepare Complaints   raw export ──► complaints_clean   (19 columns)
    Build dimensions     complaints_clean ──► companies, issues

Every transform below maps 1:1 to a step in the Foundry pipeline; the
comments name the Foundry transform used.

Usage
-----
    python pipeline.py --input data/complaints-2026-09-06_16_45.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

log = logging.getLogger("pipeline")

# --------------------------------------------------------------------------
# Configuration — every assumption in one auditable place
# --------------------------------------------------------------------------

# Foundry transform: "Rename: 16 columns"
RENAMES: dict[str, str] = {
    "Date received": "received_at",
    "Product": "product_name",
    "Sub-product": "sub_product",
    "Issue": "issue_name",
    "Sub-issue": "sub_issue",
    "Consumer complaint narrative": "narrative",
    "Company public response": "company_public_response",
    "Company": "company_name",
    "State": "state_code",
    "ZIP code": "zip_code",
    "Tags": "tags",
    "Submitted via": "submitted_via",
    "Date sent to company": "sent_to_company_at",
    "Company response to consumer": "company_response",
    "Timely response?": "timely_response_raw",
    "Complaint ID": "complaint_id",
}

# Foundry transform: five "Case" steps, each mapping the literal string
# "None" to a real null. CFPB writes "None" as text, not as a missing value,
# so without this every downstream null check silently returns False.
NULLABLE_NONE = [
    "state_code",
    "sub_issue",
    "company_public_response",
    "zip_code",
    "tags",
]

# The separator for the composite issue key. Two colons rather than one
# because a single colon plausibly appears inside a CFPB issue label.
ISSUE_KEY_SEP = "::"

# Expected results. The pipeline raises rather than writing output that
# disagrees with the Foundry build — a silent mismatch here would mean the
# repo and the screenshots describe different datasets.
EXPECT = {
    "complaints": 99_898,
    "columns": 19,
    "companies": 657,
    "issues": 42,
    "flagged": 1_060,
    "in_progress": 8_435,
    "with_narrative": 30_798,
}


# --------------------------------------------------------------------------
# Prepare Complaints
# --------------------------------------------------------------------------

def load_raw(path: Path) -> pd.DataFrame:
    """Read the CFPB export with every column as text.

    dtype=str and keep_default_na=False matter: pandas would otherwise coerce
    complaint IDs to floats and turn the literal "None" strings into NaN
    before we get a chance to handle them deliberately.
    """
    log.info("reading %s", path)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = set(RENAMES) - set(df.columns)
    if missing:
        raise ValueError(
            f"export is missing expected columns: {sorted(missing)}. "
            "CFPB occasionally renames fields; update RENAMES to match."
        )
    return df


def prepare_complaints(raw: pd.DataFrame) -> pd.DataFrame:
    """raw export → complaints_clean, mirroring the Foundry transform stack."""
    df = raw.rename(columns=RENAMES)[list(RENAMES.values())].copy()

    # Foundry: "Cast to String → complaint_id".
    # The ID is an identifier, not a quantity. Left numeric it would acquire
    # a decimal point somewhere downstream and stop joining.
    df["complaint_id"] = df["complaint_id"].astype(str).str.strip()

    # Foundry: "Convert legacy OffsetDateTime" on both date fields.
    for col in ("received_at", "sent_to_company_at"):
        df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
        if df[col].isna().any():
            raise ValueError(f"{col}: {df[col].isna().sum()} values failed to parse")

    # Foundry: five "Case" steps — literal "None" becomes a real null.
    for col in NULLABLE_NONE:
        df[col] = df[col].replace({"None": None, "": None})

    # The narrative is blank rather than "None" when absent.
    df["narrative"] = df["narrative"].replace({"": None})

    # Foundry: "Case → escalation_flag".
    # CFPB records timeliness as a yes/no outcome. It does NOT record how
    # late a response was, and sent_to_company_at measures routing lag, not
    # company response time — so no elapsed-days measure is derivable here.
    df["escalation_flag"] = df["timely_response_raw"].eq("No")

    # Foundry: "Case → is_in_progress".
    df["is_in_progress"] = df["company_response"].eq("In progress")

    # Foundry: "Concatenate strings → issue_key".
    # The same issue label appears under different products, so keying on the
    # label alone would merge unrelated categories into one object.
    df["issue_key"] = df["product_name"] + ISSUE_KEY_SEP + df["issue_name"]

    return df


# --------------------------------------------------------------------------
# Build dimensions
# --------------------------------------------------------------------------

def build_companies(clean: pd.DataFrame) -> pd.DataFrame:
    """One row per reported company — backs the Company object type."""
    return (
        clean[["company_name"]]
        .drop_duplicates()
        .sort_values("company_name")
        .reset_index(drop=True)
    )


def build_issues(clean: pd.DataFrame) -> pd.DataFrame:
    """One row per product-issue pair — backs the Issue object type.

    Deduplicating on issue_key rather than the label is the whole point:
    issue_name alone yields 36 rows and silently collapses issues that belong
    to different products.
    """
    return (
        clean[["issue_key", "issue_name", "product_name"]]
        .drop_duplicates(subset=["issue_key"])
        .sort_values("issue_key")
        .reset_index(drop=True)
    )


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def validate(clean: pd.DataFrame, companies: pd.DataFrame, issues: pd.DataFrame) -> dict:
    """Check the outputs against the published Foundry figures, and raise if
    they disagree. Publishing numbers that don't match the screenshots would
    be worse than failing loudly."""
    got = {
        "complaints": len(clean),
        "columns": clean.shape[1],
        "companies": len(companies),
        "issues": len(issues),
        "flagged": int(clean["escalation_flag"].sum()),
        "in_progress": int(clean["is_in_progress"].sum()),
        "with_narrative": int(clean["narrative"].notna().sum()),
    }
    if not clean["complaint_id"].is_unique:
        dupes = len(clean) - clean["complaint_id"].nunique()
        raise ValueError(f"complaint_id is not unique: {dupes} duplicates")

    bad = {k: (v, EXPECT[k]) for k, v in got.items() if v != EXPECT[k]}
    if bad:
        lines = [f"  {k}: got {g:,} expected {e:,}" for k, (g, e) in bad.items()]
        raise ValueError(
            "output does not match the published Foundry build:\n"
            + "\n".join(lines)
            + "\n\nIf you are running a different CFPB export this is expected — "
              "update EXPECT, and update the figures in the README to match."
        )
    return got


# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--input", type=Path,
        default=Path("data/complaints-2026-09-06_16_45.csv"),
        help="CFPB export CSV",
    )
    ap.add_argument("--outdir", type=Path, default=Path("output"))
    ap.add_argument("--skip-validation", action="store_true",
                    help="write output even if the counts differ")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")

    if not args.input.exists():
        log.error("input not found: %s", args.input)
        log.error("see data/README.md for how to reproduce the export")
        return 2

    raw = load_raw(args.input)
    log.info("raw: %s rows x %s columns", f"{len(raw):,}", raw.shape[1])

    clean = prepare_complaints(raw)
    companies = build_companies(clean)
    issues = build_issues(clean)

    if args.skip_validation:
        log.warning("validation skipped")
    else:
        stats = validate(clean, companies, issues)
        for k, v in stats.items():
            log.info("  %-15s %s", k, f"{v:,}")

    args.outdir.mkdir(parents=True, exist_ok=True)
    clean.to_csv(args.outdir / "complaints_clean.csv", index=False)
    companies.to_csv(args.outdir / "companies.csv", index=False)
    issues.to_csv(args.outdir / "issues.csv", index=False)

    # A small committed sample so the repo is browsable without a 76 MB file.
    (clean[clean["escalation_flag"]]
        .sort_values("received_at", ascending=False)
        .head(200)
        .to_csv(args.outdir / "flagged_sample.csv", index=False))

    log.info("wrote %s", args.outdir.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
