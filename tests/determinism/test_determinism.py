"""Determinism tests.

Tests that the evaluation engine produces identical outputs for identical inputs.
"""
import pytest

from app.schemas.evaluation import EvaluationRequest
from app.core.engine import run_pure_evaluation, run_evaluation


class TestEngineDeterminism:
    """Test that the pure engine function is deterministic."""
    
    def test_same_input_same_output(self):
        """Same input submitted 3 times must produce identical hashes."""
        request = EvaluationRequest(
            version="v1",
            subject="determinism-test",
            ruleset="test-rules",
            payload={"decision_requested": "ACCEPT", "justification": "Test data for determinism check"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        results = []
        for _ in range(3):
            eval_id, input_sha, output_sha = run_pure_evaluation(request)
            results.append((eval_id, input_sha, output_sha))
        
        assert results[0] == results[1] == results[2], "Engine not deterministic"
    
    def test_different_inputs_different_outputs(self):
        """Different inputs must produce different hashes."""
        request1 = EvaluationRequest(
            version="v1",
            subject="test-1",
            ruleset="rules",
            payload={"decision_requested": "ACCEPT", "justification": "First test request"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        request2 = EvaluationRequest(
            version="v1",
            subject="test-2",
            ruleset="rules",
            payload={"decision_requested": "ACCEPT", "justification": "Second test request"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        eval_id1, input_sha1, _ = run_pure_evaluation(request1)
        eval_id2, input_sha2, _ = run_pure_evaluation(request2)
        
        assert input_sha1 != input_sha2
        assert eval_id1 != eval_id2
    
    def test_accept_decision(self):
        """Payload with decision_requested=ACCEPT must produce ACCEPT."""
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"decision_requested": "ACCEPT", "justification": "Valid approval justification"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result, _ = run_evaluation(request)
        assert result.decision == "ACCEPT"
    
    def test_reject_decision_missing_decision_requested(self):
        """Payload without decision_requested must produce REJECT."""
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"justification": "Missing decision_requested field"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result, _ = run_evaluation(request)
        assert result.decision == "REJECT"
    
    def test_reject_decision_requested_reject(self):
        """Payload with decision_requested=REJECT must produce REJECT."""
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"decision_requested": "REJECT", "justification": "Explicitly rejected"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result, _ = run_evaluation(request)
        assert result.decision == "REJECT"
    
    def test_reject_missing_justification(self):
        """Payload without justification must produce REJECT."""
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"decision_requested": "ACCEPT"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result, _ = run_evaluation(request)
        assert result.decision == "REJECT"
    
    def test_reject_empty_justification(self):
        """Payload with empty justification must produce REJECT."""
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"decision_requested": "ACCEPT", "justification": ""},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result, _ = run_evaluation(request)
        assert result.decision == "REJECT"
    
    def test_reject_invalid_decision_requested(self):
        """Payload with invalid decision_requested must produce REJECT."""
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"decision_requested": "MAYBE", "justification": "Invalid decision value"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result, _ = run_evaluation(request)
        assert result.decision == "REJECT"
    
    def test_evaluation_id_derived_from_input_hash(self):
        """evaluation_id must be first 16 chars of input_sha256."""
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"decision_requested": "ACCEPT", "justification": "ID derivation test"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result, input_sha256 = run_evaluation(request)
        assert result.evaluation_id == input_sha256[:16]
    
    def test_created_time_equals_injected_time(self):
        """created_time_utc must equal injected_time_utc."""
        injected = "2024-06-15T10:30:00Z"
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"decision_requested": "ACCEPT", "justification": "Time validation test"},
            injected_time_utc=injected,
        )
        
        result, _ = run_evaluation(request)
        assert result.created_time_utc == injected
    
    def test_hash_format(self):
        """Hashes must be 64 hex chars."""
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"decision_requested": "ACCEPT", "justification": "Hash format test"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result, input_sha256 = run_evaluation(request)
        
        assert len(input_sha256) == 64
        assert len(result.output_sha256) == 64
        assert all(c in "0123456789abcdef" for c in input_sha256)
        assert all(c in "0123456789abcdef" for c in result.output_sha256)
    
    def test_reasons_non_empty(self):
        """reasons must always be non-empty."""
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"decision_requested": "ACCEPT", "justification": "Reasons validation test"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result, _ = run_evaluation(request)
        assert len(result.reasons) > 0
    
    def test_policy_id_in_result(self):
        """Result must include policy_id."""
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"decision_requested": "ACCEPT", "justification": "Policy ID test"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result, _ = run_evaluation(request)
        assert result.policy_id == "evaluation-policy-v1"
