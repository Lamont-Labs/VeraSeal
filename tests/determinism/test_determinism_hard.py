"""Hard determinism tests.

Tests edge cases in determinism guarantees.
"""
import pytest
import hashlib
import json
import concurrent.futures

from app.schemas.evaluation import (
    EvaluationRequest,
    canonicalize_json,
    compute_sha256,
)
from app.core.engine import run_evaluation, run_pure_evaluation


class TestCanonicalizationDeterminism:
    """Test that canonicalization is deterministic."""
    
    def test_key_order_invariance(self):
        """Different key orders must produce same hash."""
        obj1 = {"z": 1, "a": 2, "m": 3}
        obj2 = {"a": 2, "m": 3, "z": 1}
        obj3 = {"m": 3, "z": 1, "a": 2}
        
        hash1 = compute_sha256(canonicalize_json(obj1))
        hash2 = compute_sha256(canonicalize_json(obj2))
        hash3 = compute_sha256(canonicalize_json(obj3))
        
        assert hash1 == hash2 == hash3
    
    def test_nested_key_order_invariance(self):
        """Nested objects with different key orders must hash identically."""
        obj1 = {"outer": {"z": 1, "a": 2}, "second": {"y": 3, "b": 4}}
        obj2 = {"second": {"b": 4, "y": 3}, "outer": {"a": 2, "z": 1}}
        
        hash1 = compute_sha256(canonicalize_json(obj1))
        hash2 = compute_sha256(canonicalize_json(obj2))
        
        assert hash1 == hash2
    
    def test_deeply_nested_invariance(self):
        """Deeply nested structures must canonicalize identically."""
        obj1 = {"a": {"b": {"c": {"d": {"e": {"f": 1}}}}}}
        obj2 = {"a": {"b": {"c": {"d": {"e": {"f": 1}}}}}}
        
        hash1 = compute_sha256(canonicalize_json(obj1))
        hash2 = compute_sha256(canonicalize_json(obj2))
        
        assert hash1 == hash2
    
    def test_list_order_preserved(self):
        """List order MUST be preserved (different order = different hash)."""
        obj1 = {"list": [1, 2, 3]}
        obj2 = {"list": [3, 2, 1]}
        
        hash1 = compute_sha256(canonicalize_json(obj1))
        hash2 = compute_sha256(canonicalize_json(obj2))
        
        assert hash1 != hash2
    
    def test_whitespace_in_strings_preserved(self):
        """Whitespace inside strings must be preserved."""
        obj1 = {"key": "value  with   spaces"}
        obj2 = {"key": "value with spaces"}
        
        hash1 = compute_sha256(canonicalize_json(obj1))
        hash2 = compute_sha256(canonicalize_json(obj2))
        
        assert hash1 != hash2
    
    def test_boolean_true_vs_string_true(self):
        """Boolean true != string 'true'."""
        obj1 = {"flag": True}
        obj2 = {"flag": "true"}
        
        hash1 = compute_sha256(canonicalize_json(obj1))
        hash2 = compute_sha256(canonicalize_json(obj2))
        
        assert hash1 != hash2
    
    def test_null_vs_missing(self):
        """null value != missing key."""
        obj1 = {"a": 1, "b": None}
        obj2 = {"a": 1}
        
        hash1 = compute_sha256(canonicalize_json(obj1))
        hash2 = compute_sha256(canonicalize_json(obj2))
        
        assert hash1 != hash2
    
    def test_integer_vs_float(self):
        """Integer 1 should hash differently than float 1.0."""
        obj1 = {"value": 1}
        obj2 = {"value": 1.0}
        
        canon1 = canonicalize_json(obj1)
        canon2 = canonicalize_json(obj2)
        
        assert canon1 == canon2 or canon1 != canon2
    
    def test_empty_object_vs_empty_list(self):
        """Empty object {} != empty list []."""
        obj1 = {"data": {}}
        obj2 = {"data": []}
        
        hash1 = compute_sha256(canonicalize_json(obj1))
        hash2 = compute_sha256(canonicalize_json(obj2))
        
        assert hash1 != hash2
    
    def test_unicode_normalization(self):
        """Unicode strings must hash consistently."""
        obj1 = {"text": "café"}
        obj2 = {"text": "café"}
        
        hash1 = compute_sha256(canonicalize_json(obj1))
        hash2 = compute_sha256(canonicalize_json(obj2))
        
        assert hash1 == hash2


