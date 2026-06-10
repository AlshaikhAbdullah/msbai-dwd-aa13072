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
| Q5 | When ridership moves, is it **system-wide or localized** to one side of the river (NYC vs Jersey City)? A localized dip points to an operational cause, not weather. | NYC-vs-JC ridership (§4, V5) |

**Honesty note on margin:** the assignment asserts casual riders carry higher margins; v1 takes that as given for *framing* but only *shows* casual volume and weather-sensitivity, which is what the daily data supports. Actual per-trip margin is reserved for the revenue stretch goal.

---

## 3. What a Visitor Can Filter

Only filters the data can actually support are listed. Nothing is promised that won't be wired up. Column availability confirmed against `nyu-datasets.citibike.m_daily_trips` joined to `nyu-datasets.weather.m_weather_daily_nyc`.

- **Date range** — default to full history; lets the visitor zoom to a season, a year, or a single weather event. *Caveat surfaced in UI:* bike-type breakdowns only have data from 2021 onward.
- **Rider type** — All / Member / Casual (`num_member_trips`, `num_casual_trips`). Central to Q2 and Q3.
- **Weather band** — three independent bands the visitor can apply: **temperature** on `tavg_f` bucketed cold (<40°F) / mild (40–60°F) / warm (60–75°F) / hot (>75°F); **wet/dry** via `is_rainy`; **snow** via `is_snowy`. Cutoffs are fixed and stated so they're defensible, not arbitrary.
- **Geography** — All / NYC / Jersey City (`num_nyc_trips`, `num_jc_trips`). This is the system's only geography granularity — there are no station coordinates (see §6).
- **Bike type** — All / Classic / Electric (`num_classic_trips`, `num_electric_trips`). *Constraint:* this filters the daily **total** only. The daily table has no bike-type × rider-type cross-tab, so this filter does **not** combine with the rider-type toggle. Data exists 2021 onward.

---

## 4. Views Exposed

Four focused views beat ten cluttered ones. Each names *why* it is in front of this non-technical visitor — this doubles as the pre-written "defend the spec" answer.

- **V1 — Ridership over time, weather overlaid.** Daily/weekly rides as the primary line, a chosen weather variable (temperature, precipitation) overlaid. *Why:* lets the visitor eyeball whether a dip lines up with bad weather (explainable) or doesn't (worth a manager's attention). Directly answers Q1.
- **V2 — Rides vs temperature.** Binned curve or scatter showing the *shape* of the relationship, **split by rider type (member vs casual)** — this split is supported by the daily table. *Why:* shows where demand is elastic to weather and for whom — the basis of any promo decision (Q3). *Note:* a separate bike-type dimension (classic vs electric over time) is shown standalone, not crossed with rider type, since no such cross-tab exists in the data.
- **V3 — Member vs casual across weather bands.** Share or volume of each rider type across weather conditions. *Why:* isolates the higher-margin casual segment's weather behavior (Q2).
- **V4 — Seasonality.** Rides by month and by day-of-week — using the `season`, `month`, `day_of_week`, `is_weekend` columns already present on the weather table. *Why:* separates calendar effects from weather effects, so the visitor doesn't mistake "it's July" for "it was sunny." Guards every other view against a false weather story.
- **V5 — NYC vs Jersey City.** Ridership for each side of the river over time. *Why:* a dip on only one side is an operational/local signal, not weather (which hits both); answers Q5. This is the only geography slice the data supports — no station-level map.

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
- **Not station-level geography.** The daily table is aggregated to NYC vs Jersey City totals (`num_nyc_trips`, `num_jc_trips`) — that two-way split *is* exposed (V5). There are no station coordinates, so there is no map.
- **Not a data-analyst tool.** No raw tables, no model coefficients, no statistical jargon surfaced to the visitor.

---

## 7. Data Source

- Primary: my own daily trips table in BigQuery, joined to NYC weather on `date`.
- Fallback (schema confirmed): `nyu-datasets.citibike.m_daily_trips` joined to `nyu-datasets.weather.m_weather_daily_nyc` on `date`.
- Rider type, geography (NYC/JC), and rider×geography splits are available as daily totals. Bike type (`num_classic_trips`, `num_electric_trips`) is a total-only dimension with data **2021 onward** and no rider cross-tab.
- Weather band is computed at app load (bucketing `tavg_f`), not a stored column.
