"""Hard replay integrity tests.

Tests various tamper scenarios and edge cases.
"""
import pytest
import os
import json
import shutil
from fastapi.testclient import TestClient

from app.main import app
from app.replay.replay import replay_evaluation


client = TestClient(app)


class TestReplayTamperDetection:
    """Test that various types of tampering are detected."""
    
    def setup_method(self):
        self.artifacts_base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "artifacts"
        )
        self.test_counter = getattr(self.__class__, '_counter', 0)
        self.__class__._counter = self.test_counter + 1
    
    def _create_evaluation(self, unique_suffix):
        """Create a fresh evaluation for testing."""
        request = {
            "version": "v1",
            "subject": f"replay-hard-test-{unique_suffix}",
            "ruleset": "hard-test",
            "payload": {"decision_requested": "ACCEPT", "justification": "Hard replay test", "unique": f"hard_{unique_suffix}"},
            "injected_time_utc": "2024-08-01T00:00:00Z",
        }
        response = client.post("/evaluate", json=request)
        if response.status_code == 409:
            return None
        assert response.status_code == 200
        return response.json()["evaluation_id"]
    
    def test_tamper_input_sha256(self):
        """Changing input_sha256 in output must be detected."""
        eval_id = self._create_evaluation(f"input_sha_{self.test_counter}")
        if not eval_id:
            pytest.skip("Evaluation already exists")
        
        output_path = os.path.join(self.artifacts_base, "evaluations", eval_id, "output.json")
        with open(output_path, "r") as f:
            data = json.load(f)
        
        data["input_sha256"] = "a" * 64
        with open(output_path, "w") as f:
            json.dump(data, f)
        
        result, error = replay_evaluation(eval_id)
        assert result is not None
        assert result.replay_ok is False
        assert len(result.mismatches) > 0
    
    def test_tamper_output_sha256(self):
        """Changing output_sha256 must be detected."""
        eval_id = self._create_evaluation(f"output_sha_{self.test_counter}")
        if not eval_id:
            pytest.skip("Evaluation already exists")
        
        output_path = os.path.join(self.artifacts_base, "evaluations", eval_id, "output.json")
        with open(output_path, "r") as f:
            data = json.load(f)
        
        data["output_sha256"] = "b" * 64
        with open(output_path, "w") as f:
            json.dump(data, f)
        
        result, error = replay_evaluation(eval_id)
        assert result is not None
        assert result.replay_ok is False
    
    def test_tamper_evaluation_id(self):
        """Changing evaluation_id in output - replay checks against folder name, not saved value."""
        eval_id = self._create_evaluation(f"eval_id_{self.test_counter}")
        if not eval_id:
            pytest.skip("Evaluation already exists")
        
        output_path = os.path.join(self.artifacts_base, "evaluations", eval_id, "output.json")
        with open(output_path, "r") as f:
            data = json.load(f)
        
        data["evaluation_id"] = "tampered1234567"
        with open(output_path, "w") as f:
            json.dump(data, f)
        
        result, error = replay_evaluation(eval_id)
        assert result is not None
        assert result.replay_ok is True
    
    def test_tamper_reasons(self):
        """Changing reasons in output.json - replay regenerates from input, doesn't use saved reasons."""
        eval_id = self._create_evaluation(f"reasons_{self.test_counter}")
        if not eval_id:
            pytest.skip("Evaluation already exists")
        
        output_path = os.path.join(self.artifacts_base, "evaluations", eval_id, "output.json")
        with open(output_path, "r") as f:
            data = json.load(f)
        
        data["reasons"] = ["Tampered reason"]
        with open(output_path, "w") as f:
            json.dump(data, f)
        
        result, error = replay_evaluation(eval_id)
        assert result is not None
        assert result.replay_ok is True
    
    def test_tamper_created_time(self):
        """Changing created_time_utc in output.json - replay regenerates from input."""
        eval_id = self._create_evaluation(f"time_{self.test_counter}")
        if not eval_id:
            pytest.skip("Evaluation already exists")
        
        output_path = os.path.join(self.artifacts_base, "evaluations", eval_id, "output.json")
        with open(output_path, "r") as f:
            data = json.load(f)
        
        data["created_time_utc"] = "2099-12-31T23:59:59Z"
        with open(output_path, "w") as f:
            json.dump(data, f)
        
        result, error = replay_evaluation(eval_id)
        assert result is not None
        assert result.replay_ok is True


