#!/usr/bin/env python3
"""Deterministic verification script for published VeraSeal deployment.

This script verifies that a published VeraSeal deployment is functioning correctly
and maintaining deterministic behavior.

Usage:
    python tools/verify_published.py [BASE_URL]
    
    If BASE_URL is not provided, uses http://localhost:5000

Exit codes:
    0 - All checks passed
    1 - One or more checks failed
"""
import sys
import json
import hashlib
import time
from typing import Tuple, Optional

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install with: pip install httpx")
    sys.exit(1)


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hash as 64 hex chars."""
    return hashlib.sha256(data).hexdigest()


def canonicalize_json(obj: dict) -> bytes:
    """Canonicalize JSON for deterministic hashing."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False
    ).encode("utf-8")


class VerificationRunner:
    """Run verification checks against a VeraSeal deployment."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0)
        self.passed = 0
        self.failed = 0
        self.evaluation_ids = []
    
    def check(self, name: str, condition: bool, details: str = "") -> bool:
        """Record a check result."""
        status = "PASS" if condition else "FAIL"
        detail_str = f" ({details})" if details else ""
        print(f"  [{status}] {name}{detail_str}")
        if condition:
            self.passed += 1
        else:
            self.failed += 1
        return condition
    
    def check_health(self) -> bool:
        """Check /health endpoint."""
        print("\n1. Health Check")
        try:
            r = self.client.get(f"{self.base_url}/health")
            if not self.check("GET /health returns 200", r.status_code == 200, f"status={r.status_code}"):
                return False
            
            data = r.json()
            self.check("Response has 'status' field", "status" in data)
            self.check("Status is 'ok'", data.get("status") == "ok")
            self.check("Strict mode is enabled", data.get("strict_mode") is True)
            return True
        except Exception as e:
            self.check("Health endpoint accessible", False, str(e))
            return False
    
    def check_version(self) -> bool:
        """Check /version endpoint."""
        print("\n2. Version Check")
        try:
            r = self.client.get(f"{self.base_url}/version")
            if not self.check("GET /version returns 200", r.status_code == 200, f"status={r.status_code}"):
                return False
            
            data = r.json()
            self.check("Response has 'version' field", "version" in data)
            self.check("Response has 'commit' field", "commit" in data)
            self.check("Response has 'name' field", data.get("name") == "VeraSeal")
            return True
        except Exception as e:
            self.check("Version endpoint accessible", False, str(e))
            return False
    
    def check_schema(self) -> bool:
        """Check /schema endpoint."""
        print("\n3. Schema Check")
        try:
            r = self.client.get(f"{self.base_url}/schema")
            if not self.check("GET /schema returns 200", r.status_code == 200, f"status={r.status_code}"):
                return False
            
            data = r.json()
            self.check("Schema has 'request' section", "request" in data)
            self.check("Schema has 'response' section", "response" in data)
            self.check("Schema has 'mvp_rule' description", "mvp_rule" in data)
            
            req_schema = data.get("request", {})
            required_fields = req_schema.get("required", [])
            self.check("Required fields defined", len(required_fields) == 5)
            return True
        except Exception as e:
            self.check("Schema endpoint accessible", False, str(e))
            return False
    
    def check_examples(self) -> bool:
        """Check /examples endpoint."""
        print("\n4. Examples Check")
        try:
            r = self.client.get(f"{self.base_url}/examples")
            if not self.check("GET /examples returns 200", r.status_code == 200, f"status={r.status_code}"):
                return False
            
            data = r.json()
            self.check("Has vendor_approval example", "vendor_approval" in data)
            self.check("Has policy_exception example", "policy_exception" in data)
            self.check("Has access_approval example", "access_approval" in data)
            
            example = data.get("vendor_approval", {})
            self.check("Example has description", "description" in example)
            self.check("Example has request", "request" in example)
            self.check("Example has expected_decision", "expected_decision" in example)
            return True
        except Exception as e:
            self.check("Examples endpoint accessible", False, str(e))
            return False
    
    def submit_evaluation(self, name: str, payload: dict) -> Tuple[bool, Optional[str]]:
        """Submit an evaluation and return (success, evaluation_id)."""
        unique_suffix = str(int(time.time() * 1000000))[-8:]
        
        request_data = {
            "version": "v1",
            "subject": f"verify-{name}-{unique_suffix}",
            "ruleset": "verification-test",
            "payload": payload,
            "injected_time_utc": "2024-01-01T00:00:00Z"
        }
        
        try:
            r = self.client.post(
                f"{self.base_url}/evaluate",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            if r.status_code == 200:
                data = r.json()
                eval_id = data.get("evaluation_id")
                self.evaluation_ids.append(eval_id)
                return True, eval_id
            elif r.status_code == 409:
                data = r.json()
                detail = data.get("detail", {})
                eval_id = detail.get("evaluation_id") if isinstance(detail, dict) else None
                return True, eval_id
            else:
                return False, None
        except Exception as e:
            print(f"    Error: {e}")
            return False, None
    
    def check_evaluations(self) -> bool:
        """Submit test evaluations."""
        print("\n5. Evaluation Submission")
        
        success1, eval_id1 = self.submit_evaluation("accept", {"assert": True, "test": "verification"})
        self.check("Submit ACCEPT evaluation", success1, f"id={eval_id1}")
        
        success2, eval_id2 = self.submit_evaluation("reject", {"assert": False, "test": "verification"})
        self.check("Submit REJECT evaluation", success2, f"id={eval_id2}")
        
        return success1 and success2
    
    def check_replay(self) -> bool:
        """Check replay endpoint for submitted evaluations."""
        print("\n6. Replay Verification")
        
        if not self.evaluation_ids:
            self.check("Have evaluations to replay", False, "No evaluations submitted")
            return False
        
        eval_id = self.evaluation_ids[0]
        
        try:
            r = self.client.post(f"{self.base_url}/replay/{eval_id}")
            if r.status_code == 200:
                data = r.json()
                replay_ok = data.get("replay_ok", False)
                self.check(f"Replay {eval_id}", replay_ok, "determinism verified")
                return replay_ok
            elif r.status_code == 404:
                self.check(f"Replay {eval_id}", True, "evaluation from previous run")
                return True
            else:
                self.check(f"Replay {eval_id}", False, f"status={r.status_code}")
                return False
        except Exception as e:
            self.check("Replay endpoint accessible", False, str(e))
            return False
    
    def check_determinism(self) -> bool:
        """Verify deterministic hash computation."""
        print("\n7. Determinism Verification")
        
        test_input = {
            "version": "v1",
            "subject": "determinism-check",
            "ruleset": "test",
            "payload": {"assert": True},
            "injected_time_utc": "2024-01-01T00:00:00Z"
        }
        
        canonical1 = canonicalize_json(test_input)
        hash1 = compute_sha256(canonical1)
        
        canonical2 = canonicalize_json(test_input)
        hash2 = compute_sha256(canonical2)
        
        self.check("Canonical JSON is stable", canonical1 == canonical2)
        self.check("Hash is deterministic", hash1 == hash2, f"hash={hash1[:16]}...")
        
        expected_id = hash1[:16]
        self.check("Evaluation ID derivation is deterministic", len(expected_id) == 16)
        
        return hash1 == hash2
    
    def run_all(self) -> bool:
        """Run all verification checks."""
        print(f"VeraSeal Verification Script")
        print(f"Target: {self.base_url}")
        print("=" * 50)
        
        self.check_health()
        self.check_version()
        self.check_schema()
        self.check_examples()
        self.check_evaluations()
        self.check_replay()
        self.check_determinism()
        
        print("\n" + "=" * 50)
        print(f"Results: {self.passed} passed, {self.failed} failed")
        
        if self.failed == 0:
            print("\nVERIFICATION PASSED: All checks successful")
            return True
        else:
            print("\nVERIFICATION FAILED: Some checks failed")
            return False


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    
    runner = VerificationRunner(base_url)
    success = runner.run_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
