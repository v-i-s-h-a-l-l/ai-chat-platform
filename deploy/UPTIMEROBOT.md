# Keep the Render API warm with UptimeRobot

YelloBot’s backend runs on Render. Without regular traffic, the first login after a restart can be slow. **UptimeRobot** pings your health endpoint every 5 minutes so the API stays ready and you get alerted if it goes down.

> **One-time setup (~5 minutes).** Do this after Render is deployed. No code changes needed on each deploy.

---

## 1. Create a free account

1. Go to [https://uptimerobot.com](https://uptimerobot.com) and sign up (free tier is enough).
2. Confirm your email if prompted.

---

## 2. Add a monitor

1. Dashboard → **Add New Monitor**.
2. Use these settings:

| Field | Value |
|-------|--------|
| **Monitor Type** | HTTP(s) |
| **Friendly Name** | YelloBot API health |
| **URL** | `https://ai-chat-platform-irvb.onrender.com/health` |
| **Monitoring Interval** | 5 minutes |
| **Monitor Timeout** | 60 seconds |
| **Alert Contacts** | Your email (create one if needed) |

3. Click **Create Monitor**.

Replace the URL if your Render service uses a different hostname (check Render → **yellobot-api** → URL).

---

## 3. Confirm it works

1. In UptimeRobot, status should show **Up** within a few minutes.
2. Open the URL in a browser — you should see JSON like:

```json
{
  "status": "healthy",
  "checks": {
    "database": true,
    "redis": true,
    "qdrant": true
  }
}
```

3. Try login on [https://www.yellobot.online](https://www.yellobot.online) — should respond quickly.

---

## 4. Optional: status page for reviewers

UptimeRobot free tier includes a public status page:

1. **My Settings** → **Public Status Pages** → create a page.
2. Add your **YelloBot API health** monitor.
3. Share the status URL with reviewers if you want them to see uptime at a glance.

---

## What this does and does not do

| Does | Does not |
|------|----------|
| Hits `/health` every 5 minutes to keep Render active | Fix bugs or misconfigured env vars |
| Emails you when the API is down | Guarantee zero downtime (Render/platform outages still happen) |
| Reduces cold-start delays on register/login | Replace Render Starter billing — you still pay for the service |

The frontend also **pre-warms** the API when users open the landing, login, or register pages (`useApiPrewarm`).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Monitor shows **Down** | Check Render logs; open `/health` manually; verify Postgres/Redis/Qdrant env vars |
| Login still slow once | Wait 1–2 monitor cycles after a deploy; try again |
| Wrong URL | Render → **yellobot-api** → copy the `.onrender.com` URL + `/health` |

---

## Why not GitHub Actions?

This repo previously used a scheduled GitHub workflow to ping `/health`. **UptimeRobot is preferred** for production: more reliable scheduling, downtime alerts, and a status page. The GitHub keep-alive workflow has been removed to avoid duplicate pings.
