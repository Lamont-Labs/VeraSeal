"""Adversarial input tests - 10x harder hostile inputs.

Tests that attempt to break the system through edge cases,
injection attacks, and malformed data.
"""
import pytest
import json
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.evaluation import EvaluationRequest, canonicalize_json, compute_sha256


client = TestClient(app)


def unique_id():
    return uuid.uuid4().hex[:8]


VALID_REQUEST = {
    "version": "v1",
    "subject": "test-subject",
    "ruleset": "test-ruleset",
    "payload": {"assert": True},
    "injected_time_utc": "2024-01-01T00:00:00Z",
}


class TestTypeCoercion:
    """Test that type coercion attacks are rejected."""
    
    def test_version_as_integer(self):
        request = {**VALID_REQUEST, "version": 1}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_version_as_list(self):
        request = {**VALID_REQUEST, "version": ["v1"]}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_version_as_dict(self):
        request = {**VALID_REQUEST, "version": {"value": "v1"}}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_version_as_null(self):
        request = {**VALID_REQUEST, "version": None}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_version_as_boolean(self):
        request = {**VALID_REQUEST, "version": True}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_subject_as_integer(self):
        request = {**VALID_REQUEST, "subject": 12345}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_subject_as_list(self):
        request = {**VALID_REQUEST, "subject": ["test"]}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_payload_as_string(self):
        request = {**VALID_REQUEST, "payload": '{"assert": true}'}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_payload_as_list(self):
        request = {**VALID_REQUEST, "payload": [{"assert": True}]}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_payload_as_null(self):
        request = {**VALID_REQUEST, "payload": None}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_injected_time_as_integer(self):
        request = {**VALID_REQUEST, "injected_time_utc": 1704067200}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422


