#!/usr/bin/env bash
# =============================================================================
# SportSentinel — GCP Setup Script
# Google Solutions Hackathon 2026
# Run this once on Day 1 to provision all cloud infrastructure.
# Compatible with macOS (M2) + gcloud CLI (already authenticated).
# =============================================================================

set -euo pipefail   # Exit on error, unset var, or pipe failure

# =============================================================================
# CONFIGURATION — edit these if needed
# =============================================================================
PROJECT_ID="sportsentinel-2026"
REGION="us-central1"
SA_NAME="sportsentinel-sa"
SA_DISPLAY="SportSentinel Service Account"
BUCKET_NAME="sportsentinel-videos"
BQ_DATASET="sportsentinel"
BQ_TABLE="detection_events"
CREDENTIALS_FILE="credentials.json"

# Derived values (do not edit)
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo ""
echo "============================================================"
echo "  SportSentinel — GCP Bootstrap"
echo "  Project : $PROJECT_ID"
echo "  Region  : $REGION"
echo "============================================================"
echo ""

# =============================================================================
# SECTION 1 — Create & activate the GCP project
# =============================================================================
echo "[1/8] Creating GCP project: $PROJECT_ID ..."

# Create the project (skip if it already exists)
if gcloud projects describe "$PROJECT_ID" &>/dev/null; then
  echo "  → Project $PROJECT_ID already exists, skipping creation."
else
  gcloud projects create "$PROJECT_ID" \
    --name="SportSentinel 2026"
  echo "  → Project created."
fi

# Set this project as the active project for all subsequent gcloud commands
gcloud config set project "$PROJECT_ID"
echo "  → Active project set to $PROJECT_ID."

# Retrieve the billing account linked to your current login and attach it.
# Required before any API or resource can be enabled.
BILLING_ACCOUNT=$(gcloud billing accounts list \
  --filter="open=true" \
  --format="value(name)" \
  --limit=1)

if [[ -z "$BILLING_ACCOUNT" ]]; then
  echo ""
  echo "  ⚠️  No open billing account found."
  echo "  Please link a billing account at:"
  echo "  https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
  echo "  Then re-run this script."
  exit 1
fi

gcloud billing projects link "$PROJECT_ID" \
  --billing-account="$BILLING_ACCOUNT"
echo "  → Billing account $BILLING_ACCOUNT linked."

# =============================================================================
# SECTION 2 — Enable all required Google Cloud APIs
# =============================================================================
echo ""
echo "[2/8] Enabling required APIs (this may take ~2 minutes) ..."

APIS=(
  run.googleapis.com              # Cloud Run — crawler orchestration
  firestore.googleapis.com        # Firestore — asset, alert, graph storage
  storage.googleapis.com          # Cloud Storage — video file storage
  pubsub.googleapis.com           # Pub/Sub — event messaging between services
  bigquery.googleapis.com         # BigQuery — detection event time-series
  aiplatform.googleapis.com       # Vertex AI — anomaly detection
  vision.googleapis.com           # Cloud Vision — OCR on scoreboards/captions
  speech.googleapis.com           # Speech-to-Text — commentary transcription
  generativelanguage.googleapis.com # Gemini — DMCA evidence bundle generation
  cloudscheduler.googleapis.com   # Cloud Scheduler — periodic scan jobs
  iam.googleapis.com              # IAM — service account management
)

gcloud services enable "${APIS[@]}" \
  --project="$PROJECT_ID"

echo "  → All APIs enabled."

# =============================================================================
# SECTION 3 — Create service account & download credentials
# =============================================================================
echo ""
echo "[3/8] Creating service account: $SA_NAME ..."

if gcloud iam service-accounts describe "$SA_EMAIL" \
     --project="$PROJECT_ID" &>/dev/null; then
  echo "  → Service account already exists, skipping creation."
else
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name="$SA_DISPLAY" \
    --project="$PROJECT_ID"
  echo "  → Service account created."
fi

# Grant editor role so the SA can read/write all resources in the project
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/editor" \
  --quiet
echo "  → Editor role granted."

# Download the JSON key to credentials.json in the project root
gcloud iam service-accounts keys create "$CREDENTIALS_FILE" \
  --iam-account="$SA_EMAIL" \
  --project="$PROJECT_ID"
echo "  → Credentials saved to $CREDENTIALS_FILE"
echo "  ⚠️  NEVER commit this file — it is already in .gitignore."

# =============================================================================
# SECTION 4 — Cloud Storage bucket for video files
# =============================================================================
echo ""
echo "[4/8] Creating Cloud Storage bucket: $BUCKET_NAME ..."

if gsutil ls -b "gs://${BUCKET_NAME}" &>/dev/null; then
  echo "  → Bucket already exists, skipping."
else
  # --uniform-bucket-level-access disables per-object ACLs (best practice)
  gcloud storage buckets create "gs://${BUCKET_NAME}" \
    --project="$PROJECT_ID" \
    --location="$REGION" \
    --uniform-bucket-level-access
  echo "  → Bucket gs://${BUCKET_NAME} created."
fi