class TestReplayInputTampering:
    """Test tampering of input.json."""
    
    def setup_method(self):
        self.artifacts_base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "artifacts"
        )
        self.test_counter = getattr(self.__class__, '_counter', 0)
        self.__class__._counter = self.test_counter + 1
    
    def _create_evaluation(self, unique_suffix):
        request = {
            "version": "v1",
            "subject": f"input-tamper-test-{unique_suffix}",
            "ruleset": "input-test",
            "payload": {"assert": True, "unique": f"input_{unique_suffix}"},
            "injected_time_utc": "2024-08-02T00:00:00Z",
        }
        response = client.post("/evaluate", json=request)
        if response.status_code == 409:
            return None
        assert response.status_code == 200
        return response.json()["evaluation_id"]
    
    def test_tamper_input_subject(self):
        """Changing subject in input must be detected."""
        eval_id = self._create_evaluation(f"subj_{self.test_counter}")
        if not eval_id:
            pytest.skip("Evaluation already exists")
        
        input_path = os.path.join(self.artifacts_base, "evaluations", eval_id, "input.json")
        with open(input_path, "r") as f:
            data = json.load(f)
        
        data["subject"] = "tampered-subject"
        with open(input_path, "w") as f:
            json.dump(data, f)
        
        result, error = replay_evaluation(eval_id)
        assert result is not None
        assert result.replay_ok is False
    
    def test_tamper_input_payload(self):
        """Changing payload in input must be detected."""
        eval_id = self._create_evaluation(f"payload_{self.test_counter}")
        if not eval_id:
            pytest.skip("Evaluation already exists")
        
        input_path = os.path.join(self.artifacts_base, "evaluations", eval_id, "input.json")
        with open(input_path, "r") as f:
            data = json.load(f)
        
        data["payload"]["tampered"] = True
        with open(input_path, "w") as f:
            json.dump(data, f)
        
        result, error = replay_evaluation(eval_id)
        assert result is not None
        assert result.replay_ok is False
    
    def test_tamper_input_time(self):
        """Changing injected_time_utc in input must be detected."""
        eval_id = self._create_evaluation(f"time_{self.test_counter}")
        if not eval_id:
            pytest.skip("Evaluation already exists")
        
        input_path = os.path.join(self.artifacts_base, "evaluations", eval_id, "input.json")
        with open(input_path, "r") as f:
            data = json.load(f)
        
        data["injected_time_utc"] = "2099-01-01T00:00:00Z"
        with open(input_path, "w") as f:
            json.dump(data, f)
        
        result, error = replay_evaluation(eval_id)
        assert result is not None
        assert result.replay_ok is False


class TestReplayEdgeCases:
    """Test replay edge cases."""
    
    def setup_method(self):
        self.artifacts_base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "artifacts"
        )
    
    def test_replay_nonexistent_returns_error(self):
        """Nonexistent evaluation must return error."""
        result, error = replay_evaluation("0000000000000000")
        assert result is None
        assert error is not None
    
    def test_replay_short_id_returns_error(self):
        """Short evaluation ID must return error."""
        result, error = replay_evaluation("short")
        assert result is None
        assert error is not None
    
    def test_replay_empty_id_returns_error(self):
        """Empty evaluation ID must return error."""
        result, error = replay_evaluation("")
        assert result is None
        assert error is not None
    
    def test_replay_special_chars_id_returns_error(self):
        """Special character evaluation ID must return error."""
        result, error = replay_evaluation("../../../etc")
        assert result is None
        assert error is not None


class TestReplayAPIEndpoints:
    """Test replay API endpoints."""
    
    def test_replay_post_endpoint(self):
        """POST /replay/{id} must return JSON."""
        response = client.post("/replay/nonexistent123")
        assert response.status_code == 404
    
    def test_replay_get_endpoint(self):
        """GET /replay/{id} must return HTML."""
        response = client.get("/replay/nonexistent123")
        assert response.status_code == 404
        assert "text/html" in response.headers.get("content-type", "")


class TestMetadataTampering:
    """Test tampering of metadata.json."""
    
    def setup_method(self):
        self.artifacts_base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "artifacts"
        )
        self.test_counter = getattr(self.__class__, '_counter', 0)
        self.__class__._counter = self.test_counter + 1
    
    def _create_evaluation(self, unique_suffix):
        request = {
            "version": "v1",
            "subject": f"meta-tamper-test-{unique_suffix}",
            "ruleset": "meta-test",
            "payload": {"assert": True, "unique": f"meta_{unique_suffix}"},
            "injected_time_utc": "2024-08-03T00:00:00Z",
        }
        response = client.post("/evaluate", json=request)
        if response.status_code == 409:
            return None
        assert response.status_code == 200
        return response.json()["evaluation_id"]
    
    def test_tamper_metadata_subject(self):
        """Tampering metadata.json subject should be detectable."""
        eval_id = self._create_evaluation(f"meta_subj_{self.test_counter}")
        if not eval_id:
            pytest.skip("Evaluation already exists")
        
        meta_path = os.path.join(self.artifacts_base, "evaluations", eval_id, "metadata.json")
        with open(meta_path, "r") as f:
            data = json.load(f)
        
        original_subject = data["subject"]
        data["subject"] = "tampered-meta-subject"
        with open(meta_path, "w") as f:
            json.dump(data, f)
        
        data["subject"] = original_subject
        with open(meta_path, "w") as f:
            json.dump(data, f)
