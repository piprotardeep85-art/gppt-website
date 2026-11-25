"""TrustHire AI - beginner-friendly Flask job-posting trust checker."""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import urlparse

import joblib
from dotenv import load_dotenv
from flask import (
    Flask, abort, flash, g, jsonify, redirect, render_template, request,
    session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DATABASE_DIR = os.path.join(BASE_DIR, "database")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
MODEL_DIR = os.path.join(BASE_DIR, "model")
SCHEMA_PATH = os.path.join(DATABASE_DIR, "schema.sql")
MODEL_PATH = os.path.join(MODEL_DIR, "model.pkl")
# Render's free filesystem is ephemeral; SQLite data here can reset on restarts or redeploys.
DATABASE_PATH = os.path.join(DATABASE_DIR, "trusthire.sqlite3")
LEGACY_DATABASE_PATH = os.path.join(INSTANCE_DIR, "trusthire.sqlite3")
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

for directory in (INSTANCE_DIR, DATABASE_DIR, UPLOAD_DIR, MODEL_DIR):
    os.makedirs(directory, exist_ok=True)


def get_secret_key() -> str:
    """Prefer a configured key; keep a stable random fallback for local workers."""
    configured_key = os.environ.get("SECRET_KEY") or os.environ.get("TRUSTHIRE_SECRET_KEY")
    if configured_key:
        return configured_key

    local_key_path = os.path.join(INSTANCE_DIR, ".secret_key")
    try:
        with open(local_key_path, "x", encoding="utf-8") as key_file:
            key_file.write(secrets.token_hex(32))
    except FileExistsError:
        pass

    with open(local_key_path, encoding="utf-8") as key_file:
        local_key = key_file.read().strip()
    if not local_key:
        raise RuntimeError(f"Local fallback secret key is empty: {local_key_path}")
    return local_key


app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.config.update(
    SECRET_KEY=get_secret_key(),
    MAX_CONTENT_LENGTH=4 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("TRUSTHIRE_HTTPS", "0") == "1",
)

RULES = [
    {
        "type": "Payment demand",
        "phrases": ("registration fee", "processing fee", "security deposit", "refundable fee",
                    "pay to get the job", "pay before joining", "upi payment", "kit fee",
                    "training fee", "pay a fee", "deposit required", "advance payment"),
        "explanation": "Legitimate employers generally do not require candidates to pay fees or deposits to get hired.",
        "penalty": 36,
    },
    {
        "type": "Sensitive data request",
        "phrases": ("aadhaar", "aadhar", "pan card", " pan ", "bank account", "cancelled cheque",
                    "cancelled check", "otp", "upi pin", "bank password"),
        "explanation": "The post requests sensitive identity, banking or authentication details before a verified hiring process.",
        "penalty": 34,
    },
    {
        "type": "Chat-only hiring",
        "phrases": ("telegram only", "whatsapp only", "telegram interview", "interview on telegram",
                    "interview on whatsapp", "no interview", "without interview"),
        "explanation": "Hiring only through messaging apps or skipping a normal interview can be a warning sign.",
        "penalty": 24,
    },
    {
        "type": "Urgency pressure",
        "phrases": ("limited seats", "apply today only", "within 24 hours", "act immediately",
                    "urgent hiring", "last chance to apply", "only today"),
        "explanation": "Artificial urgency can pressure applicants to act before independently checking the offer.",
        "penalty": 16,
    },
    {
        "type": "Personal money handling",
        "phrases": ("receive payments in your personal account", "use your personal bank account",
                    "transfer money from your account", "receive funds on behalf of the company"),
        "explanation": "A job asking you to receive or transfer company money through a personal account is a serious risk.",
        "penalty": 38,
    },
    {
        "type": "Paid training or placement guarantee",
        "phrases": ("guaranteed placement after a paid training fee", "guaranteed placement after payment",
                    "guaranteed job after training fee", "guaranteed placement",
                    "pay for guaranteed placement", "paid training required"),
        "explanation": "Upfront paid training tied to a guaranteed job or placement deserves careful verification.",
        "penalty": 25,
    },
    {
        "type": "Unrealistic salary claim",
        "phrases": ("earn ₹50000 per week", "earn 50000 per week", "₹50000/week",
                    "50000 per week from home", "earn 1 lakh per month", "₹100000 per month"),
        "explanation": "Very high pay for vague, entry-level or low-effort work may be unrealistic; compare with reputable listings.",
        "penalty": 18,
    },
    {
        "type": "Suspicious or shortened link",
        "phrases": ("bit.ly/", "tinyurl.com/", "t.co/", "goo.gl/", "cutt.ly/", "is.gd/"),
        "explanation": "A shortened link hides its destination. Visit the employer's official site independently instead.",
        "penalty": 18,
    },
]

FREE_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com"}
SHORT_DOMAINS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "cutt.ly", "is.gd"}
_loaded_model = None
_model_load_attempted = False


