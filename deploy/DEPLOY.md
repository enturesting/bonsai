# Deploying Bonsai to DigitalOcean App Platform

Step-by-step runbook for shipping the Bonsai eval harness to DO App Platform.
Artifacts live in `deploy/`: [`Dockerfile`](./Dockerfile) + [`app.yaml`](./app.yaml).

The service runs `uvicorn main:app` on port **8080** and exposes **`/healthz`**
(see `main.py`) as the platform health check.

## Prerequisites

- [`doctl`](https://docs.digitalocean.com/reference/doctl/how-to/install/) installed and authenticated: `doctl auth init`
- The repo pushed to GitHub (App Platform builds from a connected repo), **or**
  use the container-registry path in step 2b.
- Values ready for the four secrets: `MONGODB_URI`, `ANTHROPIC_API_KEY`,
  `VOYAGE_API_KEY`, `GEMINI_API_KEY`.

## 1. Build & smoke-test the image locally

```bash
docker build -f deploy/Dockerfile -t bonsai:local .
docker run --rm -p 8080:8080 -e MOCK_AUT=1 bonsai:local
# in another shell:
curl -fsS http://localhost:8080/healthz   # -> {"status":"ok","service":"bonsai"}
```

`MOCK_AUT=1` gives the deterministic, no-API path — enough to verify the app boots
and serves `/healthz` without any real keys.

## 2a. Create the app from the repo (recommended)

Edit `deploy/app.yaml` → set `github.repo` to your `owner/repo`, then:

```bash
doctl apps create --spec deploy/app.yaml
doctl apps list                      # grab the APP_ID
```

App Platform builds `deploy/Dockerfile` and rolls out one `basic-xxs` instance.
`deploy_on_push: true` means future pushes to `main` redeploy automatically.

## 2b. (Alternative) Push to DO Container Registry

If you'd rather ship a prebuilt image instead of building from the repo:

```bash
doctl registry login
docker tag bonsai:local registry.digitalocean.com/<your-registry>/bonsai:latest
docker push registry.digitalocean.com/<your-registry>/bonsai:latest
```

Then swap the `dockerfile_path`/`github` block in `app.yaml` for an `image:` source
pointing at that registry tag, and `doctl apps create --spec deploy/app.yaml`.

## 3. Set the secrets

Secrets are declared as `type: SECRET` in `app.yaml` with no values (never commit
real keys). Set them after create, then redeploy to pick them up:

```bash
APP_ID=<from step 2>
doctl apps update $APP_ID --spec deploy/app.yaml \
  --env "MONGODB_URI=...,ANTHROPIC_API_KEY=...,VOYAGE_API_KEY=...,GEMINI_API_KEY=..."
```

Or set them in the DO control panel: **Apps → bonsai → Settings → web →
Environment Variables** (mark each **Encrypted**). Leave `MOCK_AUT=0` for the
live AUT path, or `1` to demo without Gemini.

## 4. Get the public link

```bash
doctl apps get $APP_ID --format DefaultIngress --no-header
# -> https://bonsai-xxxxx.ondigitalocean.app
```

## 5. Smoke-test the deployment

```bash
APP_URL=$(doctl apps get $APP_ID --format DefaultIngress --no-header)
curl -fsS "$APP_URL/healthz"          # -> {"status":"ok","service":"bonsai"}
curl -fsS "$APP_URL/" | head          # dashboard renders
```

A green `/healthz` plus a rendering `/` dashboard means the rollout is live.

## Troubleshooting

- **Health check failing / app cycling** — check logs: `doctl apps logs $APP_ID --type run -f`.
  Usually a missing secret (Mongo/Anthropic/Voyage/Gemini) crashing boot.
- **SSE streams cut off** — confirmed `--timeout-keep-alive 75` is in the run command;
  it must outlive DO's load-balancer idle timeout.
- **Build fails on deps** — the image pins `requirements.txt`; rebuild locally
  (step 1) to reproduce before re-pushing.
