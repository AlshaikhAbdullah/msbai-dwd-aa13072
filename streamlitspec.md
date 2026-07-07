# SPEC — NYC Weather × Citibike Ridership Dashboard

*Author: Abdullah Alshaikh*
*Status: v1 — descriptive. Predictive and revenue work are out of scope for v1 (see Non-Goals).*

---

## 1. Purpose & Audience

A public, interactive dashboard that lets a **non-technical decision-maker — a journalist or a city planner, explicitly not a data analyst** — explore how NYC weather relates to Citibike ridership across the full available history.

The dashboard exists to support **decisions, not decoration**. Every view is here to help answer a real operational or commercial question: when ridership moves, is it the weather or is it us, and where is there money to be made by acting on the weather. Naming the audience up front constrains every choice below: defaults are sensible, labels are plain English, and no chart assumes the reader can read a regression table.

---

## 2. Business Questions This Dashboard Answers

These are the spine of the product. Each question is phrased as a decision someone acts on, and each maps to exactly one view. If a question has no view behind it, it is cut.

| # | Question | View that answers it |
|---|----------|----------------------|
| Q1 | Is a given period's ridership change driven by **weather** or by something **operational** we control? | Ridership-over-time with weather overlay (§4, V1) |
| Q2 | How does the **weather sensitivity of casual riders** differ from members? Casual riders carry higher margin, so their responsiveness is the commercially interesting one. | Member-vs-casual across weather bands (§4, V3) |
| Q3 | Given Q2, does a **weather-triggered promo aimed at casual riders** make sense — is there a forecastable window where casual demand is elastic to good weather? | Rides-vs-temperature relationship, split by rider type (§4, V2) |
| Q4 | What does a **typical weather day** look like for ridership, so an unusual day is recognizable as unusual? | Seasonality view — rides by month / day-of-week (§4, V4) |


**Honesty note on margin:** the assignment asserts casual riders carry higher margins; v1 takes that as given for *framing* but only *shows* casual volume and weather-sensitivity, which is what the daily data supports. Actual per-trip margin is reserved for the revenue stretch goal.

---

## 3. What a Visitor Can Filter

All filters live in the sidebar and act on the in-memory dataframe — moving one never re-queries BigQuery. They are chosen so a non-technical visitor can reproduce any headline claim.

| Filter | Options | Why it exists |
|--------|---------|---------------|
| **Date range** | Any window within 2013-06 → present | Isolate the period a journalist is writing about (a heat wave, a snow month, a specific year) |
| **Rider type** | All / Member / Casual | The member-vs-casual split is the commercial spine (Q2, Q3); the visitor can reshape every time-series to one segment |
| **Weather band** | All / Cold <40°F / Mild 40–60°F / Warm 60–75°F / Hot >75°F | Ask "what happens on cold days?" without reading a temperature axis |
| **Precipitation** | All / Dry days / Rainy days | Separate the effect of rain from the effect of temperature |
| **Bike type** | All / Classic / E-bike (2021+ only, labeled) | Inspect the classic-vs-electric shift; honestly gated to years where the data exists |

---

## 4. Views Exposed

Five focused views beat ten cluttered ones. Each names *why* it is in front of this non-technical visitor — this doubles as the pre-written "defend the spec" answer. Every chart's **title is the one-sentence claim** it makes.

- **V1 — Ridership over time, weather overlaid.** Daily rides (7-day average) as the primary line, a chosen weather variable (temperature or precipitation) overlaid on a second axis. *Why:* lets the visitor eyeball whether a dip lines up with bad weather (explainable) or doesn't (worth a manager's attention). Answers **Q1**.
- **V2 — Rides vs temperature, split by rider type.** Scatter of daily rides against average temperature with a smoothed trend per rider type. *Why:* shows casual demand is steeper in temperature than member demand — the elasticity that makes a weather-triggered promo worth considering. Answers **Q3**.
- **V3 — Member vs casual across weather bands.** Grouped bars of average daily rides per weather band. *Why:* the casual/member gap widens in bad weather, so casual demand is the elastic, promotable segment. Answers **Q2**.
- **V4 — Seasonality (month & day-of-week).** Average rides by calendar month and by weekday. *Why:* separates "it's July" from "it was sunny" so an unusual day is recognizable as unusual. Answers **Q4**.
- **V5 — NYC vs Jersey City over time.** 7-day-average daily rides for each region. *Why:* JC is a separate operational footprint at a fraction of the volume; its weather sensitivity may differ. Context for all of the above.

---

## 5. What "Good" Means

The quality bar the Verify targets (§6) make measurable.

- **Correct** — every number reconciles to the source daily table; verified by a check script, not assumed.
- **Fast** — loads quickly enough that a journalist won't bounce; data is cached and loaded once, all filtering happens in memory (never re-queries BigQuery on a slider move).
- **Public** — the URL is genuinely open; tested by someone other than me.
- **Clear** — a stranger understands each chart without me in the room; every chart title states the claim it makes.

## 6. Verify Targets (concrete)

| Bar | Target | How measured | Result |
|-----|--------|--------------|--------|
| **Load-time** | Cold load ≤ 12 s; every filter interaction < 100 ms (no BigQuery re-query) | time `load_data()`; confirm `@st.cache_data` + in-memory pandas | Cold load **10.1 s**; interactions instant (cached). **PASS** |
| **Correctness** | 100% of `check_correctness.py` checks pass; member+casual+unknown = total and NYC+JC = total on every row | run the gate script | **28/28 PASS** |
| **Public-reach** | A person who is not the author opens the URL with no Google login and sees the dashboard | someone else loads the README URL on their own device | *pending public deploy (see README)* |
| **Clarity** | Each of the 5 charts shows a one-sentence English claim as its title; no jargon, no raw tables | visual inspection | **PASS** — claims are chart titles |

---

## 7. Data Source

- **Primary:** `msbai-dwd-aa13072.citibike.daily_summary_mat` — this project's own materialized daily table (day × region × rider × bike), built by the pipeline in `pipeline/`.
- **Fallback:** `nyu-datasets.citibike.m_daily_trips` — used automatically if the project table is absent/empty.
- **Weather (both cases):** `nyu-datasets.weather.m_weather_daily_nyc`, joined on `date`.
- The app loads the small daily table **once**, joins weather, computes weather bands, and caches the result; all filtering is in-memory.

---

## 6. Non-Goals (v1)

A spec is as much about what is *not* built. These boundaries are deliberate.

- **Not predictive.** v1 is descriptive. Forecasting next week's ridership is a stretch goal, and only with a held-out-history error reported.
- **Not reconstructed revenue.** Any dollar figure (stretch only) applies *today's* pricing across all history as a yardstick, clearly labeled as such — not historical revenue, since prices have changed many times.

- **Not a data-analyst tool.** No raw tables, no model coefficients, no statistical jargon surfaced to the visitor.

---

## 7. Data Source