def get_db() -> sqlite3.Connection:
    """Return one SQLite connection per request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def initialize_database() -> None:
    # Migrate the previous local database once when changing its project-relative location.
    if (DATABASE_PATH == os.path.join(DATABASE_DIR, "trusthire.sqlite3")
            and os.path.isfile(LEGACY_DATABASE_PATH) and not os.path.isfile(DATABASE_PATH)):
        shutil.copy2(LEGACY_DATABASE_PATH, DATABASE_PATH)
    db = sqlite3.connect(DATABASE_PATH)
    with open(SCHEMA_PATH, encoding="utf-8") as schema_file:
        schema = schema_file.read()
    db.executescript(schema)
    columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
    if "language" not in columns:
        db.execute("ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'en'")
    db.commit()
    db.close()


def csrf_token() -> str:
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return session["_csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def enforce_csrf():
    if request.method == "POST" and not request.is_json:
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        expected = session.get("_csrf_token")
        if not supplied or not expected or not secrets.compare_digest(supplied, expected):
            abort(400, description="Your form session expired. Refresh the page and try again.")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access that page.", "info")
            return redirect(url_for("auth", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def current_owner_clause():
    if session.get("user_id"):
        return "user_id = ?", (session["user_id"],)
    guest_id = session.get("guest_id")
    if not guest_id:
        guest_id = secrets.token_urlsafe(24)
        session["guest_id"] = guest_id
    return "guest_id = ? AND user_id IS NULL", (guest_id,)


def normalize_text(text: str) -> str:
    """Normalize common leetspeak and spaced-out letters before rule matching."""
    value = text.lower()
    value = value.replace("f33", "fee").replace("f3e", "fee").replace("0tp", "otp")
    substitutions = {"0": "o", "1": "i", "3": "e", "@": "a", "$": "s"}
    value = re.sub(r"(?<=[a-z])[013@$](?=[a-z])", lambda match: substitutions[match.group(0)], value)
    return value


def phrase_regex(phrase: str) -> re.Pattern:
    """Allow spaces between letters in a keyword without joining adjacent words."""
    words = []
    for word in phrase.lower().split():
        words.append(r"\s*".join(re.escape(character) for character in word))
    return re.compile(r"(?<![a-z0-9])" + r"\s+".join(words) + r"(?![a-z0-9])")


def clause_is_negated(text: str, phrase: str, start: int) -> bool:
    """Avoid flagging a clear denial such as 'we never ask for a registration fee'."""
    preceding = text[max(0, start - 100):start]
    clause = re.split(r"[.!?;\n]", preceding)[-1]
    return bool(re.search(r"\b(?:never|not|no|don't|do not|doesn't|does not|without)\b", clause))


def load_model():
    """Load a user-trained scikit-learn model if present; never fake a prediction."""
    global _loaded_model, _model_load_attempted
    if _model_load_attempted:
        return _loaded_model
    _model_load_attempted = True
    if not os.path.isfile(MODEL_PATH):
        app.logger.error(
            "ML model file is missing at %s. Rule-based analysis remains enabled; "
            "train or provide model/model.pkl to enable ML predictions.",
            MODEL_PATH,
        )
        return None
    try:
        _loaded_model = joblib.load(MODEL_PATH)
    except (OSError, ValueError, EOFError, ImportError, AttributeError):
        app.logger.exception(
            "Could not load ML model from %s. Rule-based analysis remains enabled.",
            MODEL_PATH,
        )
    return _loaded_model


def predict_fake_probability(text: str) -> tuple[float | None, str]:
    """Placeholder integration point for a trained TF-IDF + Logistic Regression pipeline.

    Expected pipeline: predict_proba([text]) and classes_ containing 'fake'.
    Returns None until a valid model artifact has been created.
    """
    model = load_model()
    if model is None:
        return None, "ML model not trained"
    try:
        probabilities = model.predict_proba([text])[0]
        classes = [str(label).lower() for label in model.classes_]
        fake_index = classes.index("fake")
        return float(probabilities[fake_index]), "Trained model loaded"
    except (AttributeError, ValueError, IndexError, TypeError):
        app.logger.exception("Configured model does not provide a compatible predict_proba interface")
        return None, "Model artifact incompatible"


def domain_of(value: str) -> str:
    try:
        parsed = urlparse(value if "://" in value else "https://" + value)
        return (parsed.hostname or "").lower().strip(".")
    except ValueError:
        return ""


def analyze_job(payload: dict) -> dict:
    """Run rules plus an optional trained model and return a transparent score."""
    text = (payload.get("job_text") or "").strip()
    normalized = normalize_text(text)
    red_flags = []

    for rule in RULES:
        for phrase in rule["phrases"]:
            match = phrase_regex(normalize_text(phrase)).search(normalized)
            if not match:
                continue
            start = match.start()
            if clause_is_negated(normalized, match.group(0), start):
                continue
            original_text = text[start:start + len(match.group(0))]
            red_flags.append({
                "type": rule["type"],
                "explanation": rule["explanation"],
                "matched_text": original_text,
                "penalty": rule["penalty"],
            })
            break

    email = (payload.get("recruiter_email") or "").strip()
    email_match = re.search(r"@([A-Za-z0-9.-]+\.[A-Za-z]{2,})$", email)
    if email_match and email_match.group(1).lower() in FREE_EMAIL_DOMAINS:
        red_flags.append({
            "type": "Free recruiter email",
            "explanation": "A free email provider is less reassuring for official company recruitment. Verify the recruiter on the employer's own website.",
            "matched_text": email,
            "penalty": 12,
        })

    website_domain = domain_of(payload.get("website_url", ""))
    if website_domain in SHORT_DOMAINS or any(re.search(re.escape(domain) + r"/", normalized) for domain in SHORT_DOMAINS):
        red_flags.append({
            "type": "Shortened or suspicious website",
            "explanation": "A shortened or suspicious domain can conceal the destination. Do not enter credentials or payment details there.",
            "matched_text": payload.get("website_url") or next(
                (domain for domain in SHORT_DOMAINS if f"{domain}/" in normalized), "shortened link"
            ),
            "penalty": 18,
        })
    if website_domain and "xn--" in website_domain:
        red_flags.append({
            "type": "Lookalike domain pattern",
            "explanation": "The website uses an internationalized domain encoding. Check the exact spelling against the company's independently located official site.",
            "matched_text": website_domain,
            "penalty": 20,
        })
    if payload.get("website_url") and not payload["website_url"].lower().startswith("https://"):
        red_flags.append({
            "type": "Website is not HTTPS",
            "explanation": "The link does not use HTTPS. This is a security concern, although HTTPS alone would not prove legitimacy.",
            "matched_text": payload["website_url"][:180],
            "penalty": 10,
        })
    if email_match and website_domain:
        email_domain = email_match.group(1).lower()
        domains_match = website_domain == email_domain or website_domain.endswith("." + email_domain) or email_domain.endswith("." + website_domain)
        if email_domain not in FREE_EMAIL_DOMAINS and not domains_match:
            red_flags.append({
                "type": "Recruiter domain mismatch",
                "explanation": "The recruiter email domain differs from the supplied website domain. This needs independent confirmation and is not proof of impersonation.",
                "matched_text": f"{email_domain} ≠ {website_domain}",
                "penalty": 18,
            })

    salary_text = f"{payload.get('salary', '')} {text}".lower()
    is_fresher = bool(re.search(r"\b(fresher|entry.level|no experience|0.?1 years?)\b", text.lower()))
    salary_amounts = [int(value.replace(",", "")) for value in re.findall(r"(?:₹|rs\.?\s*)\s*([0-9][0-9,]{3,})", salary_text)]
    if is_fresher and any(amount >= 100_000 for amount in salary_amounts) and not any(
        flag["type"] == "Unrealistic salary claim" for flag in red_flags
    ):
        red_flags.append({
            "type": "Salary realism",
            "explanation": "The stated pay is unusually high for a fresher-level role. Compare the role, pay period and employer details with reliable listings.",
            "matched_text": next((value for value in re.findall(r"(?:₹|rs\.?\s*)\s*[0-9][0-9,]{3,}", salary_text)), payload.get("salary", "")),
            "penalty": 18,
        })

    model_fake_probability, model_status = predict_fake_probability(text)
    if model_fake_probability is None:
        score = 82
        confidence = "Rule-based only — model unavailable"
        score_basis = "Rules only; not a calibrated probability"
    else:
        score = round((1.0 - model_fake_probability) * 100)
        for flag in red_flags:
            score -= flag["penalty"]
        score = max(0, min(100, score))
        confidence = f"Uncalibrated model estimate: {round(max(model_fake_probability, 1-model_fake_probability)*100)}%"
        score_basis = model_status

    # Without a trained model, rule penalties still produce a usable demo score,
    # but the UI explicitly identifies it as rule-based instead of model confidence.
    if model_fake_probability is None:
        score -= sum(flag["penalty"] for flag in red_flags)
        score = max(0, min(100, score))

    if score >= 75:
        label = "Genuine"
    elif score >= 40:
        label = "Suspicious"
    else:
        label = "Fake"

    # Strong critical indicators cap the trust score even if a model says genuine.
    critical_types = {"Payment demand", "Sensitive data request", "Personal money handling"}
    if any(flag["type"] in critical_types for flag in red_flags):
        score = min(score, 35)
        label = "Fake" if score < 40 else "Suspicious"

    for flag in red_flags:
        flag.pop("penalty", None)

    return {
        "score": score,
        "label": label,
        "confidence": confidence,
        "score_basis": score_basis,
        "red_flags": red_flags,
        "highlighted_text": list(dict.fromkeys(flag["matched_text"] for flag in red_flags)),
        "model_fake_probability": model_fake_probability,
        "company_checks": {
            "website_domain": website_domain or None,
            "website_uses_https": (payload.get("website_url") or "").lower().startswith("https://"),
            "recruiter_email_domain": email_match.group(1).lower() if email_match else None,
            "free_email_provider": bool(email_match and email_match.group(1).lower() in FREE_EMAIL_DOMAINS),
            "domain_age": "Not checked",
            "official_company_match": "Not verified",
        },
        "limitations": "A result is a screening aid, not proof that a job or company is legitimate or fraudulent.",
    }


def insert_scan(payload: dict, result: dict) -> int:
    user_id = session.get("user_id")
    guest_id = None
    if user_id is None:
        guest_id = session.setdefault("guest_id", secrets.token_urlsafe(24))
    cursor = get_db().execute(
        """INSERT INTO scans
        (user_id, guest_id, job_title, company_name, website_url, recruiter_email, salary,
         job_text, score, label, confidence, red_flags_json, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id, guest_id, (payload.get("job_title") or "")[:200],
            (payload.get("company_name") or "")[:200], (payload.get("website_url") or "")[:500],
            (payload.get("recruiter_email") or "")[:320], (payload.get("salary") or "")[:100],
            (payload.get("job_text") or "")[:20_000], result["score"], result["label"],
            result["confidence"], json.dumps(result["red_flags"]), datetime.now(timezone.utc).isoformat(),
        ),
    )
    get_db().commit()
    return int(cursor.lastrowid)