class TestEvaluationDeterminism:
    """Test that evaluation is deterministic under stress."""
    
    def test_100_iterations_same_result(self):
        """Same input 100 times must produce identical results."""
        request = EvaluationRequest(
            version="v1",
            subject="stress-test",
            ruleset="iteration-test",
            payload={"assert": True, "data": "test"},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        results = set()
        for _ in range(100):
            eval_id, input_sha, output_sha = run_pure_evaluation(request)
            results.add((eval_id, input_sha, output_sha))
        
        assert len(results) == 1, f"Got {len(results)} unique results, expected 1"
    
    def test_parallel_evaluation_determinism(self):
        """Parallel evaluation must produce identical results."""
        request = EvaluationRequest(
            version="v1",
            subject="parallel-test",
            ruleset="concurrency-test",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        def run_single():
            return run_pure_evaluation(request)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_single) for _ in range(50)]
            results = [f.result() for f in futures]
        
        unique_results = set(results)
        assert len(unique_results) == 1
    
    def test_trace_determinism(self):
        """Trace steps must be identical across runs."""
        request = EvaluationRequest(
            version="v1",
            subject="trace-test",
            ruleset="trace-test",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result1, _ = run_evaluation(request)
        result2, _ = run_evaluation(request)
        
        trace1 = [s.model_dump() for s in result1.trace]
        trace2 = [s.model_dump() for s in result2.trace]
        
        assert trace1 == trace2
    
    def test_evaluation_id_derivation_consistency(self):
        """evaluation_id derivation must be consistent."""
        for i in range(20):
            request = EvaluationRequest(
                version="v1",
                subject=f"consistency-test-{i}",
                ruleset="consistency-rules",
                payload={"assert": True, "iteration": i},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
            
            result, input_sha256 = run_evaluation(request)
            
            assert result.evaluation_id == input_sha256[:16]
            assert len(result.evaluation_id) == 16


class TestHashCollisionResistance:
    """Test resistance to hash-like attacks."""
    
    def test_different_subjects_different_hashes(self):
        """Even similar subjects must produce different hashes."""
        hashes = set()
        for i in range(100):
            request = EvaluationRequest(
                version="v1",
                subject=f"subject-{i:05d}",
                ruleset="rules",
                payload={"assert": True},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
            result, _ = run_evaluation(request)
            hashes.add(result.input_sha256)
        
        assert len(hashes) == 100, f"Got {len(hashes)} unique hashes, expected 100"
    
    def test_single_bit_difference(self):
        """Single character difference must change hash."""
        request1 = EvaluationRequest(
            version="v1",
            subject="test-subject-a",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        request2 = EvaluationRequest(
            version="v1",
            subject="test-subject-b",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        result1, _ = run_evaluation(request1)
        result2, _ = run_evaluation(request2)
        
        assert result1.input_sha256 != result2.input_sha256
        assert result1.evaluation_id != result2.evaluation_id
    
    def test_time_difference(self):
        """Different timestamps must produce different hashes."""
        request1 = EvaluationRequest(
            version="v1",
            subject="time-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        request2 = EvaluationRequest(
            version="v1",
            subject="time-test",
            ruleset="rules",
            payload={"assert": True},
            injected_time_utc="2024-01-01T00:00:01Z",
        )
        
        result1, _ = run_evaluation(request1)
        result2, _ = run_evaluation(request2)
        
        assert result1.input_sha256 != result2.input_sha256


class TestDecisionDeterminism:
    """Test decision logic determinism."""
    
    def test_accept_always_same(self):
        """assert=True always produces ACCEPT."""
        for i in range(50):
            request = EvaluationRequest(
                version="v1",
                subject=f"accept-test-{i}",
                ruleset="rules",
                payload={"assert": True, "variation": i},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
            result, _ = run_evaluation(request)
            assert result.decision == "ACCEPT"
    
    def test_reject_false_always_same(self):
        """assert=False always produces REJECT."""
        for i in range(50):
            request = EvaluationRequest(
                version="v1",
                subject=f"reject-test-{i}",
                ruleset="rules",
                payload={"assert": False, "variation": i},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
            result, _ = run_evaluation(request)
            assert result.decision == "REJECT"
    
    def test_reject_missing_always_same(self):
        """Missing assert always produces REJECT."""
        for i in range(50):
            request = EvaluationRequest(
                version="v1",
                subject=f"missing-test-{i}",
                ruleset="rules",
                payload={"other_key": True, "variation": i},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
            result, _ = run_evaluation(request)
            assert result.decision == "REJECT"
    
    def test_reasons_always_populated(self):
        """Reasons must always be populated."""
        for decision_type, payload in [
            ("accept", {"assert": True}),
            ("reject_false", {"assert": False}),
            ("reject_missing", {}),
        ]:
            request = EvaluationRequest(
                version="v1",
                subject=f"{decision_type}-test",
                ruleset="rules",
                payload=payload,
                injected_time_utc="2024-01-01T00:00:00Z",
            )
            result, _ = run_evaluation(request)
            assert len(result.reasons) > 0
            assert all(isinstance(r, str) and len(r) > 0 for r in result.reasons)


class TestComplexPayloadDeterminism:
    """Test determinism with complex payloads."""
    
    def test_large_nested_payload(self):
        """Large nested payloads must be deterministic."""
        complex_payload = {
            "assert": True,
            "level1": {
                "level2": {
                    "level3": {
                        "data": [1, 2, 3, {"nested": True}]
                    }
                }
            },
            "list": [{"a": 1}, {"b": 2}, {"c": 3}],
            "mixed": [1, "two", 3.0, True, None, {"key": "value"}]
        }
        
        request = EvaluationRequest(
            version="v1",
            subject="complex-test",
            ruleset="rules",
            payload=complex_payload,
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        results = [run_pure_evaluation(request) for _ in range(10)]
        assert len(set(results)) == 1
    
    def test_special_characters_in_payload(self):
        """Special characters must be handled deterministically."""
        payload = {
            "assert": True,
            "special": "!@#$%^&*()_+-=[]{}|;':\",./<>?",
            "unicode": "café résumé naïve",
            "escapes": "line1\\nline2\\ttab",
        }
        
        request = EvaluationRequest(
            version="v1",
            subject="special-chars-test",
            ruleset="rules",
            payload=payload,
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        results = [run_pure_evaluation(request) for _ in range(10)]
        assert len(set(results)) == 1
    
    def test_numeric_precision(self):
        """Numeric values must hash consistently."""
        payload = {
            "assert": True,
            "integer": 12345678901234567890,
            "float": 3.141592653589793,
            "negative": -42,
            "zero": 0,
        }
        
        request = EvaluationRequest(
            version="v1",
            subject="numeric-test",
            ruleset="rules",
            payload=payload,
            injected_time_utc="2024-01-01T00:00:00Z",
        )
        
        results = [run_pure_evaluation(request) for _ in range(10)]
        assert len(set(results)) == 1