class TestInjectionAttacks:
    """Test resistance to injection attacks."""
    
    def test_subject_with_path_traversal(self):
        request = {**VALID_REQUEST, "subject": "../../../etc/passwd", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            assert "../" not in response.json()["evaluation_id"]
    
    def test_subject_with_null_byte(self):
        request = {**VALID_REQUEST, "subject": f"test\x00subject-{unique_id()}", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409, 422, 400)
    
    def test_subject_with_unicode_escape(self):
        request = {**VALID_REQUEST, "subject": f"test\\u0000subj-{unique_id()}", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409, 422)
    
    def test_payload_with_script_tag(self):
        request = {**VALID_REQUEST, "subject": f"xss-test-{unique_id()}", "payload": {"assert": True, "xss": "<script>alert(1)</script>", "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_payload_with_sql_injection(self):
        request = {**VALID_REQUEST, "subject": f"sql-test-{unique_id()}", "payload": {"assert": True, "sql": "'; DROP TABLE users; --", "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_payload_with_template_injection(self):
        request = {**VALID_REQUEST, "subject": f"tpl-test-{unique_id()}", "payload": {"assert": True, "template": "{{7*7}}", "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_subject_with_newlines(self):
        request = {**VALID_REQUEST, "subject": f"line1\nline2\rline3-{unique_id()}", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409, 422)


class TestBoundaryValues:
    """Test boundary value conditions."""
    
    def test_subject_exactly_128_chars(self):
        base = "x" * 120 + unique_id()
        request = {**VALID_REQUEST, "subject": base[:128], "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_subject_127_chars(self):
        base = "y" * 119 + unique_id()
        request = {**VALID_REQUEST, "subject": base[:127], "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_ruleset_exactly_128_chars(self):
        base = "r" * 120 + unique_id()
        request = {**VALID_REQUEST, "ruleset": base[:128], "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_subject_single_char(self):
        request = {**VALID_REQUEST, "subject": "z", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_empty_payload(self):
        request = {**VALID_REQUEST, "subject": f"empty-{unique_id()}", "payload": {}}
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            data = response.json()
            assert data["result"]["decision"] == "REJECT"
        else:
            assert response.status_code == 409
    
    def test_deeply_nested_payload(self):
        nested = {"level": 1, "uid": unique_id()}
        for i in range(2, 51):
            nested = {"level": i, "child": nested}
        request = {**VALID_REQUEST, "subject": f"nested-{unique_id()}", "payload": {"assert": True, "nested": nested}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_large_payload(self):
        uid = unique_id()
        large_data = {"key_" + str(i): "value_" + str(i) for i in range(1000)}
        request = {**VALID_REQUEST, "subject": f"large-{uid}", "payload": {"assert": True, "uid": uid, **large_data}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_payload_with_long_strings(self):
        uid = unique_id()
        request = {**VALID_REQUEST, "subject": f"long-{uid}", "payload": {"assert": True, "long": "x" * 100000, "uid": uid}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)


class TestTimeFormatEdgeCases:
    """Test edge cases in time format validation."""
    
    def test_time_with_milliseconds(self):
        request = {**VALID_REQUEST, "subject": f"ms-{unique_id()}", "injected_time_utc": "2024-01-01T00:00:00.123Z", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_time_with_microseconds(self):
        request = {**VALID_REQUEST, "subject": f"us-{unique_id()}", "injected_time_utc": "2024-01-01T00:00:00.123456Z", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_time_with_timezone_offset_positive(self):
        request = {**VALID_REQUEST, "subject": f"tzp-{unique_id()}", "injected_time_utc": "2024-01-01T12:00:00+05:30", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_time_with_timezone_offset_negative(self):
        request = {**VALID_REQUEST, "subject": f"tzn-{unique_id()}", "injected_time_utc": "2024-01-01T12:00:00-08:00", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_time_midnight(self):
        request = {**VALID_REQUEST, "subject": f"mid-{unique_id()}", "injected_time_utc": "2024-01-01T00:00:00Z", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_time_end_of_day(self):
        request = {**VALID_REQUEST, "subject": f"eod-{unique_id()}", "injected_time_utc": "2024-01-01T23:59:59Z", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_time_leap_year(self):
        request = {**VALID_REQUEST, "subject": f"leap-{unique_id()}", "injected_time_utc": "2024-02-29T12:00:00Z", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_invalid_time_no_seconds(self):
        request = {**VALID_REQUEST, "injected_time_utc": "2024-01-01T12:00Z"}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_invalid_time_no_t_separator(self):
        request = {**VALID_REQUEST, "injected_time_utc": "2024-01-01 12:00:00Z"}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422
    
    def test_invalid_time_lowercase_z(self):
        request = {**VALID_REQUEST, "injected_time_utc": "2024-01-01T12:00:00z"}
        response = client.post("/evaluate", json=request)
        assert response.status_code == 422


class TestMalformedJSON:
    """Test handling of malformed JSON."""
    
    def test_truncated_json(self):
        response = client.post(
            "/evaluate",
            content=b'{"version": "v1", "subject":',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
    
    def test_json_with_trailing_comma(self):
        response = client.post(
            "/evaluate",
            content=b'{"version": "v1", "subject": "test",}',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
    
    def test_json_with_single_quotes(self):
        response = client.post(
            "/evaluate",
            content=b"{'version': 'v1'}",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
    
    def test_json_with_unquoted_keys(self):
        response = client.post(
            "/evaluate",
            content=b'{version: "v1"}',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
    
    def test_empty_body(self):
        response = client.post(
            "/evaluate",
            content=b'',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in (400, 422)
    
    def test_null_body(self):
        response = client.post(
            "/evaluate",
            content=b'null',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_array_body(self):
        response = client.post(
            "/evaluate",
            content=b'[{"version": "v1"}]',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_json_with_comments(self):
        response = client.post(
            "/evaluate",
            content=b'{"version": "v1" /* comment */}',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400


class TestUnicodeEdgeCases:
    """Test Unicode edge cases."""
    
    def test_subject_with_emoji(self):
        request = {**VALID_REQUEST, "subject": f"test-🔐-{unique_id()}", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_subject_with_chinese(self):
        request = {**VALID_REQUEST, "subject": f"测试主题-{unique_id()}", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_subject_with_arabic(self):
        request = {**VALID_REQUEST, "subject": f"موضوع-{unique_id()}", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_subject_with_rtl_override(self):
        request = {**VALID_REQUEST, "subject": f"test\u202eevil-{unique_id()}", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409, 422)
    
    def test_payload_with_zero_width_chars(self):
        request = {**VALID_REQUEST, "subject": f"zw-{unique_id()}", "payload": {"assert": True, "key": "test\u200bvalue", "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)
    
    def test_subject_with_combining_chars(self):
        request = {**VALID_REQUEST, "subject": f"test\u0301subj-{unique_id()}", "payload": {"assert": True, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        assert response.status_code in (200, 409)


class TestPayloadTypeCoercion:
    """Test payload value type coercion resistance."""
    
    def test_assert_as_string_true(self):
        request = {**VALID_REQUEST, "subject": f"str-true-{unique_id()}", "payload": {"assert": "true", "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            assert response.json()["result"]["decision"] == "REJECT"
        else:
            assert response.status_code == 409
    
    def test_assert_as_string_True(self):
        request = {**VALID_REQUEST, "subject": f"str-True-{unique_id()}", "payload": {"assert": "True", "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            assert response.json()["result"]["decision"] == "REJECT"
        else:
            assert response.status_code == 409
    
    def test_assert_as_integer_1(self):
        request = {**VALID_REQUEST, "subject": f"int-1-{unique_id()}", "payload": {"assert": 1, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            assert response.json()["result"]["decision"] == "REJECT"
        else:
            assert response.status_code == 409
    
    def test_assert_as_integer_0(self):
        request = {**VALID_REQUEST, "subject": f"int-0-{unique_id()}", "payload": {"assert": 0, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            assert response.json()["result"]["decision"] == "REJECT"
        else:
            assert response.status_code == 409
    
    def test_assert_as_empty_list(self):
        request = {**VALID_REQUEST, "subject": f"list-{unique_id()}", "payload": {"assert": [], "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            assert response.json()["result"]["decision"] == "REJECT"
        else:
            assert response.status_code == 409
    
    def test_assert_as_empty_dict(self):
        request = {**VALID_REQUEST, "subject": f"dict-{unique_id()}", "payload": {"assert": {}, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            assert response.json()["result"]["decision"] == "REJECT"
        else:
            assert response.status_code == 409
    
    def test_assert_as_null(self):
        request = {**VALID_REQUEST, "subject": f"null-{unique_id()}", "payload": {"assert": None, "uid": unique_id()}}
        response = client.post("/evaluate", json=request)
        if response.status_code == 200:
            assert response.json()["result"]["decision"] == "REJECT"
        else:
            assert response.status_code == 409


class TestNegativeInfinity:
    """Test negative infinity handling."""
    
    def test_payload_with_negative_infinity(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="test",
                payload={"value": float("-inf")},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_nested_nan(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="test",
                payload={"nested": {"deep": {"value": float("nan")}}},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
    
    def test_list_with_nan(self):
        with pytest.raises(Exception):
            EvaluationRequest(
                version="v1",
                subject="test",
                ruleset="test",
                payload={"list": [1, 2, float("nan")]},
                injected_time_utc="2024-01-01T00:00:00Z",
            )
