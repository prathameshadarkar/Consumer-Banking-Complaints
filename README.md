# Complaint Operations Console

**An operational review queue for consumer banking complaints, built end-to-end
in Palantir Foundry.**

99,898 CFPB complaints across 657 companies, reduced to a queue of **1,060
records with a recorded untimely response** — with the individual complaint,
its company and its issue one click away.

[**Case study with screenshots**](https://www.prathameshadarkar.com/complaint-operations.html)
· [Build journal](BUILD_JOURNAL.md)
· [Ontology](docs/ontology.md)

---

## The problem

A complaint operations team needs a place to start and the context to
investigate. A national export contains useful signal, but an operator still
has to get from an aggregate count to a single complaint — and a dashboard
that only shows counts leaves that last step undone.

This is built around that transition: start with the overall picture, narrow
to a review queue, select a company to inspect its history and response mix,
then open the individual complaint behind any row.

## What it does

Two Workshop views over a three-object ontology:

1. **Overall details** — four counts across the top, a filtered review queue,
   and a properties panel that resolves the selected complaint together with
   its linked Company and Issue. Beneath: response mix, top issues by volume,
   and the companies carrying the most flagged records.
2. **Company-wise details** — pick a company and the whole page follows: their
   complaint trend by week, their totals, and their response distribution.
   The selection drives a **link traversal**, not a string filter.

An embedded **AIP Analyst** answers follow-up questions by writing and running
a query against the ontology, with the source visible beside the answer.

## Findings in this snapshot

| | |
|---|---:|
| Complaints | 99,898 |
| Companies | 657 |
| Flagged for review (untimely response) | 1,060 &nbsp;·&nbsp; 1.06% |
| Reported in progress | 8,435 |
| With a public narrative | 30,798 &nbsp;·&nbsp; 30.8% |

**Flagged complaints are concentrated.** Five of 657 companies account for
**55% of all untimely responses**. Synchrony alone carries 215 — 20.3% of the
flagged set on 4.3% of complaint volume, a within-company rate of 5.02%
against a 1.06% baseline.

**Volume and review priority are different questions.** Capital One has the
largest complaint volume in the export at 8,830 and **zero** flagged records.
Ranking companies by complaints tells you about size; ranking by flagged
records tells you where responses are being missed.

**One issue dominates.** "Managing an account" accounts for 23,677 complaints,
roughly 24% of the dataset and 65% more than the next issue.

These describe this snapshot. They are not a ranking of company quality, and
they are not adjusted for customer base — a larger issuer will naturally
generate more complaints.

## Architecture

```
CFPB Consumer Complaint Database
        │  filtered export: 99,898 rows x 16 columns
        ▼
pipeline.py  ──►  rename · cast · parse dates · null handling
        │         derived flags · composite issue key
        ▼
Foundry: Pipeline Builder ──► Ontology ──► Workshop + AIP Analyst
                              Complaint ──► Company
                              Complaint ──► Issue
```

The data preparation is reproducible from this repo. The Foundry pipeline,
ontology and Workshop application were built in-platform;
[`BUILD_JOURNAL.md`](BUILD_JOURNAL.md) documents each decision and
[`docs/ontology.md`](docs/ontology.md) specifies the object model.

## The ontology

| Object type | Rows | Primary key | Title |
|---|---:|---|---|
| Complaint | 99,898 | `complaint_id` | `complaint_id` |
| Company | 657 | `company_name` | `company_name` |
| Issue | 42 | `issue_key` | `issue_name` |

Two many-to-one link types, both from Complaint. Product and State stayed
as properties — see [the ontology notes](docs/ontology.md) for why.

**What the ontology buys over a flat table:** the review queue and the
complaint detail are the same object, so selecting a row traverses to its
company and that company's other complaints without a join written in
advance. Re-slicing the queue by product is a filter, not a new pipeline.

## Running the pipeline

```bash
pip install -r requirements.txt
# download the CFPB export into data/ — see data/README.md
python pipeline.py --input data/complaints-2026-09-06_16_45.csv
```

Writes `output/complaints_clean.csv`, `companies.csv` and `issues.csv`, and
validates every count against the figures published above. It **raises rather
than writing** output that disagrees with them — publishing numbers that don't
match the screenshots would be worse than failing loudly.

```
INFO    raw: 99,898 rows x 16 columns
INFO      complaints      99,898
INFO      columns         19
INFO      companies          657
INFO      issues              42
INFO      flagged          1,060
INFO      in_progress      8,435
INFO      with_narrative  30,798
```

## Repo contents

| Path | What |
|---|---|
| `pipeline.py` | The Foundry transform stack, reproduced in pandas |
| `BUILD_JOURNAL.md` | Every decision and why |
| `docs/ontology.md` | Object types, keys, links, and the traversal argument |
| `DEMO_SCRIPT.md` | Three-minute walkthrough |
| `data/README.md` | How to reproduce the export, and the filters used |
| `output/flagged_sample.csv` | 200 most recent flagged complaints |

## Limitations

**"Flagged" means historically untimely, not currently open.** The rule uses
CFPB's published `Timely response?` field. It records whether a response met
the expected window — not how late it was, and not whether anything remains
outstanding.

**No elapsed-time measure exists in this data.** `Date sent to company` minus
`Date received` is CFPB's routing lag, not the company's response time. Any
"days overdue" figure would have to come from a firm's own case system.

**`Consumer disputed?` is absent** from the current export, so an escalation
rule combining untimely responses with consumer disputes — the original
design — isn't buildable against this data.

**Public complaints are not a representative sample.** They reflect who
chooses to complain to a federal regulator, which is not the same as who has
a problem.

**This has not been evaluated in a live operations team.** No claim is made
about time saved or outcomes improved. A prototype earns the right to be
evaluated, not the claim of having been.

## Source

[CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/)
· [Field definitions](https://www.consumerfinance.gov/complaint/data-use/)
· Public domain, redistributable.

Received dates 18 March – 1 September 2026 (UTC), exported 6 September 2026.

---

*Built by [Prathamesh Adarkar](https://www.prathameshadarkar.com).*

**Note on the live application:** the Workshop app runs on a Palantir AIP
developer-tier instance behind authentication and cannot be hosted publicly.
The [case study page](https://www.prathameshadarkar.com/complaint-operations.html)
carries full screenshots; this repo carries the reproducible data work.
