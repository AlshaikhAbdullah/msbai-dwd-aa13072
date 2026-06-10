
## Cloud Credentials

**Provider:** GCP
**Project ID:** `msbai-dwd-aa13072`
**Service Account:** `claude-agent@msbai-dwd-aa13072.iam.gserviceaccount.com`

### Roles Granted

| Role | Justification |
|------|--------------|
| `roles/bigquery.dataEditor` | Create/write tables in the project's BigQuery datasets |
| `roles/bigquery.jobUser` | Execute BigQuery query jobs (required for reads and writes) |
| `roles/run.developer` | Deploy and manage the Cloud Run visualization website |
| `roles/storage.objectAdmin` | Read/write GCS buckets for build artifacts and static assets |

**Note:** `roles/bigquery.dataViewer` on `nyu-datasets` must be granted separately by the `nyu-datasets` project admin to allow reading `nyu-datasets.weather.m_weather_daily_nyc`.

### Per-User Credentials

Each team member has their own encrypted credentials file: `.cloud-credentials.<email>.enc`.
The encryption passphrase must be set as `GCP_CREDENTIALS_KEY` or `CLOUD_CREDENTIALS_KEY` in Claude Code on the Web environment variables.

Authentication is handled automatically at session start via `.claude/hooks/cloud-auth.sh`.

### Adding a New Team Member

Ask the agent: "Add me to the GCP credentials" — it will run the Add Team Member workflow.

### Escalating Permissions

If a command fails with a 403/access denied error, ask the agent: "Fix my GCP permissions" — it will identify the missing role and instruct the project owner to grant it.
