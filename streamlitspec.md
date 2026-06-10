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



---

## 4. Views Exposed

Four focused views beat ten cluttered ones. Each names *why* it is in front of this non-technical visitor — this doubles as the pre-written "defend the spec" answer.

- **V1 — Ridership over time, weather overlaid.** Daily/weekly rides as the primary line, a chosen weather variable (temperature, precipitation) overlaid. *Why:* lets the visitor eyeball whether a dip lines up with bad weather (explainable) or doesn't (worth a manager's attention). Directly answers Q1.


---

## 5. What "Good" Means

The quality bar the Verify targets make measurable. Stated here as intent; concrete numbers live in the separate Verify targets.

- **Correct** — every number reconciles to the source daily table; verified by a check script, not assumed.
- **Fast** — loads quickly enough that a journalist won't bounce; data is cached and loaded once, all filtering happens in memory (never re-queries BigQuery on a slider move).
- **Public** — the URL is genuinely open; tested by someone other than me.
- **Clear** — a stranger understands each chart without me in the room; every chart title states the claim it makes.

---

## 6. Non-Goals (v1)

A spec is as much about what is *not* built. These boundaries are deliberate.

- **Not predictive.** v1 is descriptive. Forecasting next week's ridership is a stretch goal, and only with a held-out-history error reported.
- **Not reconstructed revenue.** Any dollar figure (stretch only) applies *today's* pricing across all history as a yardstick, clearly labeled as such — not historical revenue, since prices have changed many times.

- **Not a data-analyst tool.** No raw tables, no model coefficients, no statistical jargon surfaced to the visitor.

---

## 7. Data Source


