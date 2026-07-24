# Production verification checklist

Use this after every Render + Vercel deploy (including preview branches before merging to `main`).

## Backend health

1. Open `https://YOUR-RENDER-URL.onrender.com/health`
2. Confirm JSON response:
   - `"status": "healthy"` (or briefly `"degraded"` during cold start)
   - `"checks.database": true`
   - `"checks.redis": true`
   - `"checks.qdrant": true`

## Frontend API URL

1. Open your site (Vercel production or preview URL)
2. Press **F12 → Network**
3. Trigger login or register
4. Confirm requests go to your Render URL (e.g. `https://ai-chat-platform-irvb.onrender.com`)
5. Confirm **no** requests to `http://localhost:8000`

## Auth and cookies

1. Register a new test account (or log in)
2. Refresh the page — you should stay logged in
3. If login fails, check:
   - `CORS_ORIGINS` on Render matches your exact frontend URL (no trailing slash)
   - `COOKIE_SECURE=true` and `COOKIE_SAMESITE=none` on Render
   - `www` vs non-`www` URL matches `CORS_ORIGINS`

## Chat

1. Create a project
2. Send a message — streaming reply should appear
3. Stop button should abort generation mid-stream

## Document RAG

1. Upload a PDF (max 25 MB)
2. Wait until document status shows **Ready** with chunk count
3. Ask: **"What is this document about?"**
4. Reply should reference document content; Network tab should not show errors

## Environment variables (Render)

Required on `yellobot-api`:

- `ENVIRONMENT=production`
- `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`
- `GROQ_API_KEY`, `HUGGINGFACE_API_KEY`
- `QDRANT_URL`, `QDRANT_API_KEY`
- `EMBEDDING_PROVIDER=huggingface`, `RERANK_ENABLED=false`
- `CORS_ORIGINS=https://yellobot.online,https://www.yellobot.online`
- `COOKIE_SECURE=true`, `COOKIE_SAMESITE=none`
- `METRICS_TOKEN` (if `METRICS_ENABLED=true`)

## Environment variables (Vercel)

Required on frontend project:

- `VITE_API_URL=https://YOUR-RENDER-URL.onrender.com` (no trailing slash)

After changing `VITE_*` variables, **redeploy** — values are baked in at build time.

## Preview branch smoke test (before merging to main)

On the Vercel Preview URL:

- [ ] API calls use Render URL, not localhost
- [ ] Register / login / refresh works
- [ ] Create project + chat stream works
- [ ] Upload PDF → Ready → document question works
- [ ] No CORS errors in browser console

Temporarily add the preview URL to Render `CORS_ORIGINS` for testing, then remove after merge if desired.

## Rollback

If production breaks after merge:

1. Revert the merge commit on `main` in GitHub
2. Vercel and Render will redeploy the previous commit automatically
3. No database rollback needed for code-only changes

## Rotate secrets

If API keys were shared in chat or logs, rotate them in:

- Groq console
- Hugging Face settings
- Qdrant Cloud
- Render `SECRET_KEY` (forces re-login for all users)
