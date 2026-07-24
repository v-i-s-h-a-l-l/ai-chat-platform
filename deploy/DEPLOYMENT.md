# Deploy YelloBot (Vercel + Railway + Qdrant Cloud)

This guide assumes you have **no prior deployment experience**. Follow the steps in order.  
Estimated time: **45–90 minutes** (mostly waiting for builds).

You will create accounts on 4 services (all have free tiers to start):

| Service | What it hosts |
|---------|----------------|
| [Groq](https://console.groq.com) | AI chat (API key) |
| [Qdrant Cloud](https://cloud.qdrant.io) | Document search vectors |
| [Railway](https://railway.app) | Backend API + database + Redis + file storage |
| [Vercel](https://vercel.com) | React frontend |

Your app repo: `https://github.com/v-i-s-h-a-l-l/ai-chat-platform`

---

## Before you start

1. Push this repo to GitHub (if not already on `main`).
2. Have a Groq API key ready ([console.groq.com](https://console.groq.com)).
3. Use Chrome/Edge — Railway and Vercel login with GitHub.

---

## Part 1 — Qdrant Cloud (5 min)

1. Sign up at [cloud.qdrant.io](https://cloud.qdrant.io).
2. **Create cluster** → choose **Free** tier → pick a region close to you.
3. When ready, copy:
   - **Cluster URL** (looks like `https://xxxxxxxx.us-east-1-0.aws.cloud.qdrant.io`)
   - **API Key** (if shown)
4. Save these in a notes file — you will paste them into Railway later.

---

## Part 2 — Railway backend (30–45 min)

### 2.1 Create project

1. Go to [railway.app](https://railway.app) → **Login with GitHub**.
2. **New Project** → **Deploy from GitHub repo**.
3. Select **`v-i-s-h-a-l-l/ai-chat-platform`**.
4. Railway creates a service — click it → **Settings**:
   - **Root Directory**: leave empty (repo root)
   - **Config file**: `railway.toml` (should auto-detect)
   - **Builder**: Dockerfile → `backend/Dockerfile.production`

### 2.2 Add PostgreSQL

1. In the project, click **+ New** → **Database** → **PostgreSQL**.
2. Railway auto-creates `DATABASE_URL` — you do not need to copy it manually.

### 2.3 Add Redis

1. **+ New** → **Database** → **Redis**.
2. Railway auto-creates `REDIS_URL`.

### 2.4 Add persistent storage (required for document uploads)

1. Click your **API service** (not Postgres/Redis).
2. **Settings** → **Volumes** → **Add Volume**.
3. **Mount path**: `/app/storage`
4. **Size**: 1 GB minimum (increase if you upload many PDFs).

This lets the API and ingestion worker (same container) share uploaded files.

### 2.5 Set environment variables

Click your API service → **Variables** → **Raw Editor** and paste (edit placeholders):

```env
ENVIRONMENT=production
SECRET_KEY=PASTE_RANDOM_STRING_1
GROQ_API_KEY=your_groq_key
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
CORS_ORIGINS=https://placeholder.vercel.app
COOKIE_SECURE=true
COOKIE_SAMESITE=none
RATE_LIMIT_USE_REDIS=true
INGESTION_INLINE_FALLBACK=false
RAG_ENABLED=true
METRICS_ENABLED=true
METRICS_TOKEN=PASTE_RANDOM_STRING_2
DOCUMENT_STORAGE_PATH=/app/storage/documents
INGESTION_MAX_JOBS=2
```

Generate random strings (PowerShell):

```powershell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }) -as [byte[]])
```

Run twice for `SECRET_KEY` and `METRICS_TOKEN`.

**Link plugin variables** (Railway usually does this automatically):

- `DATABASE_URL` → from Postgres service
- `REDIS_URL` → from Redis service

If missing: **Variables** → **Add Reference** → pick Postgres/Redis.

**Important:** Leave `CORS_ORIGINS` as a placeholder for now — update it after Vercel (Part 3).

### 2.6 Deploy

1. **Deploy** (or push to GitHub — Railway redeploys automatically).
2. First deploy takes **10–20 minutes** (installs PyTorch + embedding models).
3. Open **Settings** → **Networking** → **Generate Domain**.
4. Copy your public URL, e.g. `https://yellobot-api-production.up.railway.app`.
5. Test: open `https://YOUR-RAILWAY-URL/health` — should show `"status":"healthy"` (may be `"degraded"` until Qdrant is reachable).

---

## Part 3 — Vercel frontend (10 min)

1. Go to [vercel.com](https://vercel.com) → **Login with GitHub**.
2. **Add New…** → **Project** → import **`ai-chat-platform`**.
3. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. **Environment Variables**:

   | Name | Value |
   |------|-------|
   | `VITE_API_URL` | Your Railway URL from Part 2.6 (no trailing slash) |

5. Click **Deploy**.
6. Copy your Vercel URL, e.g. `https://ai-chat-platform.vercel.app`.

### 3.1 Finish cross-origin auth

Go back to **Railway** → your API service → **Variables**:

- Update `CORS_ORIGINS` to your **exact Vercel URL** (e.g. `https://ai-chat-platform.vercel.app`).
- Railway will redeploy automatically.

---

## Part 4 — Verify everything works

Open your **Vercel URL** in the browser:

1. **Register** a new account → should succeed (no CORS errors in DevTools → Console).
2. **Refresh the page** → you should stay logged in.
3. Create a **project**.
4. **Upload a PDF** → wait until status shows **Ready** (may take 1–3 min on first run while models load).
5. Ask: **"What is this document about?"** → answer should come from the document.

If upload stays on "Processing" forever:

- Railway → **Logs** → check worker errors (Redis, Qdrant, or out-of-memory).
- Ensure **Volume** is mounted at `/app/storage`.
- Ensure `REDIS_URL` and `QDRANT_URL` are set.

---

## Part 5 — Optional: custom domains

| Service | Where |
|---------|--------|
| Frontend | Vercel → Project → Settings → Domains |
| API | Railway → Service → Settings → Networking → Custom Domain |

After adding a custom frontend domain, update Railway `CORS_ORIGINS` to match.

---

## Cost estimate

| Service | Typical cost |
|---------|----------------|
| Vercel Hobby | $0 |
| Railway | ~$5 trial credit, then ~$10–25/mo (API + Postgres + Redis + volume) |
| Qdrant Cloud Free | $0 (1 GB cluster) |
| Groq | Free tier with rate limits |

---

## Troubleshooting

### Login fails / 401 on every request

- `CORS_ORIGINS` must exactly match your Vercel URL.
- `COOKIE_SAMESITE=none` and `COOKIE_SECURE=true` must both be set.

### "I cannot access uploaded documents"

- Check `/health` — `qdrant` and `redis` should be `true`.
- Confirm document shows **Ready** with chunk count.
- Check Railway logs for RAG retrieval lines.

### Build runs out of memory

- Railway → Service → **Settings** → increase memory to **2 GB+**.

### Health check fails on deploy

- First boot runs DB migrations + model download — allow up to 5 minutes.
- `healthcheckTimeout` in `railway.toml` is set to 300 seconds.

---

## Files added for deployment

| File | Purpose |
|------|---------|
| [backend/Dockerfile.production](backend/Dockerfile.production) | Combined API + worker for Railway |
| [backend/scripts/start_production.sh](backend/scripts/start_production.sh) | Migrations + worker + uvicorn |
| [railway.toml](railway.toml) | Railway build/deploy config |
| [frontend/vercel.json](frontend/vercel.json) | SPA routing on Vercel |
| [deploy/env.production.example](deploy/env.production.example) | All production env vars |

Local development is unchanged — still use `docker compose`, `uvicorn`, and `arq` separately.

---

## Need help?

If something fails, grab:

1. Railway **Deploy Logs** (last 50 lines)
2. Browser **Console** errors (F12)
3. Result of `https://YOUR-API/health`

Share those and we can pinpoint the issue.