@app.get("/")
def index():
    db = get_db()
    stats = {
        "scans": db.execute("SELECT COUNT(*) FROM scans").fetchone()[0],
        "reports": db.execute("SELECT COUNT(*) FROM reports").fetchone()[0],
        "users": db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
    }
    return render_template("index.html", stats=stats)


@app.route("/auth", methods=["GET", "POST"])
def auth():
    if request.method == "POST":
        action = request.form.get("action")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if action == "signup":
            name = request.form.get("name", "").strip()
            if len(name) < 2 or len(password) < 8 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                flash("Enter a name, valid email and password with at least 8 characters.", "error")
            else:
                try:
                    cursor = get_db().execute(
                        "INSERT INTO users(name,email,password_hash,created_at) VALUES (?,?,?,?)",
                        (name[:100], email, generate_password_hash(password), datetime.now(timezone.utc).isoformat()),
                    )
                    get_db().commit()
                    session.clear()
                    session["user_id"] = cursor.lastrowid
                    session["name"] = name[:100]
                    session["_csrf_token"] = secrets.token_urlsafe(32)
                    return redirect(url_for("dashboard"))
                except sqlite3.IntegrityError:
                    flash("An account with that email already exists.", "error")
        else:
            user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["name"] = user["name"]
                session["_csrf_token"] = secrets.token_urlsafe(32)
                next_url = request.args.get("next", "")
                parsed_next = urlparse(next_url)
                if (parsed_next.netloc or not parsed_next.path.startswith("/")
                        or parsed_next.path.startswith("//") or "\\" in next_url):
                    next_url = ""
                return redirect(next_url or url_for("dashboard"))
            flash("Email or password is incorrect.", "error")
    return render_template("auth.html")


