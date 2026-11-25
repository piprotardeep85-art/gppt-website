import json
from pathlib import Path

import pytest

import app as trusthire


@pytest.fixture()
def client(tmp_path, monkeypatch):
    database = tmp_path / "test.sqlite3"
    monkeypatch.setattr(trusthire, "DATABASE_PATH", database)
    trusthire.initialize_database()
    trusthire.app.config.update(TESTING=True, SECRET_KEY="test-secret")
    return trusthire.app.test_client()


def test_genuine_sample_without_fee_request_is_not_flagged(client):
    result = trusthire.analyze_job({
        "job_text": "We never ask candidates for a registration fee. Apply through the official careers page and attend two interviews."
    })
    assert result["red_flags"] == []
    assert result["label"] == "Genuine"


def test_fee_and_otp_are_critical_warnings():
    result = trusthire.analyze_job({
        "job_text": "Pay a registration fee by UPI and send your OTP to confirm the job."
    })
    assert result["label"] == "Fake"
    assert {flag["type"] for flag in result["red_flags"]} >= {"Payment demand", "Sensitive data request"}


def test_optional_model_probability_affects_base_score(monkeypatch):
    monkeypatch.setattr(trusthire, "predict_fake_probability", lambda _text: (0.9, "test model"))
    result = trusthire.analyze_job({"job_text": "An ordinary role with a standard interview and clear job duties."})
    assert result["score"] == 10
    assert result["label"] == "Fake"
    assert "Uncalibrated" in result["confidence"]


def test_leetspeak_payment_is_detected():
    result = trusthire.analyze_job({"job_text": "Pay a registration f33 to receive the job offer."})
    assert any(flag["type"] == "Payment demand" for flag in result["red_flags"])


def test_spaced_out_payment_is_detected():
    result = trusthire.analyze_job({"job_text": "Pay the r e g i s t r a t i o n f e e to receive your offer."})
    assert any(flag["type"] == "Payment demand" for flag in result["red_flags"])
    assert any("r e g i s t r a t i o n f e e" in flag["matched_text"] for flag in result["red_flags"])


def test_safety_warning_about_otp_is_not_a_credential_request():
    result = trusthire.analyze_job({"job_text": "We will never ask you to send OTP, Aadhaar or bank details."})
    assert not any(flag["type"] == "Sensitive data request" for flag in result["red_flags"])


def test_personal_account_and_no_interview_detected():
    result = trusthire.analyze_job({
        "job_text": "No interview. Receive payments in your personal account for the employer."
    })
    assert any(flag["type"] == "Personal money handling" for flag in result["red_flags"])
    assert any(flag["type"] == "Chat-only hiring" for flag in result["red_flags"])


def test_api_analyze_returns_expected_json(client):
    response = client.post("/api/analyze", json={
        "job_text": "Pay a refundable registration fee to reserve one of our limited seats."
    })
    assert response.status_code == 200
    body = response.get_json()
    assert {"score", "label", "confidence", "red_flags"} <= body.keys()
    assert body["label"] == "Fake"


def test_api_requires_sufficient_job_text(client):
    response = client.post("/api/analyze", json={"job_text": "Too short"})
    assert response.status_code == 400


def test_missing_model_logs_clear_fallback_message(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(trusthire, "MODEL_PATH", str(tmp_path / "missing-model.pkl"))
    monkeypatch.setattr(trusthire, "_model_load_attempted", False)
    monkeypatch.setattr(trusthire, "_loaded_model", None)

    assert trusthire.load_model() is None
    assert "ML model file is missing" in caplog.text
    assert trusthire.load_model() is None
    assert caplog.text.count("ML model file is missing") == 1


def test_login_and_history_pages_load(client):
    assert client.get("/").status_code == 200
    assert client.get("/auth").status_code == 200
    assert client.get("/history").status_code == 200
    assert client.get("/about").status_code == 200
    assert client.get("/report").status_code == 200


def test_report_rejects_javascript_link(client):
    client.get("/report")
    with client.session_transaction() as state:
        csrf = state["_csrf_token"]
    response = client.post("/report", data={
        "csrf_token": csrf, "company_name": "Example",
        "job_link": "javascript:alert(1)", "description": "Suspicious message asked me to pay a fee."
    })
    assert response.status_code == 200
    with trusthire.app.app_context():
        count = trusthire.get_db().execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        assert count == 0


def test_signup_does_not_allow_role_assignment(client):
    client.get("/auth")
    with client.session_transaction() as state:
        csrf = state["_csrf_token"]
    response = client.post("/auth", data={
        "csrf_token": csrf, "action": "signup", "name": "Test User",
        "email": "test@example.com", "password": "long-password",
        "role": "admin",
    })
    assert response.status_code == 302
    with trusthire.app.app_context():
        user = trusthire.get_db().execute("SELECT role FROM users WHERE email = ?", ("test@example.com",)).fetchone()
        assert user["role"] == "user"


def test_login_next_url_does_not_redirect_off_site(client):
    client.get("/auth")
    with client.session_transaction() as state:
        csrf = state["_csrf_token"]
    with trusthire.app.app_context():
        trusthire.get_db().execute(
            "INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",
            ("Example", "redirect@example.com", trusthire.generate_password_hash("password123"),
             "2026-01-01T00:00:00+00:00"),
        )
        trusthire.get_db().commit()
    response = client.post("/auth?next=https://example.com", data={
        "csrf_token": csrf, "action": "login",
        "email": "redirect@example.com", "password": "password123",
    }, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"


def test_five_fake_and_genuine_sample_posts():
    samples_path = Path(trusthire.BASE_DIR) / "samples" / "job_posts.json"
    samples = json.loads(samples_path.read_text(encoding="utf-8"))
    assert len(samples["fake"]) == 5
    assert len(samples["genuine"]) == 5
    assert all(trusthire.analyze_job({"job_text": post})["label"] == "Fake" for post in samples["fake"])
    assert all(trusthire.analyze_job({"job_text": post})["label"] == "Genuine" for post in samples["genuine"])

