# Cloud Run Deployment

## Prerequisites

- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- GCP project with billing enabled
- [Upstash](https://console.upstash.com) account (free tier)

## 1. Upstash Redis

1. Create a free Redis database at [console.upstash.com](https://console.upstash.com)
2. Copy the `rediss://` connection string (double-s = TLS, works with redis-py out of the box)

## 2. Set Environment

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"  # optional, defaults to us-central1
```

## 3. Create Secrets

Run `deploy/setup.sh` or manually create each secret:

```bash
echo -n 'your-x-bearer-token'     | gcloud secrets versions add X_BEARER_TOKEN --data-file=-
echo -n 'your-gemini-api-key'     | gcloud secrets versions add GEMINI_API_KEY --data-file=-
echo -n 'your-discord-bot-token'  | gcloud secrets versions add DISCORD_BOT_TOKEN --data-file=-
echo -n '123456789'               | gcloud secrets versions add DISCORD_CHANNEL_ID --data-file=-
echo -n 'rediss://...@...:6379'   | gcloud secrets versions add REDIS_URL --data-file=-
echo -n 'ghp_...'                 | gcloud secrets versions add GITHUB_TOKEN --data-file=-
echo -n '123456789'               | gcloud secrets versions add GITHUB_DISCORD_CHANNEL_ID --data-file=-
```

## 4. Deploy

```bash
chmod +x deploy/setup.sh
./deploy/setup.sh
```

This enables APIs, builds the image, creates 3 Cloud Run Jobs, and sets up Cloud Scheduler triggers.

## 5. Verify

```bash
# Run each job manually
gcloud run jobs execute botman-pipeline --region=$GCP_REGION --wait
gcloud run jobs execute botman-github   --region=$GCP_REGION --wait
gcloud run jobs execute botman-cleanup  --region=$GCP_REGION --wait

# Check logs
gcloud run jobs executions list --job=botman-pipeline --region=$GCP_REGION
```

## 6. Update (after code changes)

```bash
IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/botman/botman:latest"
gcloud builds submit --tag "${IMAGE}" .
gcloud run jobs update botman-pipeline --image="${IMAGE}" --region=$GCP_REGION
gcloud run jobs update botman-github   --image="${IMAGE}" --region=$GCP_REGION
gcloud run jobs update botman-cleanup  --image="${IMAGE}" --region=$GCP_REGION
```

## 7. Cost

| Service | Free Tier | Usage |
|---------|-----------|-------|
| Cloud Run Jobs | 2M requests/mo | ~1,400 runs/mo |
| Cloud Scheduler | 3 free jobs | 3 jobs |
| Upstash Redis | 10K commands/day | ~500 commands/day |
| Artifact Registry | 500MB | ~100MB |
| Secret Manager | 6 active versions | 7 secrets |

**Estimated cost: $0.00/month** within free tier limits.
