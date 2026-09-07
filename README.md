# Reproducing the export

The raw file is ~76 MB and is not committed. To regenerate it:

1. Go to the [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/)
2. Open **Download the data**
3. Apply these filters **before** downloading — the unfiltered database is
   millions of rows:

   | Filter | Value |
   |---|---|
   | Date received | 2026-03-18 to 2026-09-01 |
   | Product | Credit card |
   | | Checking or savings account |
   | | Money transfer, virtual currency, or money service |

4. Export as CSV and save it here.

That should give **99,898 rows across 16 columns**, covering 657 companies.

## Why credit reporting is excluded

Credit reporting is by far the largest CFPB product category and is dominated
by automated, bulk-submitted disputes. Including it would swamp every
operational signal in the dataset: the queue would be almost entirely
credit-reporting records, and the company rankings would measure dispute-bot
volume rather than complaint handling.

Excluding it is a scoping decision, not a data-quality one, and it is the
single most consequential choice in this project.

## A note on dates

The export was pulled on 6 September 2026 but the latest received date
present is 1 September. CFPB publishes with a lag, so the final period in any
time series is partial and will understate volume. Charts in the application
show this as a drop at the right-hand edge; it is a publication artefact, not
a decline in complaints.
