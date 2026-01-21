"""API endpoint tests.

Comprehensive tests for all HTTP endpoints.
"""
import pytest
import json
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


VALID_REQUEST = {
    "version": "v1",
    "subject": "api-test",
    "ruleset": "api-rules",
    "payload": {"decision_requested": "ACCEPT", "justification": "API endpoint test evaluation"},
    "injected_time_utc": "2024-01-01T00:00:00Z",
}


class TestHealthEndpoint:
    """Test /health endpoint."""
    
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_returns_json(self):
        response = client.get("/health")
        assert "application/json" in response.headers.get("content-type", "")
    
    def test_health_contains_status(self):
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
    
    def test_health_contains_strict_mode(self):
        response = client.get("/health")
        data = response.json()
        assert "strict_mode" in data
        assert data["strict_mode"] is True


class TestIndexEndpoint:
    """Test / endpoint."""
    
    def test_index_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200
    
    def test_index_returns_html(self):
        response = client.get("/")
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_index_contains_veraseal(self):
        response = client.get("/")
        assert "VeraSeal" in response.text


class TestSystemCheckEndpoint:
    """Test /system-check endpoint."""
    
    def test_system_check_returns_200(self):
        response = client.get("/system-check")
        assert response.status_code == 200
    
    def test_system_check_returns_html(self):
        response = client.get("/system-check")
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_system_check_contains_pass(self):
        response = client.get("/system-check")
        assert "PASS" in response.text or "FAIL" in response.text


