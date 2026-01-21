"""Replay integrity tests.

Tests that the replay engine correctly verifies or detects mismatches.
"""
import pytest
import os
import json
from fastapi.testclient import TestClient

from app.main import app
from app.replay.replay import replay_evaluation


client = TestClient(app)


class TestReplayIntegrity:
    """Test replay verification functionality."""
    
    def setup_method(self):
        self.artifacts_base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "artifacts"
        )
    
    def test_replay_succeeds_for_valid_evaluation(self):
        """Replay of untampered evaluation must succeed."""
        unique_request = {
            "version": "v1",
            "subject": "replay-valid-test",
            "ruleset": "valid-test",
            "payload": {"decision_requested": "ACCEPT", "justification": "Valid replay test", "unique": "replay_valid_001"},
            "injected_time_utc": "2024-07-01T00:00:00Z",
        }
        
        response = client.post("/evaluate", json=unique_request)
        if response.status_code == 409:
            pytest.skip("Evaluation already exists")
        
        assert response.status_code == 200
        eval_id = response.json()["evaluation_id"]
        
        replay_response = client.post(f"/replay/{eval_id}")
        assert replay_response.status_code == 200
        
        replay_result = replay_response.json()
        assert replay_result["replay_ok"] is True
        assert replay_result["mismatches"] == []
    
    def test_replay_fails_for_nonexistent_evaluation(self):
        """Replay of nonexistent evaluation must fail."""
        result, error = replay_evaluation("nonexistent0000")
        
        assert result is None
        assert error is not None
        assert "not found" in error.lower()
    
    def test_replay_detects_decision_change(self):
        """Replay must detect if decision was tampered."""
        unique_request = {
            "version": "v1",
            "subject": "replay-decision-test",
            "ruleset": "decision-test",
            "payload": {"decision_requested": "ACCEPT", "justification": "Decision tamper test", "unique": "decision_tamper_001"},
            "injected_time_utc": "2024-07-02T00:00:00Z",
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
        
        output_data["decision"] = "REJECT"
        
        with open(output_path, "w") as f:
            json.dump(output_data, f)
        
        replay_response = client.post(f"/replay/{eval_id}")
        assert replay_response.status_code == 200
        
        replay_result = replay_response.json()
        assert replay_result["replay_ok"] is False
        assert any("decision" in m.lower() for m in replay_result["mismatches"])


class TestAppendOnlyPolicy:
    """Test that the append-only policy is enforced."""
    
    def test_duplicate_evaluation_rejected(self):
        """Submitting the same evaluation twice must fail on second attempt."""
        unique_request = {
            "version": "v1",
            "subject": "append-only-test",
            "ruleset": "append-test",
            "payload": {"decision_requested": "ACCEPT", "justification": "Append-only policy test", "unique": "append_only_001"},
            "injected_time_utc": "2024-07-03T00:00:00Z",
        }
        
        response1 = client.post("/evaluate", json=unique_request)
        if response1.status_code == 409:
            pass
        else:
            assert response1.status_code == 200
        
        response2 = client.post("/evaluate", json=unique_request)
        
        assert response2.status_code == 409
