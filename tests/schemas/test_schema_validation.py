"""Schema validation tests.

Comprehensive tests for Pydantic schema validation.
"""
import pytest
import json
import math

from app.schemas.evaluation import (
    EvaluationRequest,
    EvaluationResult,
    TraceStep,
    ReplayResult,
    HealthResponse,
    canonicalize_json,
    compute_sha256,
)


class TestEvaluationRequestSchema:
    """Test EvaluationRequest schema validation."""
    
    def test_valid_minimal_request(self):
        req = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        assert req.version == "v1"
    
    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="rules",
                payload={},
                injected_time_utc="2024-01-01T00:00:00Z",
                extra_field="forbidden",
            )
    
    def test_version_must_be_v1(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v2",
                subject="test",
                ruleset="rules",
                payload={},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_version_must_be_string(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version=1,
                subject="test",
                ruleset="rules",
                payload={},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_subject_cannot_be_empty(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="",
                ruleset="rules",
                payload={},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_subject_max_128_chars(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="x" * 129,
                ruleset="rules",
                payload={},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_subject_exactly_128_chars_ok(self):
        req = EvaluationRequest(
            version="v1",
            subject="x" * 128,
            ruleset="rules",
            payload={},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        assert len(req.subject) == 128
    
    def test_ruleset_cannot_be_empty(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="",
                payload={},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_ruleset_max_128_chars(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="x" * 129,
                payload={},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_payload_must_be_dict(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="rules",
                payload=[1, 2, 3],
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_payload_nan_forbidden(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="rules",
                payload={"value": float("nan")},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_payload_infinity_forbidden(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="rules",
                payload={"value": float("inf")},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_payload_nested_nan_forbidden(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="rules",
                payload={"nested": {"value": float("nan")}},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_payload_list_nan_forbidden(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="rules",
                payload={"list": [1, float("nan"), 3]},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_time_format_rfc3339_z(self):
        req = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={},
            injected_time_utc="2024-01-15T10:30:00Z",
        )
        assert req.injected_time_utc == "2024-01-15T10:30:00Z"
    
    def test_time_format_rfc3339_offset(self):
        req = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={},
            injected_time_utc="2024-01-15T10:30:00+05:30",
        )
        assert "+05:30" in req.injected_time_utc
    
    def test_time_format_milliseconds(self):
        req = EvaluationRequest(
            version="v1",
            subject="test",
            ruleset="rules",
            payload={},
            injected_time_utc="2024-01-15T10:30:00.123Z",
        )
        assert ".123Z" in req.injected_time_utc
    
    def test_time_format_invalid(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="rules",
                payload={},
                injected_time_utc="2024-01-15",
            )


class TestEvaluationResultSchema:
    """Test EvaluationResult schema validation."""
    
    def test_valid_result(self):
        result = EvaluationResult(
            evaluation_id="1234567890abcdef",
            input_sha256="a" * 64,
            output_sha256="b" * 64,
            manifest_sha256="c" * 64,
            decision="ACCEPT",
            reasons=["test reason"],
            trace=[],
            created_time_utc="2024-01-01T00:00:00Z",
        )
        assert result.decision == "ACCEPT"
    
    def test_decision_must_be_accept_or_reject(self):
        with pytest.raises(Exception):
            EvaluationResult(
                evaluation_id="1234567890abcdef",
                input_sha256="a" * 64,
                output_sha256="b" * 64,
                manifest_sha256="c" * 64,
                decision="MAYBE",
                reasons=["test"],
                trace=[],
                created_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_reasons_cannot_be_empty(self):
        with pytest.raises(Exception):
            EvaluationResult(
                evaluation_id="1234567890abcdef",
                input_sha256="a" * 64,
                output_sha256="b" * 64,
                manifest_sha256="c" * 64,
                decision="ACCEPT",
                reasons=[],
                trace=[],
                created_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_input_sha256_must_be_64_hex(self):
        with pytest.raises(Exception):
            EvaluationResult(
                evaluation_id="1234567890abcdef",
                input_sha256="a" * 63,
                output_sha256="b" * 64,
                manifest_sha256="c" * 64,
                decision="ACCEPT",
                reasons=["test"],
                trace=[],
                created_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_output_sha256_must_be_64_hex(self):
        with pytest.raises(Exception):
            EvaluationResult(
                evaluation_id="1234567890abcdef",
                input_sha256="a" * 64,
                output_sha256="x" * 64,
                manifest_sha256="c" * 64,
                decision="ACCEPT",
                reasons=["test"],
                trace=[],
                created_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_manifest_sha256_can_be_empty(self):
        result = EvaluationResult(
            evaluation_id="1234567890abcdef",
            input_sha256="a" * 64,
            output_sha256="b" * 64,
            manifest_sha256="",
            decision="ACCEPT",
            reasons=["test"],
            trace=[],
            created_time_utc="2024-01-01T00:00:00Z",
        )
        assert result.manifest_sha256 == ""


class TestTraceStepSchema:
    """Test TraceStep schema validation."""
    
    def test_valid_trace_step(self):
        step = TraceStep(
            step_name="test_step",
            status="PASS",
            details="Test details",
        )
        assert step.step_name == "test_step"
    
    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            TraceStep(
                step_name="test",
                status="PASS",
                details="details",
                extra="forbidden",
            )


class TestReplayResultSchema:
    """Test ReplayResult schema validation."""
    
    def test_valid_replay_ok(self):
        result = ReplayResult(replay_ok=True, mismatches=[])
        assert result.replay_ok is True
    
    def test_valid_replay_failed(self):
        result = ReplayResult(replay_ok=False, mismatches=["mismatch1"])
        assert result.replay_ok is False
        assert len(result.mismatches) == 1


class TestHealthResponseSchema:
    """Test HealthResponse schema validation."""
    
    def test_valid_health(self):
        health = HealthResponse(status="ok", strict_mode=True)
        assert health.status == "ok"


class TestCanonicalization:
    """Test JSON canonicalization."""
    
    def test_sorted_keys(self):
        obj = {"z": 1, "a": 2, "m": 3}
        canon = canonicalize_json(obj)
        assert b'"a":2' in canon
        assert canon.index(b'"a"') < canon.index(b'"m"') < canon.index(b'"z"')
    
    def test_no_whitespace(self):
        obj = {"key": "value"}
        canon = canonicalize_json(obj)
        assert b" " not in canon
        assert b"\n" not in canon
    
    def test_utf8_encoding(self):
        obj = {"text": "café"}
        canon = canonicalize_json(obj)
        assert isinstance(canon, bytes)
        assert "café".encode("utf-8") in canon
    
    def test_nested_sorted(self):
        obj = {"outer": {"z": 1, "a": 2}}
        canon = canonicalize_json(obj)
        assert canon.index(b'"a"') < canon.index(b'"z"')
    
    def test_list_preserved(self):
        obj = {"list": [3, 1, 2]}
        canon = canonicalize_json(obj)
        assert b"[3,1,2]" in canon


class TestHashComputation:
    """Test SHA-256 hash computation."""
    
    def test_hash_length(self):
        data = b"test data"
        hash_val = compute_sha256(data)
        assert len(hash_val) == 64
    
    def test_hash_hex_chars(self):
        data = b"test"
        hash_val = compute_sha256(data)
        assert all(c in "0123456789abcdef" for c in hash_val)
    
    def test_hash_determinism(self):
        data = b"same input"
        hash1 = compute_sha256(data)
        hash2 = compute_sha256(data)
        assert hash1 == hash2
    
    def test_hash_different_inputs(self):
        hash1 = compute_sha256(b"input1")
        hash2 = compute_sha256(b"input2")
        assert hash1 != hash2
    
    def test_hash_empty_input(self):
        hash_val = compute_sha256(b"")
        assert len(hash_val) == 64