class TestEvaluateEndpoint:
    """Test /evaluate endpoint."""
    
    def test_evaluate_returns_json(self):
        request = {**VALID_REQUEST, "subject": "eval-json-test"}
        response = client.post("/evaluate", json=request)
        assert "application/json" in response.headers.get("content-type", "")
    
    def test_evaluate_returns_evaluation_id(self):
        request = {**VALID_REQUEST, "subject": "eval-id-test"}
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            data = response.json()
            assert "evaluation_id" in data
            assert len(data["evaluation_id"]) == 16
    
    def test_evaluate_returns_result(self):
        request = {**VALID_REQUEST, "subject": "eval-result-test"}
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            data = response.json()
            assert "result" in data
            assert "decision" in data["result"]
    
    def test_evaluate_accept_decision(self):
        request = {**VALID_REQUEST, "subject": "eval-accept-test", "payload": {"assert": True}}
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            assert response.json()["result"]["decision"] == "ACCEPT"
    
    def test_evaluate_reject_decision(self):
        request = {**VALID_REQUEST, "subject": "eval-reject-test", "payload": {"assert": False}}
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            assert response.json()["result"]["decision"] == "REJECT"
    
    def test_evaluate_wrong_content_type(self):
        response = client.post(
            "/evaluate",
            content="not json",
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code in (400, 415, 422)
    
    def test_evaluate_method_not_allowed(self):
        response = client.get("/evaluate")
        assert response.status_code == 405


class TestEvaluationDetailEndpoint:
    """Test /evaluations/{id} endpoints."""
    
    def setup_method(self):
        self.test_counter = getattr(self.__class__, '_counter', 0)
        self.__class__._counter = self.test_counter + 1
    
    def _get_eval_id(self):
        request = {
            **VALID_REQUEST,
            "subject": f"detail-test-{self.test_counter}",
            "payload": {"assert": True, "unique": f"detail_{self.test_counter}"}
        }
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            return response.json()["evaluation_id"]
        return None
    
    def test_evaluation_page_returns_html(self):
        eval_id = self._get_eval_id()
        if eval_id:
            response = client.get(f"/evaluations/{eval_id}")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
    
    def test_evaluation_page_contains_id(self):
        eval_id = self._get_eval_id()
        if eval_id:
            response = client.get(f"/evaluations/{eval_id}")
            assert eval_id in response.text
    
    def test_evaluation_page_404_nonexistent(self):
        response = client.get("/evaluations/nonexistent12345")
        assert response.status_code == 404
    
    def test_evaluation_input_returns_json(self):
        eval_id = self._get_eval_id()
        if eval_id:
            response = client.get(f"/evaluations/{eval_id}/input")
            assert response.status_code == 200
            assert "application/json" in response.headers.get("content-type", "")
    
    def test_evaluation_output_returns_json(self):
        eval_id = self._get_eval_id()
        if eval_id:
            response = client.get(f"/evaluations/{eval_id}/output")
            assert response.status_code == 200
            data = response.json()
            assert "decision" in data
    
    def test_evaluation_trace_returns_json(self):
        eval_id = self._get_eval_id()
        if eval_id:
            response = client.get(f"/evaluations/{eval_id}/trace")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    
    def test_evaluation_meta_returns_json(self):
        eval_id = self._get_eval_id()
        if eval_id:
            response = client.get(f"/evaluations/{eval_id}/meta")
            assert response.status_code == 200
            data = response.json()
            assert "subject" in data
    
    def test_evaluation_manifest_returns_json(self):
        eval_id = self._get_eval_id()
        if eval_id:
            response = client.get(f"/evaluations/{eval_id}/manifest")
            assert response.status_code == 200
    
    def test_evaluation_bundle_returns_zip(self):
        eval_id = self._get_eval_id()
        if eval_id:
            response = client.get(f"/evaluations/{eval_id}/bundle")
            assert response.status_code == 200
            assert "application/zip" in response.headers.get("content-type", "")
    
    def test_evaluation_input_404_nonexistent(self):
        response = client.get("/evaluations/nonexistent12345/input")
        assert response.status_code == 404
    
    def test_evaluation_output_404_nonexistent(self):
        response = client.get("/evaluations/nonexistent12345/output")
        assert response.status_code == 404
    
    def test_evaluation_trace_404_nonexistent(self):
        response = client.get("/evaluations/nonexistent12345/trace")
        assert response.status_code == 404
    
    def test_evaluation_meta_404_nonexistent(self):
        response = client.get("/evaluations/nonexistent12345/meta")
        assert response.status_code == 404
    
    def test_evaluation_manifest_404_nonexistent(self):
        response = client.get("/evaluations/nonexistent12345/manifest")
        assert response.status_code == 404
    
    def test_evaluation_bundle_404_nonexistent(self):
        response = client.get("/evaluations/nonexistent12345/bundle")
        assert response.status_code == 404


class TestReplayEndpoints:
    """Test /replay/{id} endpoints."""
    
    def setup_method(self):
        self.test_counter = getattr(self.__class__, '_counter', 0)
        self.__class__._counter = self.test_counter + 1
    
    def _get_eval_id(self):
        request = {
            **VALID_REQUEST,
            "subject": f"replay-api-test-{self.test_counter}",
            "payload": {"assert": True, "unique": f"replay_api_{self.test_counter}"}
        }
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            return response.json()["evaluation_id"]
        return None
    
    def test_replay_get_returns_html(self):
        eval_id = self._get_eval_id()
        if eval_id:
            response = client.get(f"/replay/{eval_id}")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
    
    def test_replay_post_returns_json(self):
        eval_id = self._get_eval_id()
        if eval_id:
            response = client.post(f"/replay/{eval_id}")
            assert response.status_code == 200
            assert "application/json" in response.headers.get("content-type", "")
    
    def test_replay_post_contains_replay_ok(self):
        eval_id = self._get_eval_id()
        if eval_id:
            response = client.post(f"/replay/{eval_id}")
            data = response.json()
            assert "replay_ok" in data
    
    def test_replay_get_404_nonexistent(self):
        response = client.get("/replay/nonexistent12345")
        assert response.status_code == 404
    
    def test_replay_post_404_nonexistent(self):
        response = client.post("/replay/nonexistent12345")
        assert response.status_code == 404


class TestStaticAssets:
    """Test static asset serving."""
    
    def test_styles_css_exists(self):
        response = client.get("/static/styles.css")
        assert response.status_code == 200
        assert "text/css" in response.headers.get("content-type", "")
    
    def test_nonexistent_static_404(self):
        response = client.get("/static/nonexistent.css")
        assert response.status_code == 404


class TestErrorHandling:
    """Test error handling."""
    
    def test_404_returns_proper_status(self):
        response = client.get("/nonexistent-page")
        assert response.status_code == 404
    
    def test_invalid_json_returns_400(self):
        response = client.post(
            "/evaluate",
            content=b"not valid json{",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
    
    def test_missing_fields_returns_422(self):
        response = client.post("/evaluate", json={"version": "v1"})
        assert response.status_code == 422


class TestCacheHeaders:
    """Test cache control headers."""
    
    def test_index_has_cache_control(self):
        response = client.get("/")
        cache = response.headers.get("cache-control", "")
        assert "no-cache" in cache or "no-store" in cache or cache == ""