# Organise the bucket with placeholder objects that establish folder structure
for FOLDER in raw/ variants/ test_corpus/; do
  echo "" | gsutil cp - "gs://${BUCKET_NAME}/${FOLDER}.keep" 2>/dev/null || true
done
echo "  → Folder structure (raw/, variants/, test_corpus/) initialised."

# =============================================================================
# SECTION 5 — Firestore database (Native mode)
# =============================================================================
echo ""
echo "[5/8] Creating Firestore database (Native mode) ..."

# Native mode is required for real-time listeners & document queries.
# Only one default Firestore DB is allowed per project.
if gcloud firestore databases describe \
     --project="$PROJECT_ID" &>/dev/null 2>&1; then
  echo "  → Firestore database already exists, skipping."
else
  gcloud firestore databases create \
    --project="$PROJECT_ID" \
    --location="$REGION" \
    --type=firestore-native
  echo "  → Firestore Native database created in $REGION."
fi

# =============================================================================
# SECTION 6 — BigQuery dataset
# =============================================================================
echo ""
echo "[6/8] Creating BigQuery dataset: $BQ_DATASET ..."

if bq ls --project_id="$PROJECT_ID" "$BQ_DATASET" &>/dev/null; then
  echo "  → Dataset already exists, skipping."
else
  bq --project_id="$PROJECT_ID" mk \
    --dataset \
    --location="$REGION" \
    --description="SportSentinel detection events and analytics" \
    "${PROJECT_ID}:${BQ_DATASET}"
  echo "  → Dataset created."
fi

# =============================================================================
# SECTION 7 — BigQuery table: detection_events
# =============================================================================
echo ""
echo "[7/8] Creating BigQuery table: $BQ_TABLE ..."

# Write the schema to a temp file so bq mk can consume it
SCHEMA_FILE=$(mktemp /tmp/bq_schema_XXXX.json)
cat > "$SCHEMA_FILE" << 'EOF'
[
  {
    "name": "event_id",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Unique identifier for this detection event (UUID)"
  },
  {
    "name": "asset_id",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "ID of the registered source asset that was matched"
  },
  {
    "name": "platform",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Platform where the infringing content was found (e.g. YouTube, Telegram)"
  },
  {
    "name": "source_url",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "URL of the infringing content"
  },
  {
    "name": "region",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Geo-region inferred from platform or CDN metadata"
  },
  {
    "name": "similarity",
    "type": "FLOAT64",
    "mode": "NULLABLE",
    "description": "Cosine similarity score from FAISS vector match (0.0 – 1.0)"
  },
  {
    "name": "detected_at",
    "type": "TIMESTAMP",
    "mode": "REQUIRED",
    "description": "UTC timestamp when the detection event was recorded"
  },
  {
    "name": "transform",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Transformation type detected (e.g. crop, mirror, audio_swap, overlay, compilation)"
  }
]
EOF

if bq show --project_id="$PROJECT_ID" \
     "${BQ_DATASET}.${BQ_TABLE}" &>/dev/null; then
  echo "  → Table already exists, skipping."
else
  bq --project_id="$PROJECT_ID" mk \
    --table \
    --description="Detection events from the SportSentinel matching pipeline" \
    --time_partitioning_field="detected_at" \
    --time_partitioning_type="DAY" \
    "${PROJECT_ID}:${BQ_DATASET}.${BQ_TABLE}" \
    "$SCHEMA_FILE"
  echo "  → Table ${BQ_DATASET}.${BQ_TABLE} created with day-partitioning on detected_at."
fi

rm -f "$SCHEMA_FILE"

# =============================================================================
# SECTION 8 — Write .env.example with all required variables
# =============================================================================
echo ""
echo "[8/8] Writing .env.example ..."

cat > .env.example << EOF
# -------------------------------------------------------
# SportSentinel — environment variables
# Copy to .env and fill in real values. Never commit .env.
# -------------------------------------------------------

GOOGLE_APPLICATION_CREDENTIALS=./credentials.json
GCP_PROJECT_ID=${PROJECT_ID}
GCS_BUCKET=${BUCKET_NAME}
BQ_DATASET=${BQ_DATASET}
BQ_TABLE=${BQ_TABLE}
REGION=${REGION}

# Get from https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your-gemini-api-key
EOF

echo "  → .env.example written."

# =============================================================================
# DONE
# =============================================================================
echo ""
echo "============================================================"
echo "  ✅  SportSentinel GCP setup complete!"
echo ""
echo "  Next steps:"
echo "  1. cp .env.example .env"
echo "  2. Add your GEMINI_API_KEY to .env"
echo "  3. python3 -m venv venv && source venv/bin/activate"
echo "  4. pip install -r requirements.txt"
echo "  5. python main.py"
echo ""
echo "  Project : $PROJECT_ID"
echo "  Bucket  : gs://$BUCKET_NAME"
echo "  BQ      : $PROJECT_ID.$BQ_DATASET.$BQ_TABLE"
echo "  SA      : $SA_EMAIL"
echo "  Creds   : ./$CREDENTIALS_FILE  ← keep secret!"
echo "============================================================"
