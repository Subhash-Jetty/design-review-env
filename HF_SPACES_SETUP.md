# Hugging Face Spaces Setup & Auto-Deployment Guide

## Prerequisites

1. **Hugging Face Account** — https://huggingface.co
2. **HF API Token** — https://huggingface.co/settings/tokens (with `write` permission)
3. **GitHub Repository** — Already configured with the workflow

## Step 1: Create a Hugging Face Space

Option A: Manual Creation
```
1. Go to https://huggingface.co/new-space
2. Fill in:
   - Space name: design-review-env
   - License: MIT (or prefer)
   - Space SDK: Docker
   - Visibility: Public/Private (your choice)
3. Click Create Space
```

Option B: Via CLI
```bash
huggingface-cli repo create --repo-type=space --space-sdk=docker design-review-env
```

## Step 2: Configure GitHub Secrets

Add these to your GitHub repo (Settings → Secrets and variables → Actions):

| Secret Name | Value |
|---|---|
| `HF_USERNAME` | Your HuggingFace username |
| `HF_TOKEN` | Your HuggingFace API token (with write access) |

Steps:
1. Go to your GitHub repo: https://github.com/Subhash-Jetty/design-review-env/settings/secrets/actions
2. Click "New repository secret"
3. Add `HF_USERNAME` with your HF username
4. Add `HF_TOKEN` with your HF API token
5. Click "Add secret"

## Step 3: Auto-Deployment

The workflow (`.github/workflows/deploy-hf-spaces.yml`) automatically:
- Triggers on every push to `main` branch
- Uploads all files to your HF Space
- Builds and deploys the Docker image
- Updates the Space with latest code

**Manual trigger:**
```
GitHub → Actions → Deploy to HF Spaces → Run workflow
```

## Step 4: Access Your Space

Your Space will be available at:
```
https://huggingface.co/spaces/{your-username}/design-review-env
```

Example:
```
https://huggingface.co/spaces/Subhash-Jetty/design-review-env
```

## Space Configuration Files

### Dockerfile
Located at `server/Dockerfile` — automatically used by HF Spaces SDK:Docker

### Space Badge
To add to README:
```markdown
[![Hugging Face Spaces](https://img.shields.io/badge/🤗-Open%20in%20Spaces-blue.svg)](https://huggingface.co/spaces/YOUR-USERNAME/design-review-env)
```

## Verification

After deployment:

1. **Check Space Status**
   - Navigate to your Space URL
   - Should see the FastAPI web interface or redirect to `/docs`

2. **Test API Endpoints**
   ```bash
   curl https://your-space-url.hf.space/health
   # Expected: {"status": "healthy", "environment": "design_review_env"}
   ```

3. **Check Logs**
   - Go to Space settings → Logs tab
   - View deployment and runtime logs

## Troubleshooting

### Deployment Failed
- Check GitHub Actions logs: Your repo → Actions tab
- Verify HF_TOKEN is valid and has write permission
- Ensure HF_USERNAME is spelled correctly

### Space Not Running
- Check Space settings for resource limits
- Verify Dockerfile is valid: `docker build -t test server/`
- Check Space logs for startup errors

### API Not Responding
- Verify Space is running (green status indicator)
- Check port 8000 is exposed in Dockerfile
- Verify environment variables in Space settings

## Environment Variables in Space

Set in Space settings (Settings → Secrets):

```
OPENAI_API_KEY=sk-...    # For baseline inference (optional)
HF_TOKEN=hf_...          # For HF Hub integration (automatic)
```

## API Endpoints Available

Once deployed, access via:
- **Web Dashboard**: `https://your-space.hf.space/`
- **OpenAPI Docs**: `https://your-space.hf.space/openapi.json`
- **Health Check**: `https://your-space.hf.space/health`
- **Metadata**: `https://your-space.hf.space/metadata`
- **Reset**: `POST https://your-space.hf.space/reset`
- **Step**: `POST https://your-space.hf.space/step`
- **State**: `GET https://your-space.hf.space/state`

## Continuous Updates

Each time you:
1. Push to `main` branch
2. Create a new release
3. Manually trigger the workflow

The Space automatically:
- Pulls latest code from GitHub
- Rebuilds Docker container
- Deploys new version
- Restarts with zero downtime

---

**Questions?** Refer to [Hugging Face Spaces Docs](https://huggingface.co/docs/hub/spaces-overview)
