#!/usr/bin/env bash
# Daily Botman News — Cloud Run deployment
# Prerequisites: gcloud CLI authenticated, project set
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:?Set GCP_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
REPO="botman"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/botman:latest"
SA_NAME="botman-scheduler"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=== 1. Enable APIs ==="
gcloud services enable \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com

echo "=== 2. Create Artifact Registry repo ==="
gcloud artifacts repositories create "${REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="Botman container images" \
  2>/dev/null || echo "Repo already exists"

echo "=== 3. Create secrets ==="
SECRETS=(
  X_BEARER_TOKEN
  GEMINI_API_KEY
  DISCORD_BOT_TOKEN
  DISCORD_CHANNEL_ID
  REDIS_URL
  GITHUB_TOKEN
)
for secret in "${SECRETS[@]}"; do
  gcloud secrets create "${secret}" \
    --replication-policy="automatic" \
    2>/dev/null || echo "Secret ${secret} already exists"
  echo "  -> Set value: echo -n 'VALUE' | \
gcloud secrets versions add ${secret} --data-file=-"
done

echo "=== 4. Build and push image ==="
gcloud builds submit --tag "${IMAGE}" .

echo "=== 5. Create Cloud Run Jobs ==="
SECRET_FLAGS=""
for secret in "${SECRETS[@]}"; do
  SECRET_FLAGS="${SECRET_FLAGS} \
--set-secrets=${secret}=${secret}:latest"
done

ENV_FLAGS="\
--set-env-vars=\
GEMINI_MODEL=gemini-2.0-flash,\
FETCH_INTERVAL_MINUTES=30,\
GITHUB_CHECK_INTERVAL_MINUTES=30,\
TOP_N=1,\
GITHUB_TOP_N=3,\
MIN_ENGAGEMENT=3,\
SCHEDULE_START_HOUR=9,\
SCHEDULE_END_HOUR=20"

# Values with commas must be passed separately to avoid
# --set-env-vars parsing issues.
GH_REPOS_FLAG="--update-env-vars=GITHUB_REPOS=anthropics/claude-code,openai/codex"
X_ACCOUNTS_FLAG="--update-env-vars=X_ACCOUNTS=testingcatalog,ArtificialAnlys,rowancheung,_akhaliq,HuggingPapers,DotCSV,MatthewBerman,DrJimFan,emollick,karpathy,AndrewYNg,danshipper,omarsar0,real_deep_ml,OpenAI,AnthropicAI,GoogleDeepMind,NVIDIAAI,MistralAI,AIatMeta,DeepLearningAI,perplexity_ai,sama,GaryMarcus,lexfridman,Alibaba_Qwen,dwarkesh_sp,hardmaru,aureliengeron,TencentAI_News,OpenAIDevs"

# botman-pipeline
gcloud run jobs create botman-pipeline \
  --image="${IMAGE}" \
  --args="pipeline" \
  --region="${REGION}" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=1 \
  --task-timeout=300s \
  ${SECRET_FLAGS} \
  ${ENV_FLAGS} \
  ${GH_REPOS_FLAG} \
  ${X_ACCOUNTS_FLAG}

# botman-github
gcloud run jobs create botman-github \
  --image="${IMAGE}" \
  --args="github" \
  --region="${REGION}" \
  --memory=512Mi \
  --cpu=1 \
  --max-retries=1 \
  --task-timeout=300s \
  ${SECRET_FLAGS} \
  ${ENV_FLAGS} \
  ${GH_REPOS_FLAG} \
  ${X_ACCOUNTS_FLAG}

# botman-cleanup
gcloud run jobs create botman-cleanup \
  --image="${IMAGE}" \
  --args="cleanup" \
  --region="${REGION}" \
  --memory=256Mi \
  --cpu=1 \
  --max-retries=1 \
  --task-timeout=120s \
  ${SECRET_FLAGS} \
  ${ENV_FLAGS} \
  ${GH_REPOS_FLAG} \
  ${X_ACCOUNTS_FLAG}

echo "=== 6. Create service account ==="
gcloud iam service-accounts create "${SA_NAME}" \
  --display-name="Botman Cloud Scheduler" \
  2>/dev/null || echo "SA already exists"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.invoker"

echo "=== 7. Create Cloud Scheduler triggers ==="
BASE_URI="https://${REGION}-run.googleapis.com/apis"
BASE_URI="${BASE_URI}/run.googleapis.com/v1"
BASE_URI="${BASE_URI}/namespaces/${PROJECT_ID}/jobs"

# Pipeline: every 30 min, 9am-7pm ART
gcloud scheduler jobs create http \
  botman-pipeline-trigger \
  --location="${REGION}" \
  --schedule="*/30 9-19 * * *" \
  --time-zone="America/Argentina/Buenos_Aires" \
  --uri="${BASE_URI}/botman-pipeline:run" \
  --http-method=POST \
  --oauth-service-account-email="${SA_EMAIL}"

# GitHub: every 30 min, 9am-7pm ART
gcloud scheduler jobs create http \
  botman-github-trigger \
  --location="${REGION}" \
  --schedule="*/30 9-19 * * *" \
  --time-zone="America/Argentina/Buenos_Aires" \
  --uri="${BASE_URI}/botman-github:run" \
  --http-method=POST \
  --oauth-service-account-email="${SA_EMAIL}"

# Cleanup: midnight ART
gcloud scheduler jobs create http \
  botman-cleanup-trigger \
  --location="${REGION}" \
  --schedule="0 0 * * *" \
  --time-zone="America/Argentina/Buenos_Aires" \
  --uri="${BASE_URI}/botman-cleanup:run" \
  --http-method=POST \
  --oauth-service-account-email="${SA_EMAIL}"

echo "=== Done ==="
echo "Test with: gcloud run jobs execute \
botman-pipeline --region=${REGION} --wait"
