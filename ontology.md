# The ontology

Three object types, two link types. The whole argument for building this in
Foundry rather than a BI tool lives here.

## Object types

| Object type | Backing dataset | Rows | Primary key | Title property |
|---|---|---:|---|---|
| **Complaint** | `complaints_clean` | 99,898 | `complaint_id` | `complaint_id` |
| **Company** | `companies` | 657 | `company_name` | `company_name` |
| **Issue** | `issues` | 42 | `issue_key` | `issue_name` |

### Complaint properties

| Property | Type | Notes |
|---|---|---|
| `complaint_id` | string | Primary key. Cast from integer — it is an identifier, not a quantity |
| `received_at` | timestamp | UTC |
| `sent_to_company_at` | timestamp | UTC. **Routing lag, not response time** |
| `company_name` | string | Foreign key to Company |
| `product_name` | string | Three values |
| `sub_product` | string | |
| `issue_name` | string | 36 distinct labels |
| `sub_issue` | string | Nullable — 17.4% missing |
| `issue_key` | string | Foreign key to Issue. `product_name :: issue_name` |
| `narrative` | string | Nullable — 69.2% missing |
| `company_response` | string | Five values |
| `company_public_response` | string | Nullable |
| `timely_response_raw` | string | `Yes` / `No` |
| `escalation_flag` | boolean | Derived: `timely_response_raw = "No"` |
| `is_in_progress` | boolean | Derived: `company_response = "In progress"` |
| `state_code` | string | Nullable — 1,230 missing |
| `zip_code` | string | Kept as text: leading zeros and masks like `331XX` |
| `tags` | string | Nullable |
| `submitted_via` | string | |

## Link types

Complaint is the **many** side of both. Reverse link named `Complaints`.

| From | Property | To | Key | Cardinality |
|---|---|---|---|---|
| Complaint | `company_name` | Company | `company_name` | many-to-one |
| Complaint | `issue_key` | Issue | `issue_key` | many-to-one |

## Design decisions

### Why `issue_key` and not `issue_name`

`issue_name` has **36 distinct values**; `product_name :: issue_name` has
**42**. Six labels appear under more than one product — "Managing an account"
exists under both Checking or savings and Money transfer, for instance.

Keying Issue on the label alone would silently merge those into one object,
so a complaint about managing a checking account and one about managing a
crypto wallet would resolve to the same Issue. The merge is invisible: nothing
errors, the counts just quietly become wrong.

The `::` separator rather than a single colon because a single colon
plausibly occurs inside a CFPB issue label.

### Why Product and State are not object types

Both were considered and rejected.

**Product** has three members. An object type with three rows is a dropdown,
not an object graph — it adds a link to traverse and gives nothing back that a
property doesn't already give.

**State** has 58 values including territories and military codes, and is null
for 1,230 complaints. It would only earn an object type alongside geographic
views, which this application doesn't have. Promoting it would mean either
dropping 1,230 complaints from the link or carrying a null-keyed object.

Both remain properties on Complaint, so they still appear in the detail panel,
the table and the charts. They just aren't things an operator navigates
*through*.

### Why `escalation_flag` is a derived property, not a filter

The rule is currently a single recorded field — CFPB's `Timely response?`. A
real operations team would tune it against their own SLA, likely combining
timeliness with case age and issue severity.

Modelling it as a derived property on the object rather than as a filter in
each widget means that change happens **once**. Every metric card, chart and
table on both pages reads from the same property and follows automatically.
As a per-widget filter, the same change would mean editing eleven widgets and
hoping none were missed.

That is the honest version of why the flag is where it is. It is one field
today; the point is what happens when it stops being one field.

## What the ontology buys over a flat table

The concrete answer, not the generic one:

**The queue and the detail are the same object.** Selecting a row in the
review queue doesn't look anything up — the Complaint object is already
resolved, and its Company and Issue come with it. No join was written in
advance because there is no join.

**The company view is a traversal, not a filter.** Choosing a company walks
`Company → Complaints` and returns that company's complaint set. Every widget
on the page — trend, totals, response mix — reads from that one object set.
Adding a fourth widget means pointing it at the same variable, not writing a
fourth query.

**Re-slicing is a filter, not a pipeline.** If operations asks tomorrow for
the same queue split by product, that's a filter on an existing object set.
In a BI tool built on flat extracts it is a new query, a new extract, and a
new thing to keep in sync.
