# Build journal

What was decided, and why. Written as the build happened rather than
reconstructed afterwards, including the parts that went wrong.

---

## 1. Scoping the export

**Decision: exclude credit reporting.**

Credit reporting is the largest CFPB product category by a wide margin and is
dominated by automated bulk disputes. Included, the review queue would have
been almost entirely credit-reporting records and the company rankings would
have measured dispute-bot volume rather than complaint handling.

Kept: credit card, checking or savings account, and money transfer / virtual
currency. Twelve months narrowed to roughly six to keep the row count
workable on a developer-tier instance.

Result: 99,898 rows, 657 companies, 16 columns.

This is the single most consequential decision in the project and it is a
scoping call, not a data-quality one. Someone could reasonably disagree.

## 2. Two corrections to the original design

Both surfaced when the actual export was inspected rather than assumed.

**`Consumer disputed?` no longer exists.** The intended escalation rule was
`untimely response OR consumer disputed`. That field is absent from current
CFPB exports, along with `Consumer consent provided?`. The rule became
timeliness alone.

**`Date sent to company` is not a response time.** It records when CFPB
forwarded the complaint to the company — routing lag. The gap between it and
`Date received` says nothing about how quickly the company replied. A
`days_to_company` metric was planned, built, and then dropped once it became
clear it would be read as responsiveness.

The consequence is worth stating plainly: **this dataset supports no
elapsed-time measure at all.** "Flagged" is a yes/no outcome. If someone asks
how overdue a complaint is, the correct answer is that this data can't tell
you and a real deployment would join to the firm's own case system.

## 3. Preparing the data

Thirteen transforms in Pipeline Builder, all reproduced in `pipeline.py`.

**Renamed all 16 columns** to snake_case.

**Cast `complaint_id` to string.** It arrives as an integer. Left numeric it
acquires a decimal point somewhere downstream and stops joining.

**Converted both date fields** off the legacy `OffsetDateTime` type — flagged
by a pipeline warning, not noticed unaided.

**Replaced literal `"None"` with real nulls** across five fields:
`state_code`, `sub_issue`, `company_public_response`, `zip_code`, `tags`.
CFPB writes "None" as text. Without this every downstream null check silently
returns false and the missing-data figures are wrong. This was five near-
identical Case transforms and it was the fiddliest part of the build.

**Kept `zip_code` as text.** Values include leading zeros and masks like
`331XX`.

**Two boolean rules:** `escalation_flag` from `Timely response? = No`, and
`is_in_progress` from `Company response = In progress`.

**A composite `issue_key`.** See below.

## 4. `issue_key`: a bug avoided by counting first

`issue_name` has 36 distinct values. `product_name :: issue_name` has 42.

Six issue labels appear under more than one product. Keying the Issue object
on the label alone would have merged those pairs into single objects — a
complaint about managing a checking account and one about managing a crypto
wallet resolving to the same Issue.

Nothing would have errored. The counts would just have been quietly wrong,
and the error would have been invisible in the finished application.

Caught by checking the distinct counts of both candidate keys before building
the object type rather than after.

## 5. Two pipelines, not one

The first attempt at branching inside `Prepare Complaints` inserted the new
transform **inline** rather than in parallel, which broke `complaints_clean`
— the output dropped a column and the deploy warned about it.

Rather than fight the graph, the dimension tables moved into a second
pipeline (`Build dimensions`) taking `complaints_clean` as its input. Cleaner
separation anyway: one pipeline cleans, one derives.

A follow-on trap: the second pipeline cached the input schema from when it was
added, so it couldn't see `issue_key` until the upstream output was re-synced
with **Use upstream schema** and redeployed.

## 6. The ontology

Complaint, Company and Issue as object types; Product and State left as
properties. Reasoning in [`docs/ontology.md`](docs/ontology.md).

`Complaint` was created before `issue_key` existed, so the object type had 18
properties against a 19-column dataset and the link couldn't be built. Adding
a property to an existing object type means creating it and then mapping it to
a backing column — created but unmapped, it sits as "Edit-only" and looks
correct while being empty.

**A near-miss on the Issue primary key.** The object-type editor defaulted
both the key and the title to `Issue Name`. `issue_name` is not unique — 36
values across 42 rows — so that would have failed the build or silently
collapsed six issues. Key moved to `issue_key`, title left on `issue_name` so
the panel displays `Fees or interest` rather than
`Credit card::Fees or interest`.

## 7. The application

Two Workshop pages.

**Overall details** — four metric cards, a review queue filtered to
`escalation_flag = true`, and an object view bound to the table's active
object. Below: response mix, top issues, and companies by flagged count.

**Company-wise details** — an object dropdown over Company, feeding an object
set variable that **traverses** `Company → Complaints`. Every widget on the
page reads from that one variable.

The first version filtered Complaint by company name string instead. It
produced the same numbers and was the wrong thing: a string match is what a
BI tool does, and the traversal is the entire reason for building here.

**A sorting bug worth recording.** The companies chart initially sorted by
key ascending — alphabetically — so it showed Abra, ACIMA, ADP with counts of
8, 1 and 3. It looked like a working chart. It was showing the first five
companies in the alphabet rather than the top five by volume. Changed to
value descending, which surfaced the concentration finding.

**AIP Analyst** embedded for follow-up questions. It writes and runs a query
against the ontology and exposes the source. That distinction matters:
retrieval-based assistants approximate counts, and a confidently wrong number
in front of an operator is worse than no assistant.

## 8. What was deliberately not built

**Write-back Actions.** A Review Case object with ownership and status, so a
reviewer could act rather than only look. This is the clearest gap and it is
the next thing to build.

**A weighted priority score.** `escalation_flag` is currently one recorded
field. A designed score — timeliness, case age, the company's rolling rate,
issue-trend velocity — would be more useful and more defensible. Deliberately
out of scope for a first build; a score invented without an operator to
calibrate against is a guess with a decimal point.

**A map.** `state_code` and `zip_code` are strings with no coordinates, so a
Foundry map widget has nothing to plot. It would need a geocoding join. A
bar chart of the top states carries the same information and renders.

## 9. Sharing

The Workshop application runs on a Palantir AIP developer-tier instance behind
authentication. Foundry's Public Applications feature exists but requires an
Ontology SDK frontend built separately plus an Information Security Officer
approval within the enrollment — not available on a developer tier.

So the application isn't publicly hostable, and that shapes what's here: the
[case study page](https://www.prathameshadarkar.com/complaint-operations.html)
carries the screenshots, this repo carries the reproducible data work, and the
demo video carries the interaction.
