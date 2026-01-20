"""Invariant check tests.

Tests for pre, during, and post invariant checks.
"""
import pytest

from app.schemas.evaluation import EvaluationRequest, EvaluationResult, TraceStep
from app.invariants.checks import (
    check_pre_invariants,
    check_during_invariants,
    check_post_invariants,
    InvariantViolation,
)
from app.core.engine import run_evaluation


class TestPreInvariants:
    """Test pre-evaluation invariant checks."""
    
    def test_valid_request_passes_all(self):
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        checks = check_pre_invariants(request)
        assert all(status == "PASS" for _, status in checks)
    
    def test_all_checks_return_tuples(self):
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        checks = check_pre_invariants(request)
        for check in checks:
            assert isinstance(check, tuple)
            assert len(check) == 2
            name, status = check
            assert isinstance(name, str)
            assert isinstance(status, str)


class TestDuringInvariants:
    """Test during-evaluation invariant checks."""
    
    def test_during_checks_pass(self):
        checks = check_during_invariants()
        assert all(status == "PASS" for _, status in checks)
    
    def test_during_checks_format(self):
        checks = check_during_invariants()
        for check in checks:
            assert isinstance(check, tuple)
            assert len(check) == 2


class TestPostInvariants:
    """Test post-evaluation invariant checks."""
    
    def test_valid_result_passes(self):
        request = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, input_sha256 = run_evaluation(request)
        checks = check_post_invariants(result, input_sha256)
        assert all(status == "PASS" for _, status in checks)
    
    def test_evaluation_id_derivation_check(self):
        request = EvaluationRequest(
            version="v1",
            subject="derivation-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, input_sha256 = run_evaluation(request)
        assert result.evaluation_id == input_sha256[:16]


class TestInvariantViolation:
    """Test InvariantViolation exception."""
    
    def test_exception_message(self):
        with pytest.raises(InvariantViolation) as exc_info:
            raise InvariantViolation("test message")
        assert "test message" in str(exc_info.value)


class TestEvaluationInvariants:
    """Test that evaluation enforces invariants end-to-end."""
    
    def test_trace_contains_pre_checks(self):
        request = EvaluationRequest(
            version="v1",
            subject="trace-pre-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, _ = run_evaluation(request)
        trace_names = [s.step_name for s in result.trace]
        assert any("pre_" in name for name in trace_names)
    
    def test_trace_contains_during_checks(self):
        request = EvaluationRequest(
            version="v1",
            subject="trace-during-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, _ = run_evaluation(request)
        trace_names = [s.step_name for s in result.trace]
        assert any("during_" in name for name in trace_names)
    
    def test_trace_contains_post_checks(self):
        request = EvaluationRequest(
            version="v1",
            subject="trace-post-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, _ = run_evaluation(request)
        trace_names = [s.step_name for s in result.trace]
        assert any("post_" in name for name in trace_names)
    
    def test_all_trace_steps_pass(self):
        request = EvaluationRequest(
            version="v1",
            subject="trace-all-pass",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, _ = run_evaluation(request)
        assert all(s.status == "PASS" for s in result.trace)
    
    def test_trace_step_details_non_empty(self):
        request = EvaluationRequest(
            version="v1",
            subject="trace-details-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, _ = run_evaluation(request)
        assert all(len(s.details) > 0 for s in result.trace)


class TestHashInvariants:
    """Test hash-related invariants."""
    
    def test_input_hash_64_chars(self):
        request = EvaluationRequest(
            version="v1",
            subject="hash-len-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, input_sha256 = run_evaluation(request)
        assert len(input_sha256) == 64
        assert len(result.input_sha256) == 64
    
    def test_output_hash_64_chars(self):
        request = EvaluationRequest(
            version="v1",
            subject="output-hash-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, _ = run_evaluation(request)
        assert len(result.output_sha256) == 64
    
    def test_hashes_are_lowercase_hex(self):
        request = EvaluationRequest(
            version="v1",
            subject="hex-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, input_sha256 = run_evaluation(request)
        assert all(c in "0123456789abcdef" for c in input_sha256)
        assert all(c in "0123456789abcdef" for c in result.output_sha256)


class TestDecisionInvariants:
    """Test decision-related invariants."""
    
    def test_decision_is_string(self):
        request = EvaluationRequest(
            version="v1",
            subject="decision-type-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, _ = run_evaluation(request)
        assert isinstance(result.decision, str)
    
    def test_decision_is_uppercase(self):
        request = EvaluationRequest(
            version="v1",
            subject="decision-case-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, _ = run_evaluation(request)
        assert result.decision == result.decision.upper()
    
    def test_reasons_is_list(self):
        request = EvaluationRequest(
            version="v1",
            subject="reasons-type-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, _ = run_evaluation(request)
        assert isinstance(result.reasons, list)
    
    def test_reasons_contains_strings(self):
        request = EvaluationRequest(
            version="v1",
            subject="reasons-content-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        result, _ = run_evaluation(request)
        assert all(isinstance(r, str) for r in result.reasons)
