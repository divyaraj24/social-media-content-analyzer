# Deploying to Render

## Why Docker

Render's native Python runtime has no way to install system packages, and
this app has one: the `tesseract-ocr` binary that `pytesseract` shells out
to for image uploads. Without it, PDF analysis works but every image upload
fails. So this app deploys as a **Docker web service** — Render builds and
runs the `Dockerfile` at the repo root, which installs Tesseract via `apt`
before installing the Python dependencies.

The `Dockerfile` also swaps Flask's dev server for `gunicorn` (production
WSGI server) and binds to whatever port Render injects via the `$PORT` env
var — both required for a working Render deployment, verified locally with
`docker build` + `docker run -e PORT=8080` before this doc was written.

## 1. Push the repo to GitHub

Render deploys from a connected Git repo (GitHub, GitLab, or Bitbucket) —
there's no plain file upload. This project isn't in git yet:

```bash
git init
git add .
git commit -m "Initial commit"
```

Create a new repo on GitHub (via the web UI, or `gh repo create`), then:

```bash
git remote add origin <your-repo-url>
git branch -M main
git push -u origin main
```

## 2. Create the Render service

**Option A — Blueprint (recommended, matches the committed `render.yaml`):**

1. In the Render dashboard: **New +** → **Blueprint**.
2. Connect the GitHub repo you just pushed.
3. Render reads [render.yaml](../render.yaml) at the repo root and
   pre-fills a Docker web service named `social-media-content-analyzer` on
   the free plan. Click **Apply**.

**Option B — Manual web service:**

1. **New +** → **Web Service** → connect the repo.
2. Render auto-detects the `Dockerfile` and sets **Environment: Docker**.
   No build/start command needed — both are defined in the Dockerfile.
3. Pick a plan (Free is fine to start) and **Create Web Service**.

Either way, Render builds the image, starts the container, and gives you a
URL like `https://social-media-content-analyzer.onrender.com`.

## 3. (Optional) Set `GEMINI_API_KEY` for emoji-aware image extraction

Without this, image uploads fall back to Tesseract OCR — which works, but
can't detect emoji (see [limitations.md](limitations.md)). To enable the
Gemini vision path in production, get a free key at
[aistudio.google.com](https://aistudio.google.com), then:

- **Blueprint flow**: `render.yaml` declares `GEMINI_API_KEY` with
  `sync: false`, so Render prompts for its value during the Blueprint
  **Apply** step without storing it in the repo.
- **Manual service**: service **Settings** → **Environment** → **Add
  Environment Variable** → key `GEMINI_API_KEY`, value your key.

Either way this is optional — the app works without it, just without
emoji detection on images. The free tier's daily limit is low and
per-model (as low as 20 requests/day observed for `gemini-2.5-flash` — see
[limitations.md](limitations.md)); a demo deployment can hit it. If it
does, add a `GEMINI_MODEL` env var (e.g. `gemini-flash-lite-latest`)
alongside `GEMINI_API_KEY` to draw from a separate model's quota instead
of waiting for the daily reset — no redeploy needed beyond the env var
change.

## 4. Verify the deploy

Once it's live:

```bash
curl -s https://<your-service>.onrender.com/            # should be 200
curl -s -X POST -F "file=@post.png" \
  https://<your-service>.onrender.com/api/analyze        # should return JSON analysis
```

If image uploads 500 with a Tesseract-related error, the build didn't use
the Dockerfile — double check the service's **Environment** is set to
**Docker** in the Render dashboard settings, not "Python".

## Notes specific to Render's free plan

- **Cold starts**: free services spin down after ~15 minutes idle and take
  10–30s to wake on the next request. The first request after idle may look
  like it's hanging — that's expected, not a bug.
- **Ephemeral filesystem**: irrelevant here since the app already deletes
  every upload right after processing (see [architecture.md](architecture.md))
  — nothing needs to survive a restart or redeploy.
- **512MB RAM**: fine for this app's workload (Flask + Tesseract on
  single-image requests). Large PDFs or very high-resolution images could
  push close to that limit under concurrent load — the `--workers 2` in the
  Dockerfile's gunicorn command is a conservative default for that reason.

## Redeploying after changes

Render auto-deploys on every push to the connected branch by default. To
change that (e.g. manual deploys only), see the service's **Settings** →
**Build & Deploy** in the Render dashboard.