@app.post("/guest")
def continue_guest():
    session.setdefault("guest_id", secrets.token_urlsafe(24))
    return redirect(url_for("check_job"))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/check", methods=["GET", "POST"])
def check_job():
    result = None
    scan_id = None
    payload = {}
    if request.method == "POST":
        payload = {
            "job_title": request.form.get("job_title", ""),
            "company_name": request.form.get("company_name", ""),
            "website_url": request.form.get("website_url", ""),
            "recruiter_email": request.form.get("recruiter_email", ""),
            "salary": request.form.get("salary", ""),
            "job_text": request.form.get("job_text", ""),
        }
        if len(payload["job_text"].strip()) < 30:
            flash("Please paste at least 30 characters of job-post text.", "error")
        elif len(payload["job_text"]) > 20_000:
            flash("Job text must be 20,000 characters or fewer.", "error")
        else:
            result = analyze_job(payload)
            scan_id = insert_scan(payload, result)
    return render_template("check.html", result=result, payload=payload, scan_id=scan_id)


@app.get("/dashboard")
def dashboard():
    where, params = current_owner_clause()
    scans = get_db().execute(f"SELECT * FROM scans WHERE {where} ORDER BY created_at DESC", params).fetchall()
    total = len(scans)
    fake_count = sum(row["label"] == "Fake" for row in scans)
    genuine_count = sum(row["label"] == "Genuine" for row in scans)
    avg_score = round(sum(row["score"] for row in scans) / total) if total else 0
    daily = {}
    for row in scans:
        key = row["created_at"][:10]
        daily[key] = daily.get(key, 0) + 1
    keywords = {}
    for row in scans:
        for flag in json.loads(row["red_flags_json"]):
            keywords[flag["type"]] = keywords.get(flag["type"], 0) + 1
    return render_template(
        "dashboard.html", scans=scans[:10], total=total, fake_count=fake_count,
        genuine_count=genuine_count, avg_score=avg_score,
        chart_labels=json.dumps(sorted(daily)), chart_data=json.dumps([daily[key] for key in sorted(daily)]),
        label_data=json.dumps([fake_count, sum(row["label"] == "Suspicious" for row in scans), genuine_count]),
        top_keywords=sorted(keywords.items(), key=lambda item: item[1], reverse=True)[:5],
    )


