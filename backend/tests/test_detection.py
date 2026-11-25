from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_otp_message_is_high_risk():
    response = client.post("/api/scan/text", json={
        "text": "Send your OTP and UPI PIN immediately to confirm the job.",
        "language": "en",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["risk_label"] == "High Risk"
    assert any(e["rule_id"] == "OTP_PIN" for e in body["evidence"])


def test_genuine_style_message_is_not_verified():
    response = client.post("/api/scan/text", json={
        "text": "Please attend the interview at the office mentioned on the official careers page.",
        "language": "en",
    })
    assert response.status_code == 200
    assert response.json()["risk_label"] == "Verified"


def test_empty_input_is_rejected():
    response = client.post("/api/scan/text", json={"text": "", "language": "en"})
    assert response.status_code == 422


def test_private_url_is_rejected():
    response = client.post("/api/scan/url", json={"url": "http://127.0.0.1/admin"})
    assert response.status_code == 400


def test_enhanced_result_includes_explanation_fields():
    response = client.post("/api/scan/text", json={
        "text": "Pay registration fee and join via WhatsApp today only.",
        "language": "en",
    })
    body = response.json()
    assert "trust_score" in body
    assert "highlighted_suspicious_text" in body
    assert "company_email_check" in body


def test_company_check_does_not_claim_verification():
    response = client.post("/api/company/check", json={
        "company_name": "Example Company",
        "website": "https://example.com",
        "recruiter_email": "hr@gmail.com",
    })
    assert response.status_code == 200
    assert response.json()["verification_status"] == "Not Verified"


def test_safety_chat_returns_guidance():
    response = client.post("/api/chat", json={"question": "Can I share OTP with the recruiter?"})
    assert response.status_code == 200
    assert "OTP" in response.json()["answer"] or "otp" in response.json()["answer"].lower()


def test_model_info_does_not_claim_trained_accuracy():
    response = client.get("/api/model/info")
    body = response.json()
    assert body["model_status"] == "Not trained"
    assert "quality_metrics" in body
