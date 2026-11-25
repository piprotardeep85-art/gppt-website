# TrustHire AI

TrustHire AI is a responsive Flask job-post screening site. It combines explainable rule checks with an optional saved scikit-learn TF-IDF + Logistic Regression model and stores accounts, scans and reports in SQLite.

## Project layout

```text
trusthire_ai/
├── app.py
├── Procfile
├── render.yaml
├── runtime.txt
├── requirements.txt
├── .env.example
├── database/
│   ├── schema.sql
│   └── trusthire.sqlite3       # Created on first start; ignored by Git
├── instance/                   # Local session-key fallback; ignored by Git
├── model/
│   ├── model.pkl               # Optional trained model; not included
│   └── train_model.py
├── uploads/                    # Created at startup; report images are local
├── samples/job_posts.json
├── static/
├── templates/
└── tests/
```

## Run locally

Windows PowerShell:

```powershell
cd D:\Hackthon\trusthire_ai
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `SECRET_KEY` in `.env` to a long random value before using accounts. If it is unset, the app creates a stable random local fallback in the ignored `instance` folder. Start the website:

```powershell
python app.py
```

Visit `http://127.0.0.1:5000/check`. The development run block binds to `0.0.0.0` and uses `PORT` when supplied. This allows other devices on the same WiFi to connect.

## Open on a phone over local WiFi

1. Connect the phone and computer to the same WiFi network.
2. On the computer, run `ipconfig` and find the active adapter's **IPv4 Address**, for example `192.168.1.25`.
3. Keep `python app.py` running, then open `http://192.168.1.25:5000/check` in the phone's Chrome browser.
4. If the page cannot connect, allow Python or TCP port `5000` through Windows Defender Firewall for **Private networks**. Do not expose this development server directly to the public internet.

The WiFi address only works on that local network. For a public URL, deploy to Render using the next section.

## Deploy on Render free plan

The repository includes `render.yaml`, `Procfile`, and `runtime.txt` for a Render Blueprint deployment. Both Render configuration files start Gunicorn bound to Render's `PORT`; the Blueprint uses `/check` as its health check.

1. Push this project folder to a GitHub repository (commands below).
2. Sign in at [Render](https://render.com/) and choose **New → Blueprint**.
3. Connect the GitHub repository containing `app.py` at its root and select `render.yaml`.
4. Review the `trusthire-ai` web service and create it. The Blueprint uses `pip install -r requirements.txt` and `gunicorn app:app --bind 0.0.0.0:$PORT`.
5. In the Render service's **Environment** settings, confirm that `SECRET_KEY` has a generated secret. Keep it private.
6. Confirm `TRUSTHIRE_HTTPS=1` and `FLASK_DEBUG=0` are set. Render provides HTTPS for the public service.
7. Wait for the deploy to finish and open the `onrender.com` URL shown in the service dashboard, then add `/check`.

Render's free filesystem is ephemeral. **SQLite data and locally uploaded report images can be lost when the service restarts, redeploys or sleeps.** Use a managed database and persistent object storage for real users. The local session-key file is also ephemeral on Render, so always configure the Render `SECRET_KEY` environment variable.

## Optional ML model

No trained model artifact is bundled. At startup the app attempts to load `model/model.pkl` once. If it is missing, a clear error is logged and rule-based analysis remains available.

To create the optional artifact, provide an appropriately licensed CSV with `text,label` columns and labels `fake` / `genuine` (or `fraudulent` / `legitimate`):

```powershell
python model\train_model.py path\to\licensed_jobs.csv
```

The script writes `model/model.pkl`. `.gitignore` deliberately does not ignore this file, so add it to Git if you want Render to load it. Only load model files you trust: joblib/pickle artifacts can execute code when loaded. The demo examples are not a training dataset; no model accuracy is claimed.

## Dependencies and checks

`requirements.txt` pins the direct runtime and test dependencies to versions installed in the development environment; Gunicorn is pinned for Render's Linux runtime. Pandas is not imported by this project and is intentionally not added.

Run tests:

```powershell
python -m pytest -q
```

## Push to GitHub

Run these commands from `D:\Hackthon\trusthire_ai`, replacing the repository URL with your own:

```powershell
git init
git add .
git commit -m "Prepare TrustHire AI for Render deployment"
git branch -M main
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPOSITORY>.git
git push -u origin main
```

If `origin` already exists, use `git remote set-url origin https://github.com/<YOUR-USERNAME>/<YOUR-REPOSITORY>.git` instead of `git remote add origin`.

## Safety and deployment notes

- The model path, database, schema, uploads, templates and static assets are anchored to the application directory, not the current working directory.
- User passwords are hashed and form posts use CSRF tokens. Use HTTPS for deployed accounts.
- No WHOIS, official-company registry, LinkedIn, web-reputation or domain-age lookup is configured. Company identity is not verified by the current prototype.
- A score is a screening aid, not proof that a job or company is legitimate or fraudulent.