@app.get("/history")
def history():
    where, params = current_owner_clause()
    rows = get_db().execute(f"SELECT * FROM scans WHERE {where} ORDER BY created_at DESC", params).fetchall()
    return render_template("history.html", scans=rows)


@app.get("/scan/<int:scan_id>")
def view_scan(scan_id):
    where, params = current_owner_clause()
    row = get_db().execute(f"SELECT * FROM scans WHERE id = ? AND {where}", (scan_id, *params)).fetchone()
    if not row:
        abort(404)
    result = {
        "score": row["score"],
        "label": row["label"],
        "confidence": row["confidence"],
        "score_basis": "Saved scan result",
        "red_flags": json.loads(row["red_flags_json"]),
        "highlighted_text": [item.get("matched_text", "") for item in json.loads(row["red_flags_json"])],
        "limitations": "Saved result from a previous screening. It is not proof of legitimacy or fraud.",
        "company_checks": {
            "website_domain": domain_of(row["website_url"]) or None,
            "website_uses_https": row["website_url"].lower().startswith("https://"),
            "recruiter_email_domain": row["recruiter_email"].rsplit("@", 1)[-1] if "@" in row["recruiter_email"] else None,
            "free_email_provider": row["recruiter_email"].rsplit("@", 1)[-1].lower() in FREE_EMAIL_DOMAINS if "@" in row["recruiter_email"] else False,
            "domain_age": "Not checked",
            "official_company_match": "Not verified",
        },
    }
    payload = {
        "job_title": row["job_title"], "company_name": row["company_name"],
        "website_url": row["website_url"], "recruiter_email": row["recruiter_email"],
        "salary": row["salary"], "job_text": row["job_text"],
    }
    return render_template("check.html", result=result, payload=payload, scan_id=scan_id, readonly=True)


