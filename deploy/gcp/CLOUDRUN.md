# Push P0 to Cloud Run

1. Create a project at https://console.cloud.google.com/ and enable Cloud Run, Artifact Registry, Cloud Build.
2. Region asia-south1 (Mumbai).
3. Install gcloud: https://cloud.google.com/sdk/docs/install
4. From repo root:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud config set run/region asia-south1
gcloud run deploy janaavaaz --source . --region asia-south1 --allow-unauthenticated --set-env-vars=USE_FIXTURES=true,APP_MODE=demo,GCP_REGION=asia-south1
```

Gemini key: https://aistudio.google.com/apikey
