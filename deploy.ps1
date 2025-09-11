# Deploy script for agent-mesh with Firebase Storage (PowerShell)
# Make sure to set your environment variables before running this script

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying Agent Mesh with Firebase Storage..." -ForegroundColor Green

# Check if required environment variables are set
if (-not $env:FIREBASE_SERVICE_ACCOUNT_JSON) {
    Write-Host "❌ Error: FIREBASE_SERVICE_ACCOUNT_JSON environment variable not set" -ForegroundColor Red
    Write-Host "Please set it with your Firebase service account JSON" -ForegroundColor Red
    exit 1
}

if (-not $env:FIREBASE_STORAGE_BUCKET) {
    Write-Host "❌ Error: FIREBASE_STORAGE_BUCKET environment variable not set" -ForegroundColor Red
    Write-Host "Please set it with your Firebase storage bucket name (e.g., your-project.appspot.com)" -ForegroundColor Red
    exit 1
}

if (-not $env:PROJECT_ID) {
    Write-Host "❌ Error: PROJECT_ID environment variable not set" -ForegroundColor Red
    Write-Host "Please set it with your Google Cloud project ID" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Environment variables validated" -ForegroundColor Green

# Set default region if not specified
$REGION = if ($env:REGION) { $env:REGION } else { "us-central1" }
$SERVICE_NAME = if ($env:SERVICE_NAME) { $env:SERVICE_NAME } else { "agent-mesh-python-service" }

Write-Host "📦 Building and deploying to Cloud Run..." -ForegroundColor Blue

# Build and deploy using gcloud
gcloud run deploy $SERVICE_NAME `
    --source ./service `
    --platform managed `
    --region $REGION `
    --project $env:PROJECT_ID `
    --allow-unauthenticated `
    --set-env-vars "FIREBASE_SERVICE_ACCOUNT_JSON=$env:FIREBASE_SERVICE_ACCOUNT_JSON" `
    --set-env-vars "FIREBASE_STORAGE_BUCKET=$env:FIREBASE_STORAGE_BUCKET" `
    --memory 2Gi `
    --cpu 2 `
    --timeout 60s `
    --max-instances 10

Write-Host "✅ Service deployed successfully!" -ForegroundColor Green

# Get the service URL
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region=$REGION --project=$env:PROJECT_ID --format="value(status.url)"

Write-Host "🌐 Service URL: $SERVICE_URL" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔧 Don't forget to update your frontend tool configuration with the new URL:" -ForegroundColor Yellow
Write-Host "   Update the URL in lib/tools.ts to: $SERVICE_URL" -ForegroundColor Yellow
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Magenta
Write-Host "   1. Update your frontend configuration" -ForegroundColor White
Write-Host "   2. Test image generation with the coding agent" -ForegroundColor White
Write-Host "   3. Verify images are served from Firebase Storage" -ForegroundColor White