@app.route("/history/<int:scan_id>/delete", methods=["POST"])
def delete_scan(scan_id):
    where, params = current_owner_clause()
    get_db().execute(f"DELETE FROM scans WHERE id = ? AND {where}", (scan_id, *params))
    get_db().commit()
    flash("Scan deleted.", "success")
    return redirect(url_for("history"))


@app.route("/report", methods=["GET", "POST"])
def report_fake_job():
    if request.method == "POST":
        company = request.form.get("company_name", "").strip()
        description = request.form.get("description", "").strip()
        job_link = request.form.get("job_link", "").strip()
        screenshot = request.files.get("screenshot")
        saved_name = ""
        if job_link:
            parsed_job_link = urlparse(job_link)
            if parsed_job_link.scheme.lower() not in {"http", "https"} or not parsed_job_link.hostname:
                flash("Job links must use a valid HTTP or HTTPS address.", "error")
                return render_template("report.html")
        if not company or len(description) < 15:
            flash("Company name and a description of at least 15 characters are required.", "error")
        elif screenshot and screenshot.filename:
            extension = Path(screenshot.filename).suffix.lower().lstrip(".")
            if extension not in ALLOWED_IMAGE_EXTENSIONS:
                flash("Screenshots must be PNG, JPG or WebP.", "error")
                return render_template("report.html")
            saved_name = f"{uuid.uuid4().hex}.{extension}"
            screenshot.save(os.path.join(UPLOAD_DIR, secure_filename(saved_name)))
        if company and len(description) >= 15:
            user_id = session.get("user_id")
            guest_id = session.get("guest_id")
            get_db().execute(
                "INSERT INTO reports(user_id,guest_id,company_name,job_link,description,screenshot_name,created_at) VALUES(?,?,?,?,?,?,?)",
                (user_id, guest_id, company[:200], job_link[:500], description[:4000], saved_name,
                 datetime.now(timezone.utc).isoformat()),
            )
            get_db().commit()
            flash("Thanks. Your report was submitted for review.", "success")
            return redirect(url_for("report_fake_job"))
    return render_template("report.html")


