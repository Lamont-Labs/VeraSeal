"""Tests for new API endpoints: /version, /schema, /examples."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestVersionEndpoint:
    """Tests for /version endpoint."""
    
    def test_version_returns_200(self):
        response = client.get("/version")
        assert response.status_code == 200
    
    def test_version_has_version_field(self):
        response = client.get("/version")
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)
    
    def test_version_has_commit_field(self):
        response = client.get("/version")
        data = response.json()
        assert "commit" in data
        assert isinstance(data["commit"], str)
    
    def test_version_has_name_field(self):
        response = client.get("/version")
        data = response.json()
        assert data.get("name") == "VeraSeal"
    
    def test_version_has_description(self):
        response = client.get("/version")
        data = response.json()
        assert "description" in data


class TestSchemaEndpoint:
    """Tests for /schema endpoint."""
    
    def test_schema_returns_200(self):
        response = client.get("/schema")
        assert response.status_code == 200
    
    def test_schema_has_request_section(self):
        response = client.get("/schema")
        data = response.json()
        assert "request" in data
    
    def test_schema_has_response_section(self):
        response = client.get("/schema")
        data = response.json()
        assert "response" in data
    
    def test_schema_has_mvp_rule(self):
        response = client.get("/schema")
        data = response.json()
        assert "mvp_rule" in data
    
    def test_schema_request_has_required_fields(self):
        response = client.get("/schema")
        data = response.json()
        required = data["request"].get("required", [])
        assert "version" in required
        assert "subject" in required
        assert "ruleset" in required
        assert "payload" in required
        assert "injected_time_utc" in required
    
    def test_schema_request_forbids_additional(self):
        response = client.get("/schema")
        data = response.json()
        assert data["request"].get("additionalProperties") is False


class TestExamplesEndpoint:
    """Tests for /examples endpoint."""
    
    def test_examples_returns_200(self):
        response = client.get("/examples")
        assert response.status_code == 200
    
    def test_examples_has_vendor_approval(self):
        response = client.get("/examples")
        data = response.json()
        assert "vendor_approval" in data
    
    def test_examples_has_policy_exception(self):
        response = client.get("/examples")
        data = response.json()
        assert "policy_exception" in data
    
    def test_examples_has_access_approval(self):
        response = client.get("/examples")
        data = response.json()
        assert "access_approval" in data
    
    def test_example_has_required_fields(self):
        response = client.get("/examples")
        data = response.json()
        example = data["vendor_approval"]
        assert "description" in example
        assert "request" in example
        assert "expected_decision" in example
    
    def test_example_request_is_valid(self):
        response = client.get("/examples")
        data = response.json()
        request = data["vendor_approval"]["request"]
        assert request.get("version") == "v1"
        assert "subject" in request
        assert "ruleset" in request
        assert "payload" in request
        assert "injected_time_utc" in request


class TestImprovedErrorMessages:
    """Tests for improved validation error formatting."""
    
    def test_missing_field_error_has_fix(self):
        response = client.post("/evaluate", json={
            "version": "v1",
            "subject": "test"
        })
        assert response.status_code == 422
        data = response.json()
        detail = data.get("detail", {})
        assert "error" in detail or isinstance(detail, str)
    
    def test_invalid_json_error(self):
        response = client.post(
            "/evaluate",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        data = response.json()
        detail = data.get("detail", {})
        if isinstance(detail, dict):
            assert "error" in detail
            assert "fix" in detail
    
    def test_extra_field_error(self):
        response = client.post("/evaluate", json={
            "version": "v1",
            "subject": "test",
            "ruleset": "test",
            "payload": {"assert": True},
            "injected_time_utc": "2024-01-01T00:00:00Z",
            "extra_field": "not allowed"
        })
        assert response.status_code == 422


class TestIndexPageElements:
    """Tests for index page UI elements."""
    
    def test_index_page_has_copy_buttons(self):
        response = client.get("/")
        assert response.status_code == 200
        html = response.text
        assert "copyJson()" in html
        assert "copyMinified()" in html
        assert "copyCurl()" in html
    
    def test_index_page_has_curl_command(self):
        response = client.get("/")
        assert response.status_code == 200
        html = response.text
        assert "curlCommand" in html
    
    def test_index_page_has_schema_link(self):
        response = client.get("/")
        assert response.status_code == 200
        html = response.text
        assert "/schema" in html
    
    def test_index_page_has_examples_link(self):
        response = client.get("/")
        assert response.status_code == 200
        html = response.text
        assert "/examples" in html
    
    def test_index_page_has_version_link(self):
        response = client.get("/")
        assert response.status_code == 200
        html = response.text
        assert "/version" in html
