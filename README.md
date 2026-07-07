# msbai-dwd-aa13072 — NYC Weather × Citibike Ridership

Dealing with Data Using Python. A data pipeline (BigQuery) + public Streamlit
dashboard exploring how NYC weather relates to Citibike ridership across the full
history (2013–present, NYC + Jersey City).

## Live dashboard

**Public URL:** _TODO — paste the Streamlit Community Cloud URL here after deploy_

Opens with no login and loads in ~10 s (data cached; all filtering in-memory).

## Repo layout

| Path | What |
|------|------|
| `pipeline/` | BigQuery loaders, SQL views, materialized table, reconciliation (`pipeline/README.md`) |
| `pipeline/reconciliation.md` | Independent-source verification vs `nyu-datasets.citibike` |
| `dashboard/` | Streamlit app (`app.py`), data loader (`data.py`), correctness gate |
| `streamlitspec.md` | Dashboard spec: questions, filters, views, Verify targets |
| `dashboard/DECISIONS.md` | Decisions memo + verification results |
| `CLAUDE.md` | Pipeline Specify decisions + cloud setup |

## Deploy the dashboard to Streamlit Community Cloud

1. Go to <https://share.streamlit.io> and sign in with GitHub.
2. **New app** → repo `AlshaikhAbdullah/msbai-dwd-aa13072`, branch `main`,
   main file path `dashboard/app.py`.
3. **Advanced settings → Secrets:** paste your service-account key using the
   format in `dashboard/.streamlit/secrets.toml.example` (the `[gcp_service_account]`
   block). `data.py` picks this up automatically; locally it uses ADC.
4. Deploy. Copy the resulting `*.streamlit.app` URL into the **Live dashboard**
   section above.

> Cloud Run is also wired up (`dashboard/Dockerfile`), but NYU's GCP org policy
> blocks unauthenticated public access to Cloud Run, so Streamlit Community Cloud
> is the public front door.

## Run locally

```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py          # uses Application Default Credentials
python check_correctness.py   # 28/28 correctness gate
```