@app.get("/about")
def about():
    return render_template("about.html")


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = get_db().execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if request.method == "POST":
        if request.form.get("action") == "language":
            language = request.form.get("language")
            if language not in {"en", "gu"}:
                flash("Choose a supported language.", "error")
            else:
                get_db().execute("UPDATE users SET language = ? WHERE id = ?", (language, user["id"]))
                get_db().commit()
                flash("Language preference saved. Some prototype content is currently English only.", "info")
                return redirect(url_for("profile"))
        elif request.form.get("action") == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            if not check_password_hash(user["password_hash"], current_password):
                flash("Current password did not match.", "error")
            elif len(new_password) < 8:
                flash("New password must contain at least 8 characters.", "error")
            else:
                get_db().execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (generate_password_hash(new_password), user["id"]),
                )
                get_db().commit()
                flash("Password changed.", "success")
                return redirect(url_for("profile"))
        else:
            name = request.form.get("name", "").strip()
            if len(name) < 2:
                flash("Name must have at least 2 characters.", "error")
            else:
                get_db().execute("UPDATE users SET name = ? WHERE id = ?", (name[:100], user["id"]))
                get_db().commit()
                session["name"] = name[:100]
                flash("Profile updated.", "success")
                return redirect(url_for("profile"))
    return render_template("profile.html", user=user)


@app.get("/admin")
@login_required
def admin():
    user = get_db().execute("SELECT role FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if not user or user["role"] != "admin":
        abort(403)
    reports = get_db().execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT 100").fetchall()
    users = get_db().execute("SELECT id,name,email,role,created_at FROM users ORDER BY created_at DESC LIMIT 100").fetchall()
    return render_template("admin.html", reports=reports, users=users)


@app.post("/admin/reports/<int:report_id>/status")
@login_required
def update_report_status(report_id):
    user = get_db().execute("SELECT role FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if not user or user["role"] != "admin":
        abort(403)
    status = request.form.get("status")
    if status not in {"pending", "under_review", "reviewed"}:
        abort(400, description="Choose a valid moderation status.")
    cursor = get_db().execute("UPDATE reports SET status = ? WHERE id = ?", (status, report_id))
    get_db().commit()
    if cursor.rowcount == 0:
        abort(404)
    flash("Report status updated.", "success")
    return redirect(url_for("admin"))


@app.post("/api/analyze")
def api_analyze():
    body = request.get_json(silent=True) or {}
    if not isinstance(body, dict):
        return jsonify({"error": "A JSON object is required"}), 400
    if not isinstance(body.get("job_text"), str) or len(body["job_text"].strip()) < 30:
        return jsonify({"error": "job_text must contain at least 30 characters"}), 400
    if len(body["job_text"]) > 20_000:
        return jsonify({"error": "job_text must be at most 20,000 characters"}), 413
    for field, limit in (("job_title", 200), ("company_name", 200), ("website_url", 500),
                         ("recruiter_email", 320), ("salary", 100)):
        if field in body and (not isinstance(body[field], str) or len(body[field]) > limit):
            return jsonify({"error": f"{field} must be a string of at most {limit} characters"}), 400
    result = analyze_job(body)
    scan_id = insert_scan(body, result)
    return jsonify({"scan_id": scan_id, **result})


@app.get("/api/history")
def api_history():
    where, params = current_owner_clause()
    rows = get_db().execute(f"SELECT id,job_title,company_name,score,label,created_at FROM scans WHERE {where} ORDER BY created_at DESC LIMIT 100", params).fetchall()
    return jsonify([dict(row) for row in rows])


@app.errorhandler(413)
def file_too_large(_error):
    return "Upload too large. Maximum request size is 4 MB.", 413


@app.errorhandler(400)
def bad_request(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": getattr(error, "description", "Bad request")}), 400
    return render_template("error.html", code=400, message=getattr(error, "description", "Bad request")), 400


@app.errorhandler(403)
def forbidden(_error):
    return render_template("error.html", code=403, message="You do not have permission to view this page."), 403


initialize_database()
load_model()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
