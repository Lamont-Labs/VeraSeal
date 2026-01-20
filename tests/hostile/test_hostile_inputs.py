"""Hostile input tests.

Tests that malformed, malicious, or invalid inputs are rejected.
"""
import pytest
import json
import os
import shutil
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.evaluation import EvaluationRequest


client = TestClient(app)


VALID_REQUEST = {
    "version": "v1",
    "subject": "test-subject",
    "ruleset": "test-ruleset",
    "payload": {"assert": True},
    "injected_time_utc": "2024-01-01T00:00:00Z",
}


class TestMissingFields:
    """Test that missing required fields are rejected."""
    
    def test_missing_version(self):
        request = {**VALID_REQUEST}
        del request["version"]
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_missing_subject(self):
        request = {**VALID_REQUEST}
        del request["subject"]
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_missing_ruleset(self):
        request = {**VALID_REQUEST}
        del request["ruleset"]
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_missing_payload(self):
        request = {**VALID_REQUEST}
        del request["payload"]
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_missing_injected_time(self):
        request = {**VALID_REQUEST}
        del request["injected_time_utc"]
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422


class TestExtraFields:
    """Test that extra fields are rejected."""
    
    def test_extra_top_level_field(self):
        request = {**VALID_REQUEST, "extra_field": "should_fail"}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422


class TestInvalidValues:
    """Test that invalid field values are rejected."""
    
    def test_wrong_version(self):
        request = {**VALID_REQUEST, "version": "v2"}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_empty_subject(self):
        request = {**VALID_REQUEST, "subject": ""}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_subject_too_long(self):
        request = {**VALID_REQUEST, "subject": "x" * 129}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_empty_ruleset(self):
        request = {**VALID_REQUEST, "ruleset": ""}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_ruleset_too_long(self):
        request = {**VALID_REQUEST, "ruleset": "x" * 129}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_invalid_time_format(self):
        request = {**VALID_REQUEST, "injected_time_utc": "not-a-time"}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422


class TestPayloadValidation:
    """Test payload type validation."""
    
    def test_payload_with_nan(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="test",
                payload={"value": float("nan")},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_payload_with_infinity(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="test",
                payload={"value": float("inf")},
                injected_time_utc="2024-01-01T00:00:00Z",
            )


class TestReplayMismatch:
    """Test replay mismatch detection."""
    
    def setup_method(self):
        self.artifacts_base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "artifacts"
        )
    
    def test_replay_detects_tampered_output(self):
        unique_request = {
            "version": "v1",
            "subject": "replay-tamper-test",
            "ruleset": "tamper-test",
            "payload": {"assert": True, "test_id": "tamper_test_001"},
            "injected_time_utc": "2024-06-15T12:00:00Z",
        }
        
        response = client.post("/evaluate", json=unique_request)
        if response.status_code == 409:
            pytest.skip("Evaluation already exists")
        
        assert response.status_code == 200
        eval_id = response.json()["evaluation_id"]
        
        output_path = os.path.join(
            self.artifacts_base, "evaluations", eval_id, "output.json"
        )
        
        with open(output_path, "r") as f:
            output_data = json.load(f)
        
        output_data["output_sha256"] = "0" * 64
        
        with open(output_path, "w") as f:
            json.dump(output_data, f)
        
        replay_response = client.post(f"/replay/{eval_id}")
        assert replay_response.status_code == 200
        replay_result = replay_response.json()
        
        assert replay_result["replay_ok"] is False
        assert len(replay_result["mismatches"]) > 0


class TestNonUtf8:
    """Test that non-UTF8 content is rejected."""
    
    def test_non_utf8_body(self):
        response = client.post(
            "/evaluate",
            content=b"\xff\xfe",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in (400, 422)
