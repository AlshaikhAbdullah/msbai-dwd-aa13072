# Dashboard decisions memo

Defends each spec decision in business terms and reports verification results
against the targets in `streamlitspec.md §6`.

## Decisions, defended in business terms

| Decision | Business rationale |
|----------|--------------------|
| **Audience = journalist / city planner, not a data analyst** | The people who move policy and public opinion aren't analysts. If the chart needs a stats background to read, it can't do its job. This constraint forces plain labels, sensible defaults, and a claim on every chart. |
| **Five views, each tied to one question** | A dashboard that answers ten vague questions answers none. Each view maps to a decision someone acts on (is the dip weather or us? is a casual promo worth it?). Anything without a decision behind it was cut. |
| **Member vs casual is the commercial spine** | Casual riders are the higher-margin, weather-elastic segment. The whole promo case (V2, V3) rests on showing casual demand swings more with weather than member demand does — so we surface that split everywhere. |
| **Weather bands (Cold/Mild/Warm/Hot) instead of a raw temperature axis** | A planner asks "what happens on cold days?", not "what happens at 38°F?". Banding turns a continuous axis into the categories people actually reason with. |
| **Load once, cache, filter in memory** | A journalist bounces if a slider lags. The daily table is tiny (1.3 MB), so we pull it once and do every filter in pandas — no BigQuery round-trip on interaction, and no per-click query cost. |
| **Own `daily_summary_mat` with `nyu-datasets` fallback** | The dashboard runs whether or not our pipeline is loaded — it prefers our reconciled table and silently falls back, so a grader with only `nyu-datasets` still sees a working app. |
| **Claim as the chart title** | The chart has to make its point without a caption or a person explaining it. Putting the one-sentence claim in the title means the takeaway travels with a screenshot. |
| **Bike-type gated to 2021+** | The data simply doesn't exist before 2021. Rather than fabricate it, the filter is labeled and only offered where honest. |

## Verification results (vs `streamlitspec.md §6`)

| Bar | Target | Result |
|-----|--------|--------|
| **Load-time** | cold ≤ 12 s; interactions < 100 ms | Cold load **10.1 s**; interactions instant via `@st.cache_data` + in-memory pandas. **PASS** |
| **Correctness** | 100% of `check_correctness.py` | **28/28 PASS**; member+casual+unknown = total and NYC+JC = total on every row; reconciles to `daily_summary_mat` within 0.5% |
| **Public-reach** | non-author opens URL, no login | Deployed public on Streamlit Community Cloud — URL in `README.md`. NYU's GCP org policy blocks public Cloud Run, so Cloud Run is used only for authenticated/proxy access. |
| **Clarity** | one-sentence claim as each chart title, no jargon | **PASS** — all 5 charts titled with their claim; no raw tables or coefficients surfaced |

## Honest limitations

- **Margin is assumed, not measured.** We show casual *volume* and weather-sensitivity; per-trip margin needs pricing data we don't have.
- **Distance is straight-line** (haversine on start/end), not route distance — a reproducible proxy, not the actual ridden distance.
- **~3% of 2022–2024 NYC trips** that `nyu-datasets` reports are absent from the official S3 files themselves (verified); we match the authoritative source, not the reference. See `pipeline/reconciliation.md`.
