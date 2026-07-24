# Merge preview branch to production

Follow these steps after the `quality/hardening-preview` branch passes CI and preview smoke tests.

## Before merge

1. Run local checks:
   ```powershell
   cd backend
   python -m pytest
   cd ..\frontend
   npm run test
   npm run build
   ```

2. Push branch and open PR on GitHub:
   ```powershell
   git push -u origin quality/hardening-preview
   ```

3. Complete preview smoke test using [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) on the Vercel Preview URL.

4. Temporarily add preview URL to Render `CORS_ORIGINS` if testing auth on preview:
   ```
   CORS_ORIGINS=https://yellobot.online,https://www.yellobot.online,https://YOUR-PREVIEW.vercel.app
   ```

## Merge

1. Merge PR `quality/hardening-preview` → `main` on GitHub
2. Wait for Vercel production deploy (frontend)
3. Wait for Render deploy (backend, if changed)

## After merge (5-minute verification)

On live `https://yellobot.online`:

- [ ] `/health` on Render URL is healthy
- [ ] Login + page refresh works
- [ ] Chat streaming works
- [ ] Document upload → Ready → RAG question works
- [ ] Network tab shows Render API URL, not localhost

## Rollback

If anything breaks:

```powershell
git revert -m 1 MERGE_COMMIT_SHA
git push origin main
```

Vercel and Render redeploy automatically. No database rollback needed.

## Post-merge cleanup

- Remove temporary Vercel preview URL from `CORS_ORIGINS` if added
- Confirm `VITE_API_URL` is set in Vercel production environment
- Rotate any secrets that were exposed in chat logs
