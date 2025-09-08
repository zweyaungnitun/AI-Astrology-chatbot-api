# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_public_endpoint():
    """Test that public endpoints work without authentication."""
    response = client.get("/api/auth/public")
    assert response.status_code == 200
    assert response.json()["message"] == "This is a public endpoint accessible to everyone"

def test_protected_endpoint_without_token():
    """Test that protected endpoints reject requests without tokens."""
    response = client.get("/api/auth/test-protected")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers

def test_protected_endpoint_with_invalid_token():
    """Test that protected endpoints reject invalid tokens."""
    response = client.get(
        "/api/auth/test-protected",
        headers={"Authorization": "Bearer invalid-token-here"}
    )
    assert response.status_code == 401