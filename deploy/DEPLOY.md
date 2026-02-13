# Cloud Run Deployment

## Current Infrastructure

| Resource | Value |
|----------|-------|
| GCP Project | `botman-barbara` |
| Region | `southamerica-west1` (Santiago) |
| VPC | `barbara-vpc` |
| VPC Connector | `barbara-connector` |
| Redis | Memorystore `botman-redis` at `10.249.236.123:6379` |
| Artifact Registry | `botman-repo` |
| Cloud Scheduler | `southamerica-east1` (Sao Paulo) |
| Service Account | `botman-scheduler@botman-barbara.iam.gserviceaccount.com` |

## Cloud Run Jobs

| Job | Command | Schedule (ART) |
|-----|---------|---------------|
| `botman-pipeline` | X/Twitter pipeline | `*/30 9-19 * * *` |
| `botman-github` | GitHub monitor | `*/30 9-19 * * *` |
| `botman-cleanup` | Midnight cleanup | `0 0 * * *` |

## Verify

```bash
# Run each job manually
gcloud run jobs execute botman-pipeline --region=southamerica-west1 --wait
gcloud run jobs execute botman-github   --region=southamerica-west1 --wait
gcloud run jobs execute botman-cleanup  --region=southamerica-west1 --wait

# Check logs
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="botman-github"' \
  --limit=20 --format="value(textPayload)" --project=botman-barbara --freshness=30m
```

## Update (after code changes)

```bash
IMAGE="southamerica-west1-docker.pkg.dev/botman-barbara/botman-repo/botman:latest"
gcloud builds submit --tag "${IMAGE}" --project=botman-barbara .
gcloud run jobs update botman-pipeline --image="${IMAGE}" --region=southamerica-west1
gcloud run jobs update botman-github   --image="${IMAGE}" --region=southamerica-west1
gcloud run jobs update botman-cleanup  --image="${IMAGE}" --region=southamerica-west1
```

## Secrets (Secret Manager)

```bash
# Update a secret value
echo -n 'NEW_VALUE' | gcloud secrets versions add SECRET_NAME --data-file=-

# Current secrets: X_BEARER_TOKEN, GEMINI_API_KEY, DISCORD_BOT_TOKEN,
#                  DISCORD_CHANNEL_ID, REDIS_URL, GITHUB_TOKEN
```

## Architecture

```
Cloud Scheduler (southamerica-east1)
  |-- */30 9-19 * * * ART --> Cloud Run Job: botman-pipeline
  |-- */30 9-19 * * * ART --> Cloud Run Job: botman-github
  |-- 0 0 * * * ART -------> Cloud Run Job: botman-cleanup

Cloud Run Jobs (southamerica-west1)
  --> VPC Connector (barbara-connector)
    --> Memorystore Redis (10.249.236.123:6379)
  --> Discord API (external)
  --> GitHub API (external)
  --> Gemini API (external)
  --> X API (external)
```

## Cost

| Service | Free Tier | Usage |
|---------|-----------|-------|
| Cloud Run Jobs | 2M requests/mo | ~1,400 runs/mo |
| Cloud Scheduler | 3 free jobs | 3 jobs |
| Memorystore Redis | N/A | ~$36/mo (1GB basic) |
| VPC Connector | N/A | ~$7/mo (e2-micro) |
| Artifact Registry | 500MB | ~100MB |
| Secret Manager | 6 active versions | 6 secrets |
