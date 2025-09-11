#!/bin/bash

# Deploy script for agent-mesh with Firebase Storage
# Make sure to set your environment variables before running this script

set -e

echo "🚀 Deploying Agent Mesh with Firebase Storage..."

# Check if required environment variables are set
if [ -z "$FIREBASE_SERVICE_ACCOUNT_JSON" ]; then
    echo "❌ Error: FIREBASE_SERVICE_ACCOUNT_JSON environment variable not set"
    echo "Please set it with your Firebase service account JSON"
    exit 1
fi

if [ -z "$FIREBASE_STORAGE_BUCKET" ]; then
    echo "❌ Error: FIREBASE_STORAGE_BUCKET environment variable not set" 
    echo "Please set it with your Firebase storage bucket name (e.g., your-project.appspot.com)"
    exit 1
fi

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: PROJECT_ID environment variable not set"
    echo "Please set it with your Google Cloud project ID"
    exit 1
fi

echo "✅ Environment variables validated"

# Set default region if not specified
REGION=${REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"agent-mesh-python-service"}

echo "📦 Building and deploying to Cloud Run..."

# Build and deploy using gcloud
gcloud run deploy $SERVICE_NAME \
    --source ./service \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID \
    --allow-unauthenticated \
    --set-env-vars FIREBASE_SERVICE_ACCOUNT_JSON="$FIREBASE_SERVICE_ACCOUNT_JSON" \
    --set-env-vars FIREBASE_STORAGE_BUCKET="$FIREBASE_STORAGE_BUCKET" \
    --memory 2Gi \
    --cpu 2 \
    --timeout 60s \
    --max-instances 10

echo "✅ Service deployed successfully!"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format="value(status.url)")

echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "🔧 Don't forget to update your frontend tool configuration with the new URL:"
echo "   Update the URL in lib/tools.ts to: $SERVICE_URL"
echo ""
echo "📋 Next steps:"
echo "   1. Update your frontend configuration"
echo "   2. Test image generation with the coding agent"
echo "   3. Verify images are served from Firebase Storage"
