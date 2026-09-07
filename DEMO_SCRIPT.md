## 0:00 — What this is (20s)

> "This is a complaint review console for a bank's operations team, built in
> Palantir Foundry. It takes 99,898 public CFPB complaints and turns them into
> a queue of the 1,060 where the company's response was recorded as untimely."

Overall details page, full screen.

## 0:20 — The counts (20s)

Point at each card.

> "99,898 complaints, 657 companies, 1,060 flagged, 8,435 still in progress.
> The flagged number is 1.06% — that's the review queue."

## 0:40 — Queue to complaint (40s)

Click a row with a narrative.

> "The queue is the important part. Selecting a row doesn't run a lookup —
> the complaint is an object, so its properties and its linked Company and
> Issue resolve together. No join was written in advance."

Scroll the panel to the linked objects.

> "That's what the ontology buys. In a BI tool this is a second query."

## 1:20 — Concentration (30s)

Point at the companies chart.

> "Flagged complaints aren't spread evenly. Five companies out of 657 carry
> 55% of them. Synchrony alone has 215 — a fifth of the entire flagged set on
> four percent of volume."

## 1:50 — Company view (40s)

Switch tabs, select Synchrony.

> "Selecting a company traverses the link. Their trend, their totals, their
> response mix — every widget reads from one traversal, not a filter."

Switch to Capital One.

> "And this is why volume is the wrong ranking. Capital One has the most
> complaints in the whole export — 8,830 — and zero flagged. Size and review
> priority are different questions."

## 2:30 — AIP (25s)

Ask: *"Which company has the most flagged complaints?"*

Wait for the answer, then open **View source**.

> "The assistant doesn't summarise — it writes a query against the ontology
> and runs it. The source is visible, so the answer is checkable. That matters:
> a confidently wrong count is worse than no assistant."

## 2:55 — Close (10s)

> "Data prep is reproducible from the repo. The build journal covers every
> decision, including what I got wrong."
