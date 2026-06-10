# VERIFY — "Done" Targets

These are concrete enough to hand to someone else and have them check without asking me what I meant. Each target names the number and the method.

## Correctness
**Target:** Every headline number on the dashboard matches the source daily table exactly (zero tolerance for integer counts; ±0.1 for derived ratios from rounding).
**Method:** `check_correctness.py` picks 5 random dates across the full history, queries `nyu-datasets.citibike.m_daily_trips` directly for total / member / casual / nyc / jc on those dates, and asserts they equal what the dashboard's cached dataframe produces for the same dates. Prints PASS/FAIL per date. Re-run after any data-layer change.

## Speed
**Target:** Cold load (first visitor, cache empty) completes in **under 4 seconds**. Warm interaction (moving a filter, cache hot) responds in **under 1 second**.
**Method:** Streamlit shows run time in the "Running…" indicator; confirm with a stopwatch on a fresh incognito session for cold load, and by eye for filter responsiveness. The cached-once design is what makes this achievable — if cold load exceeds 4s, the join/query is too heavy and should be narrowed, not the caching loosened.

## Reach
**Target:** The URL opens for someone who is not me, on a device not logged into my Google account, with no permission prompt.
**Method:** Deploy with `--allow-unauthenticated`. Post the URL in the class Slack and have at least 2 people confirm it loads for them. Not done until someone else has opened it.

## Clarity
**Target:** A stranger can state, for each of the 5 charts, what it shows and what the takeaway is, without me explaining it.
**Method:** Every chart title is a claim, not a label ("Casual riders drop more than members on rainy days" not "Rides by rider type"). Hand the live URL to one non-technical person and ask them to read each chart back to me. Any chart they can't read is not done.

## Defense (the Translate step)
**Target:** For each chart I can say one plain-English sentence stating what happens and how much — a number, not a direction. If a claim isn't visible in the chart, it isn't a finding and gets cut.
**Method:** Write the 5 sentences out before the demo. Each must contain a magnitude.
