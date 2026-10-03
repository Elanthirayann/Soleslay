# Deployment Guide: Vercel & OnRender (Free)

This project (FastAPI + Jinja2 + SQLAlchemy) is fully configured for zero-cost deployment on **Vercel** and **Render**, along with an automated **GitHub Actions Keep-Awake Ping** to prevent Render free-tier spindowns.

---

## 1. Deploy on OnRender (Free Web Service)

Render provides a free Web Service tier.

### Option A: 1-Click / Blueprint Deploy
The repository includes a [render.yaml](file:///c:/Users/elant/Downloads/soleslay-website-updated%20%286%29/soleslay-website/render.yaml) blueprint file.
1. Push your code to GitHub.
2. Log in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** -> **Blueprint**.
4. Select your GitHub repository. Render reads `render.yaml` and sets up the service automatically.

### Option B: Manual Web Service Setup
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** -> **Web Service**.
3. Connect your GitHub repository.
4. Fill in the service settings:
   - **Name**: `soleslay-website` (or your choice)
   - **Region**: Closest to your users (e.g., Singapore, Frankfurt, Oregon)
   - **Language / Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: **Free**
   - **Health Check Path**: `/health`
5. Click **Create Web Service**. Render will build and deploy your app.
6. Once deployed, copy your service URL (e.g., `https://soleslay-website.onrender.com`).

---

## 2. Deploy on Vercel (Free Serverless)

The project includes [vercel.json](file:///c:/Users/elant/Downloads/soleslay-website-updated%20%286%29/soleslay-website/vercel.json) and [api/index.py](file:///c:/Users/elant/Downloads/soleslay-website-updated%20%286%29/soleslay-website/api/index.py) preconfigured for Vercel's Python runtime.

### Steps:
1. Push your code to GitHub.
2. Go to [Vercel Dashboard](https://vercel.com) and click **Add New...** -> **Project**.
3. Import your GitHub repository.
4. In the project setup:
   - **Framework Preset**: Other
   - **Root Directory**: `./` (leave default)
   - **Build and Output Settings**: Leave as default (Vercel automatically detects `vercel.json` and `requirements.txt`).
5. Click **Deploy**.
6. Vercel bundles the application and serves it worldwide across edge nodes.

> **Note on Vercel Serverless Filesystem**:
> Vercel executes functions in serverless sandboxes with an ephemeral `/tmp` filesystem. The codebase automatically detects Vercel (`VERCEL=1`) and mounts the database safely to `/tmp/soleslay.db`. For persistent admin edits, see the Database section below.

---

## 3. Git Wakeup File for Render Free Plan

Render free services automatically spin down after **15 minutes of inactivity**, causing the next visitor to wait 30–50 seconds for a cold boot.

The repository includes a GitHub Actions workflow:
[.github/workflows/render-keep-awake.yml](file:///c:/Users/elant/Downloads/soleslay-website-updated%20%286%29/soleslay-website/.github/workflows/render-keep-awake.yml)

### How to Activate It:
1. In your GitHub repository, go to **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository variable** (or **New repository secret**).
   - **Name**: `RENDER_APP_URL`
   - **Value**: Your Render live URL (e.g., `https://soleslay-website.onrender.com`)
3. Go to the **Actions** tab in GitHub:
   - Click on **Keep Render Service Awake** on the left.
   - Click **Run workflow** to test it immediately.
4. The workflow will now automatically run **every 14 minutes**, pinging the `/health` endpoint to keep your Render instance warm 24/7.

> **Tip (GitHub Actions 60-Day Inactivity Rule)**:
> GitHub automatically suspends scheduled workflows if a repository has no commits for 60 consecutive days. If you prefer a completely hands-off setup that never pauses:
> - Sign up for free at [cron-job.org](https://cron-job.org) or [UptimeRobot](https://uptimerobot.com).
> - Add a monitor for `https://your-service.onrender.com/health` set to ping every **10 or 14 minutes**.

---

## 4. Database Strategy (SQLite vs Free PostgreSQL)

- **Default (SQLite)**: The app ships with `app/data/soleslay.db` containing all pre-seeded catalog products, categories, and business settings.
- **For Permanent Admin Edits on Cloud**:
  Free cloud hosts (Render free tier and Vercel) have ephemeral or read-only disks. If you plan to add new products or upload photos via the admin panel and want them to persist across redeployments:
  1. Create a free PostgreSQL database on [Supabase](https://supabase.com) or [Neon](https://neon.tech).
  2. Copy the database connection URI.
  3. Set the environment variable in Render and Vercel:
     - `DATABASE_URL`: `postgresql://user:password@host/dbname`
  4. Run migration once to seed products, categories, and business info: `python -m app.migrate`
  5. Create your admin login account: `python -m app.create_admin --username <your_username>`
  The app automatically converts `postgres://` to `postgresql://` and connects seamlessly.
