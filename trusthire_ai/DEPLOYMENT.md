# Deploy TrustHire AI to Render

This deployment uses the existing Flask application in `app.py` (`app:app`), existing templates/static assets, SQLite schema, routes and APIs. It does not replace the site.

## Before deploying

- Create a GitHub repository you can connect to Render.
- Ensure `app.py`, `requirements.txt`, `render.yaml`, `runtime.txt`, `Procfile`, `templates/`, `static/`, `database/schema.sql` and the rest of the project are at the repository root.
- Do not commit `.env`, local SQLite files, local uploads, or virtual environments. `.gitignore` excludes these.
- `model/model.pkl` is optional and is not included in this project. The app logs a clear startup error and continues with rule-based analysis if it is absent. If you have a trusted trained model, place it at `model/model.pkl` and commit it; model/pickle files can execute code when loaded.

No hosted AI or other third-party API credentials are required by the current application. Render generates `SECRET_KEY` via `render.yaml`; do not commit a real secret.

## Push the project to GitHub

Open PowerShell in `D:\Hackthon\trusthire_ai`. Create an empty repository on GitHub first, then replace the placeholders below:

```powershell
git init
git add .
git commit -m "Prepare TrustHire AI for Render"
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPOSITORY>.git
git push -u origin main
```

If Git reports that `origin` already exists, update it and push:

```powershell
git remote set-url origin https://github.com/<YOUR-USERNAME>/<YOUR-REPOSITORY>.git
git push -u origin main
```

Review `git status` before pushing. The generated `database/trusthire.sqlite3`, `instance/`, `.env`, `.venv/` and uploaded report files should not be staged. `model/model.pkl` is intentionally not ignored.

## Create the Render service

1. Sign in to Render and select **New → Blueprint**.
2. Connect the GitHub repository you just pushed.
3. If this Flask project is the repository root, select the root `render.yaml`. If it is nested inside a monorepo, set the Render Blueprint/service root directory to the directory containing `app.py`.
4. Review the service definition (`trusthire-ai`, Python runtime, free plan), then create/deploy it.
5. In Render's service settings, verify:
   - `SECRET_KEY` is a generated secret. If necessary, generate a new random value in Render; never use the blank/example value from `.env.example`.
   - `TRUSTHIRE_HTTPS` is `1`.
   - `FLASK_DEBUG` is `0`.
   - Build command: `pip install -r requirements.txt`.
   - Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`.
   - Health check path: `/check`.
6. Wait for the deployment to report **Live**, open the `onrender.com` hostname shown in the Render dashboard, then visit `/check`.
7. Test the landing page, `/check`, signup/login, scan history, report submission, dashboard and `POST /api/analyze`. Check Render logs for startup/import/model errors.

Render provides HTTPS on the deployed service. A generated public URL will have this form:

```text
https://<render-service-name>.onrender.com/check
```

The exact hostname is assigned/displayed by Render after service creation. The project configuration alone does not publish the site; a Render account, connected GitHub repository and successful deployment are required.

## Production settings and data persistence

- `SECRET_KEY` must be set in Render. Without it, the app uses a random local fallback file intended only for local development; Render's filesystem can be replaced.
- The app honors Render's `PORT` and Gunicorn binds to `0.0.0.0`.
- Render's free service filesystem is ephemeral. SQLite users, scans, reports and locally uploaded report images can be lost when an instance restarts, sleeps or redeploys. The app will recreate its schema at startup, but this does not restore prior data.
- For durable production data, migrate SQLite to a managed database and move user uploads to persistent object storage. Those services are not configured in this repository.
- Free services may spin down after inactivity, so the first request can have a cold-start delay. The URL remains hosted while your personal computer is off.

## Local production-command smoke test

The Windows development server can still be tested with:

```powershell
cd D:\Hackthon\trusthire_ai
python app.py
```

It binds to `0.0.0.0` and uses `PORT` if supplied. Render's production command is:

```text
gunicorn app:app --bind 0.0.0.0:$PORT
```

Gunicorn is intended for Render's Linux environment; use `python app.py` for local Windows development.
