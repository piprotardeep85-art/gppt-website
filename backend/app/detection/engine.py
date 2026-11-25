from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DetectionRule:
    rule_id: str
    category: str
    severity: str
    keywords: tuple[str, ...]
    explanation: str


RULES = (
    DetectionRule("NO_INTERVIEW", "Suspicious recruitment", "high",
                  ("no interview", "no interview required", "instant hiring", "offer letter without interview",
                   "કોઈ ઈન્ટરવ્યુ નથી", "ઇન્ટરવ્યુ વગર"),
                  "The message claims employment can be offered without a normal interview process."),
    DetectionRule("PAYMENT_ADVANCE", "Payment fraud", "critical",
                  ("registration fee", "security deposit", "training fee", "advance payment",
                   "pay before", "fees", "નોણ્દણી ફી", "જામીન રકમ", "ટ્રેનિંગ ફી"),
                  "The message demands payment before or while applying for employment."),
    DetectionRule("OTP_PIN", "Personal data theft", "critical",
                  ("otp", "upi pin", "atm pin", "bank password", "password", "pin",
                   "ઓટીપી", "યુપીઆઈ પિન"),
                  "The message requests secret authentication or PIN information."),
    DetectionRule("BANK_DETAILS", "Identity impersonation", "high",
                  ("bank account", "credit card", "debit card", "aadhaar", "aadhar",
                   "bank details", "બૅંક ખાત"),
                  "The message requests sensitive financial or identity information."),
    DetectionRule("UNREALISTIC_SALARY", "Suspicious recruitment", "medium",
                  ("earn 50000", "earn 50,000", "earn 1 lakh", "easy money",
                   "guaranteed salary", "no experience", "નોકરી વગર", "આસાનીથી"),
                  "The offer makes unrealistic or guaranteed-income claims."),
    DetectionRule("URGENCY", "Suspicious recruitment", "medium",
                  ("act now", "urgent", "immediately", "today only", "limited seats",
                   "તાત્કાલિક", "આજે જ"),
                  "The message uses pressure or an artificial deadline."),
    DetectionRule("FREE_EMAIL", "Identity impersonation", "medium",
                  ("@gmail.", "@yahoo.", "@outlook.", "@rediff."),
                  "A free email domain is used for supposedly official recruitment."),
    DetectionRule("SUSPICIOUS_LINK", "Malicious links", "high",
                  ("bit.ly", "tinyurl", "t.co", "goo.gl", "freehost", "click here"),
                  "The message contains a shortener or an unusually suspicious link."),
)


def _evidence(text: str, keywords: Iterable[str]) -> list[str]:
    lower = text.lower()
    matches = []
    for keyword in keywords:
        if keyword.lower() in lower:
            start = lower.find(keyword.lower())
            snippet = text[max(0, start - 24):start + len(keyword) + 48].strip()
            if snippet and snippet not in matches:
                matches.append(snippet)
    return matches[:5]


def _salary_realism(text: str) -> dict:
    amounts = re.findall(r"(?:₹|rs\.?|inr\s*)\s*([0-9][0-9,]*(?:\.[0-9]+)?)(?:\s*(lakh|lac|k|thousand|crore))?",
                          text, flags=re.IGNORECASE)
    normalized = []
    for value, unit in amounts:
        number = float(value.replace(",", ""))
        unit = unit.lower()
        if unit in {"lakh", "lac"}:
            number *= 100_000
        elif unit == "crore":
            number *= 10_000_000
        elif unit in {"k", "thousand"}:
            number *= 1_000
        normalized.append(number)

    high_values = [amount for amount in normalized if amount >= 100_000]
    status = "Suspicious" if high_values else "Not Checked"
    return {
        "status": status,
        "monthly_or_period_values": high_values,
        "explanation": "A salary above ₹100,000 needs role and experience context. This check does not prove mismatch.",
    }


def _company_email_check(text: str) -> dict:
    emails = re.findall(r"\b[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", text)
    if not emails:
        return {"status": "Not Provided", "email_domains": [], "explanation": "No email domain was found."}

    free_domains = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "rediffmail.com", "icloud.com"}
    domains = sorted(set(domain.lower() for domain in emails))
    suspicious = [domain for domain in domains if domain in free_domains]
    return {
        "status": "Suspicious" if suspicious else "Official Domain Likely",
        "email_domains": domains,
        "free_email_domains": suspicious,
        "explanation": "A free email domain is weaker evidence for official recruitment, but a one-message check cannot verify a company.",
    }


def analyze_text(text: str, language: str = "en") -> dict:
    findings = []
    categories: set[str] = set()
    severities: set[str] = set()

    for rule in RULES:
        evidence = _evidence(text, rule.keywords)
        if evidence:
            findings.append({
                "rule_id": rule.rule_id,
                "category": rule.category,
                "matched_evidence": evidence,
                "severity": rule.severity,
                "explanation": rule.explanation,
            })
            categories.add(rule.category)
            severities.add(rule.severity)

    if findings:
        risk = "High Risk"
    else:
        risk = "Verified"

    highlights: list[str] = []
    for finding in findings:
        for snippet in finding["matched_evidence"]:
            if snippet not in highlights:
                highlights.append(snippet)

    # This is a transparent rule-risk score, not a calibrated ML probability.
    score = 100
    score -= sum(30 if finding["severity"] == "critical" else 18 if finding["severity"] == "high" else 10
                 for finding in findings)
    score = max(0, score)
    salary_check = _salary_realism(text)
    company_check = _company_email_check(text)

    if not findings:
        if language == "gu":
            explanation = "કોઈ સ્પષ્ટ Warning Sign મળ્યું નથી. આધારિત Scan મુજબ આ સંદેશ Verified જેવો દેખાય છે."
        else:
            explanation = "No configured warning signs were detected. The message is labeled Verified by this rule-based scan."
        limitations = "This MVP label is based only on rule matches. It does not establish official company verification or a guarantee of legitimacy."
    else:
        if language == "gu":
            explanation = "સંદેશમાં ઘણા সতર્ક संकेत મળ્યા છે. પૈસા, OTP અથવા PIN શૅર ન કરો અને સ્વતંત્ર રીતે કંપનીને ચકાસો."
        else:
            explanation = "Potential warning signs were detected. Do not pay money or share OTP/PIN details. Verify the recruiter independently."
        limitations = "This result is based on configurable text rules, not a guarantee of fraud or a numerical probability."

    return {
        "risk_label": risk,
        "evidence": findings,
        "highlighted_suspicious_text": highlights,
        "trust_score": score,
        "trust_score_label": "Rule-risk score; not a calibrated ML probability",
        "salary_realism": salary_check,
        "company_email_check": company_check,
        "categories": sorted(categories),
        "ai_available": False,
        "ai_explanation": None,
        "explanation": explanation,
        "limitations": limitations,
        "verification": {
            "status": "Not Verified",
            "company_name": None,
            "official_website": None,
            "careers_page": None,
            "recruiter_email_domain": None,
            "source_links": [],
            "last_checked": None,
        },
        "recommended_actions": [
            "Do not pay money or share OTP, UPI PIN or passwords.",
            "Verify the company through its independently found official website.",
            "Contact the company using contact details listed on the official website.",
            "Report the offer only with appropriate context and evidence.",
        ],
        "language": language,
    }
