import pytest
from fastapi.testclient import TestClient

from app.core.security import clear_rate_limit_state
from app.core.settings import RuntimeConfigError, validate_runtime_settings
from app.main import app


client = TestClient(app)


def test_ready_health_exposes_sanitized_runtime_status() -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] is True
    assert body["checks"]["config"] is True
    assert "runtime" in body
    assert "api_token" not in body["runtime"]


def test_api_requires_bearer_token_when_token_is_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_rate_limit_state()
    monkeypatch.setenv("MERCH_AGENT_API_TOKEN", "phase11-token")

    unauthenticated = client.get("/api/drafts")
    assert unauthenticated.status_code == 401

    authenticated = client.get(
        "/api/drafts",
        headers={"Authorization": "Bearer phase11-token"},
    )
    assert authenticated.status_code == 200

    clear_rate_limit_state()


def test_write_requests_reject_untrusted_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_rate_limit_state()
    monkeypatch.setenv("MERCH_AGENT_API_TOKEN", "phase11-token")

    response = client.post(
        "/api/workflows/autopilot/run",
        headers={
            "Authorization": "Bearer phase11-token",
            "Origin": "https://evil.example",
        },
        json={
            "count": 1,
            "default_product": "standard_tshirt",
            "explore_marketplaces": True,
            "touch_amazon": False,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Origin is not allowed for write requests."

    clear_rate_limit_state()


def test_delete_preflight_is_allowed_for_frontend_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_rate_limit_state()
    monkeypatch.setenv("MERCH_AGENT_API_TOKEN", "phase11-token")

    response = client.options(
        "/api/drafts/drf_20260605_0002",
        headers={
            "Origin": "http://127.0.0.1:3000",
            "Access-Control-Request-Method": "DELETE",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
    assert "DELETE" in response.headers["access-control-allow-methods"]

    clear_rate_limit_state()


def test_write_requests_are_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_rate_limit_state()
    monkeypatch.setenv("MERCH_AGENT_WRITE_RATE_LIMIT_PER_MINUTE", "1")

    payload = {
        "count": 1,
        "default_product": "standard_tshirt",
        "explore_marketplaces": True,
        "touch_amazon": False,
    }
    first = client.post("/api/workflows/autopilot/run", json=payload)
    second = client.post("/api/workflows/autopilot/run", json=payload)

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["detail"] == "Rate limit exceeded. Try again later."

    clear_rate_limit_state()


def test_production_like_runtime_requires_api_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MERCH_AGENT_ENV", "production")
    monkeypatch.delenv("MERCH_AGENT_API_TOKEN", raising=False)

    with pytest.raises(RuntimeConfigError):
        validate_runtime_settings()
