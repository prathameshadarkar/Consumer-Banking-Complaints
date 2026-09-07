"""
Complaint Operations Console — web companion.

The original of this application was built in Palantir Foundry: a Pipeline
Builder pipeline, an ontology of Complaint / Company / Issue object types with
link traversals, two Workshop views and an embedded AIP Analyst. That instance
sits behind authentication on a developer tier and cannot be hosted publicly.

This is the same analysis, same data, same review rule, rebuilt as something
anyone can open. It is a companion to that project, not a copy of it — there
is no ontology here, and the company view filters rather than traverses.

Data is precomputed by prepare_app_data.py into app_data/ (~450 KB), so the
app never loads the 99,898-row table.
"""
from __future__ import annotations

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "app_data"

ACCENT = "#60A5FA"
WARN = "#F87171"
MUTED = "#6E7C90"
GRID = "#212A38"

st.set_page_config(
    page_title="Complaint Operations Console",
    page_icon="◧",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load() -> dict:
    if not DATA.exists():
        st.error(
            "`app_data/` not found. Run `python pipeline.py` then "
            "`python prepare_app_data.py` to build it."
        )
        st.stop()
    return {
        "overview": json.loads((DATA / "overview.json").read_text()),
        "flagged": pd.read_parquet(DATA / "flagged.parquet"),
        "company": pd.read_parquet(DATA / "company_summary.parquet"),
        "issue": pd.read_parquet(DATA / "issue_summary.parquet"),
        "weekly": pd.read_parquet(DATA / "weekly.parquet"),
        "mix": pd.read_parquet(DATA / "response_mix.parquet"),
    }


d = load()
ov = d["overview"]


# --------------------------------------------------------------------------
# Chart helpers — one style, applied everywhere
# --------------------------------------------------------------------------

def hbar(df: pd.DataFrame, y: str, x: str, colour: str, y_title: str = "", x_title: str = ""):
    """Horizontal bar. Horizontal because every label here is a sentence."""
    return (
        alt.Chart(df)
        .mark_bar(color=colour, cornerRadiusEnd=3, height=18)
        .encode(
            y=alt.Y(f"{y}:N", sort="-x", title=y_title,
                    axis=alt.Axis(labelLimit=280, labelFontSize=12)),
            x=alt.X(f"{x}:Q", title=x_title, axis=alt.Axis(grid=True, gridColor=GRID)),
            tooltip=list(df.columns),
        )
        .properties(height=max(160, 30 * len(df)))
    )


def line(df: pd.DataFrame, x: str, y: str, colour: str, x_title: str = "", y_title: str = ""):
    return (
        alt.Chart(df)
        .mark_line(color=colour, point=alt.OverlayMarkDef(color=colour, size=32), strokeWidth=2)
        .encode(
            x=alt.X(f"{x}:T", title=x_title, axis=alt.Axis(grid=False)),
            y=alt.Y(f"{y}:Q", title=y_title, axis=alt.Axis(grid=True, gridColor=GRID)),
            tooltip=list(df.columns),
        )
        .properties(height=260)
    )


def donut(df: pd.DataFrame, cat: str, val: str):
    return (
        alt.Chart(df)
        .mark_arc(innerRadius=62, stroke="#0B0F1A", strokeWidth=2)
        .encode(
            theta=alt.Theta(f"{val}:Q"),
            color=alt.Color(f"{cat}:N", legend=alt.Legend(title=None, orient="bottom",
                                                          labelLimit=220, columns=1),
                            scale=alt.Scale(scheme="blues")),
            tooltip=[cat, val],
        )
        .properties(height=300)
    )


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Complaint Operations Console")
    st.caption(
        f"CFPB consumer complaints · {ov['date_min']} to {ov['date_max']} · "
        f"{ov['companies']} companies"
    )
    view = st.radio("View", ["Overall details", "Company-wise details"], label_visibility="collapsed")
    st.divider()

    if view == "Company-wise details":
        opts = d["company"].sort_values("flagged", ascending=False)["company_name"].tolist()
        selected = st.selectbox("Company", opts, index=0)
        st.caption("Ordered by flagged complaints, so the list opens on the ones that matter.")
    else:
        selected = None

    st.divider()
    st.caption(
        "**Flagged** means CFPB recorded the company's response as untimely "
        "(`Timely response? = No`). It is a historical outcome, not a claim "
        "that a complaint is still open — and the data holds no elapsed-time "
        "measure, so the console can count late responses but not how late."
    )
    st.caption(
        "Built as a companion to a Palantir Foundry application that cannot be "
        "hosted publicly. [Case study](https://www.prathameshadarkar.com/complaint-operations.html)"
    )


# --------------------------------------------------------------------------
# Overall details
# --------------------------------------------------------------------------

if view == "Overall details":
    st.title("Overall details")
    st.caption(
        "99,898 consumer complaints against 657 companies, reduced to the "
        f"{ov['flagged']:,} where the response was recorded as untimely."
    )

    c = st.columns(4)
    c[0].metric("Total complaints", f"{ov['complaints']:,}")
    c[1].metric("Flagged for review", f"{ov['flagged']:,}", f"{ov['flagged_rate']}% of total",
                delta_color="off")
    c[2].metric("In progress", f"{ov['in_progress']:,}")
    c[3].metric("Companies", f"{ov['companies']:,}")

    st.divider()

    left, right = st.columns([1.35, 1])

    with left:
        st.subheader("Flagged for review")
        q = d["flagged"].copy()
        q["received"] = pd.to_datetime(q["received_at"]).dt.strftime("%b %d, %Y")
        st.dataframe(
            q[["complaint_id", "received", "company_name", "product_name",
               "issue_name", "company_response"]],
            hide_index=True, height=380, width="stretch",
            column_config={
                "complaint_id": "ID",
                "received": "Received",
                "company_name": "Company",
                "product_name": "Product",
                "issue_name": "Issue",
                "company_response": "Response",
            },
        )

        st.subheader("Complaint detail")
        ids = d["flagged"]["complaint_id"].astype(str).tolist()
        cid = st.selectbox("Complaint ID", ids, label_visibility="collapsed")
        row = d["flagged"][d["flagged"]["complaint_id"].astype(str) == cid].iloc[0]

        f = st.columns(2)
        f[0].markdown(f"**Company**  \n{row['company_name']}")
        f[0].markdown(f"**Product**  \n{row['product_name']}")
        f[0].markdown(f"**Issue**  \n{row['issue_name']}")
        f[1].markdown(f"**Received**  \n{pd.to_datetime(row['received_at']).strftime('%d %B %Y')}")
        f[1].markdown(f"**Response**  \n{row['company_response']}")
        f[1].markdown(f"**State**  \n{row['state_code'] or '—'}")

        narrative = row["narrative"]
        if isinstance(narrative, str) and narrative.strip():
            st.text_area("Consumer narrative", narrative, height=150, disabled=True)
        else:
            st.info(
                "No public narrative. 69% of complaints have none — the consumer "
                "did not consent to publication. The structured fields still support review."
            )

    with right:
        st.subheader("Companies with the most flagged")
        top = d["company"].nlargest(10, "flagged")[["company_name", "flagged", "complaints", "flagged_rate"]]
        st.altair_chart(hbar(top, "company_name", "flagged", WARN, "", "Flagged complaints"),
                        width="stretch")
        share = top["flagged"].sum() / ov["flagged"] * 100
        st.caption(
            f"The top ten of {ov['companies']} companies account for "
            f"**{share:.0f}%** of every flagged complaint in the dataset."
        )

        st.subheader("Product mix")
        prod = pd.DataFrame(
            [{"product": k, "complaints": v} for k, v in ov["products"].items()]
        )
        st.altair_chart(donut(prod, "product", "complaints"), width="stretch")

    st.divider()
    st.subheader("Issues by volume")
    iss = (d["issue"].groupby("issue_name", as_index=False)["complaints"].sum()
           .nlargest(10, "complaints"))
    st.altair_chart(hbar(iss, "issue_name", "complaints", ACCENT, "", "Complaints"),
                    width="stretch")
    lead = iss.iloc[0]
    st.caption(
        f"“{lead['issue_name']}” alone accounts for {lead['complaints']:,} complaints — "
        f"{lead['complaints'] / ov['complaints'] * 100:.0f}% of the dataset."
    )


# --------------------------------------------------------------------------
# Company-wise details
# --------------------------------------------------------------------------

else:
    row = d["company"][d["company"]["company_name"] == selected].iloc[0]
    st.title(selected.title())
    st.caption("Metrics, trend and response mix for the selected company.")

    c = st.columns(4)
    c[0].metric("Complaints", f"{int(row['complaints']):,}")
    c[1].metric("Flagged", f"{int(row['flagged']):,}")
    c[2].metric(
        "Flagged rate", f"{row['flagged_rate']:.2f}%",
        f"{row['flagged_rate'] - ov['flagged_rate']:+.2f} pts vs {ov['flagged_rate']}% baseline",
        delta_color="inverse",
    )
    c[3].metric("Share of all flagged", f"{row['share_of_flagged']:.1f}%")

    st.divider()

    left, right = st.columns([1.4, 1])

    with left:
        st.subheader("Complaints per week")
        w = d["weekly"][d["weekly"]["company_name"] == selected].sort_values("week")
        if len(w) > 1:
            st.altair_chart(line(w.iloc[:-1], "week", "complaints", ACCENT, "", "Complaints"),
                            width="stretch")
            st.caption(
                "The final week is dropped: the export ends 1 September, so it covers "
                "a partial period and would read as a collapse."
            )
        else:
            st.info("Not enough weekly history to plot a trend for this company.")

    with right:
        st.subheader("How they resolve complaints")
        m = d["mix"][d["mix"]["company_name"] == selected]
        if len(m):
            st.altair_chart(donut(m, "company_response", "complaints"), width="stretch")
        else:
            st.info("No response data for this company.")

    st.divider()
    st.subheader(f"Flagged complaints · {int(row['flagged'])}")
    cf = d["flagged"][d["flagged"]["company_name"] == selected].copy()
    if len(cf):
        cf["received"] = pd.to_datetime(cf["received_at"]).dt.strftime("%b %d, %Y")
        st.dataframe(
            cf[["complaint_id", "received", "product_name", "issue_name", "company_response"]],
            hide_index=True, width="stretch", height=300,
            column_config={
                "complaint_id": "ID", "received": "Received",
                "product_name": "Product", "issue_name": "Issue",
                "company_response": "Response",
            },
        )
    else:
        st.success(
            f"{selected.title()} has no complaints with a recorded untimely response. "
            "Volume and review priority are different questions — the company with the "
            "largest complaint volume in this dataset has zero flagged records."
        )

st.divider()
st.caption(
    "Source: [CFPB Consumer Complaint Database]"
    "(https://www.consumerfinance.gov/data-research/consumer-complaints/). "
    f"Snapshot taken 6 September 2026, covering {ov['date_min']} to {ov['date_max']}. "
    "CFPB updates records retroactively, so these figures describe this snapshot rather "
    "than a fixed dataset. Public complaints are not a representative measure of customer "
    "experience, and counts are not adjusted for customer base."
)
