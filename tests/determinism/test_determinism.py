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
            payload={"assert": True, "data": "test"},
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
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        request2 = EvaluationRequest(
            version="v1",
            subject="test-2",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        eval_id1, input_sha1, _ = run_pure_evaluation(request1)
        eval_id2, input_sha2, _ = run_pure_evaluation(request2)
        
        assert input_sha1 != input_sha2
        assert eval_id1 != eval_id2
    
    def test_accept_decision(self):
        """Payload with assert=true must produce ACCEPT."""
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result, _ = run_evaluation(request)
        assert result.decision == "ACCEPT"
    
    def test_reject_decision_missing_assert(self):
        """Payload without assert must produce REJECT."""
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"other": "data"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result, _ = run_evaluation(request)
        assert result.decision == "REJECT"
    
    def test_reject_decision_assert_false(self):
        """Payload with assert=false must produce REJECT."""
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"assert": False},
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
            payload={"assert": True},
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
            payload={"assert": True},
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
            payload={"assert": True},
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
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result, _ = run_evaluation(request)
        assert len(result.reasons) > 0
