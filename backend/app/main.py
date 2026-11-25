from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from urllib.parse import urlparse

from app.detection.engine import analyze_text
from app.verification.url_scanner import analyze_url

app = FastAPI(
    title="AI JobTrust API",
    version="0.1.0",
    description="Explainable job-scam detection API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TextScanRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    language: str = Field(default="en", pattern="^(en|gu)$")


class UrlScanRequest(BaseModel):
    url: str = Field(min_length=3, max_length=2_048)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)


class CompanyCheckRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=300)
    website: str | None = Field(default=None, max_length=2_048)
    recruiter_email: str | None = Field(default=None, max_length=320)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AI JobTrust"}


@app.post("/api/scan/text")
def scan_text(request: TextScanRequest):
    return analyze_text(request.text, request.language)


@app.post("/api/scan/url")
def scan_url(request: UrlScanRequest):
    try:
        return analyze_url(request.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/company/check")
def check_company(request: CompanyCheckRequest):
    website_status = "Not Provided"
    website_domain = None
    email_domain = None
    evidence = []

    if request.website:
        try:
            result = analyze_url(request.website)
            website_status = "HTTPS" if result["https"] else "HTTP"
            website_domain = result["hostname"]
            evidence.append("Website URL structure and local-network safety checked.")
        except ValueError as exc:
            website_status = "Unsafe or invalid"
            evidence.append(str(exc))

    if request.recruiter_email and "@" in request.recruiter_email:
        email_domain = request.recruiter_email.rsplit("@", 1)[1].lower()
        free_domains = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com", "icloud.com"}
        if email_domain in free_domains:
            evidence.append("Recruiter uses a free email provider.")

    return {
        "company_name": request.company_name,
        "verification_status": "Not Verified",
        "website_status": website_status,
        "website_domain": website_domain,
        "email_domain": email_domain,
        "domain_match": bool(
            website_domain and email_domain and
            (website_domain == email_domain or website_domain.endswith("." + email_domain) or email_domain.endswith("." + website_domain))
        ),
        "evidence": evidence,
        "limitations": "No WHOIS, LinkedIn or official careers-page lookup is configured. HTTPS and domain matching do not prove legitimacy.",
        "last_checked": None,
    }


@app.post("/api/chat")
def safety_chat(request: ChatRequest):
    question = request.question.lower()
    if any(word in question for word in ("fee", "pay", "payment", "deposit")):
        answer = "Do not pay a registration, security or training fee before independently verifying the employer and offer."
    elif any(word in question for word in ("otp", "pin", "password", "bank")):
        answer = "Never share OTP, UPI PIN, ATM PIN, bank password or banking credentials with a recruiter."
    elif any(word in question for word in ("safe", "legitimate", "fake")):
        answer = "A message cannot be confirmed as safe or fake from one input. Check fees, urgency, email domain, official careers page and independently verified contacts."
    else:
        answer = "Verify the company through its independently located official website, avoid advance payments, and do not share sensitive credentials."
    return {"answer": answer, "source": "Rule-based safety guidance", "limitations": "Not a legal or employment-authority determination."}


@app.get("/api/model/info")
def model_info():
    return {
        "detector": "Configurable rule engine",
        "optional_ml_path": "TF-IDF + Logistic Regression",
        "model_status": "Not trained",
        "dataset": "No EMSCAD-labelled dataset is configured in this environment.",
        "explainability": "Exact matched phrases and rule explanations",
        "quality_metrics": "Not reported because no labelled validation dataset is available.",
        "trust_score_status": "Rule-risk score only; not calibrated.",
    }

