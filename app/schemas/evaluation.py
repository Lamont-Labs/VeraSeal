"""Strict Pydantic schemas for evaluation input/output.

All schemas use extra="forbid" to reject unknown fields.
"""
import hashlib
import json
import math
import re
from typing import Any, List

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


def _validate_json_only_types(value: Any, path: str = "payload") -> None:
    """Recursively validate that value contains only JSON-serializable types.
    
    Allowed: dict, list, str, int, float (not NaN/Inf), bool, None
    """
    if value is None:
        return
    if isinstance(value, bool):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"{path}: NaN and Infinity are forbidden")
        return
    if isinstance(value, str):
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError(f"{path}: dict keys must be strings")
            _validate_json_only_types(v, f"{path}.{k}")
        return
    if isinstance(value, list):
        for i, item in enumerate(value):
            _validate_json_only_types(item, f"{path}[{i}]")
        return
    raise ValueError(f"{path}: type {type(value).__name__} is not JSON-serializable")


def canonicalize_json(obj: Any) -> bytes:
    """Canonicalize JSON for deterministic hashing.
    
    - Sorted keys recursively
    - Fixed separators (",", ":")
    - No extra whitespace
    - UTF-8 encoding
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False
    ).encode("utf-8")


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hash as 64 hex chars."""
    return hashlib.sha256(data).hexdigest()


class EvaluationRequest(BaseModel):
    """Input schema for evaluation requests.
    
    All fields required. No extra fields allowed.
    """
    model_config = ConfigDict(extra="forbid", strict=True)
    
    version: str
    subject: str
    ruleset: str
    payload: dict
    injected_time_utc: str
    
    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        if v != "v1":
            raise ValueError("version must be 'v1'")
        return v
    
    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        if not v or len(v) > 128:
            raise ValueError("subject must be non-empty and max 128 chars")
        return v
    
    @field_validator("ruleset")
    @classmethod
    def validate_ruleset(cls, v: str) -> str:
        if not v or len(v) > 128:
            raise ValueError("ruleset must be non-empty and max 128 chars")
        return v
    
    @field_validator("injected_time_utc")
    @classmethod
    def validate_injected_time(cls, v: str) -> str:
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
        if not re.match(pattern, v):
            raise ValueError("injected_time_utc must be RFC3339/ISO8601 format")
        return v
    
    @model_validator(mode="after")
    def validate_payload_types(self) -> "EvaluationRequest":
        _validate_json_only_types(self.payload, "payload")
        return self


class TraceStep(BaseModel):
    """Single step in evaluation trace."""
    model_config = ConfigDict(extra="forbid")
    
    step_name: str
    status: str
    details: str


class EvaluationResult(BaseModel):
    """Output schema for evaluation results."""
    model_config = ConfigDict(extra="forbid")
    
    evaluation_id: str
    input_sha256: str
    output_sha256: str
    manifest_sha256: str
    decision: str
    reasons: List[str]
    trace: List[TraceStep]
    created_time_utc: str
    
    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v not in ("ACCEPT", "REJECT"):
            raise ValueError("decision must be 'ACCEPT' or 'REJECT'")
        return v
    
    @field_validator("reasons")
    @classmethod
    def validate_reasons(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("reasons must be non-empty")
        return v
    
    @field_validator("input_sha256", "output_sha256")
    @classmethod
    def validate_sha256(cls, v: str) -> str:
        if len(v) != 64 or not all(c in "0123456789abcdef" for c in v):
            raise ValueError("hash must be 64 hex chars")
        return v
    
    @field_validator("manifest_sha256")
    @classmethod
    def validate_manifest_sha256(cls, v: str) -> str:
        if v == "":
            return v
        if len(v) != 64 or not all(c in "0123456789abcdef" for c in v):
            raise ValueError("hash must be 64 hex chars")
        return v


class ReplayResult(BaseModel):
    """Result of replay verification."""
    model_config = ConfigDict(extra="forbid")
    
    replay_ok: bool
    mismatches: List[str]


class HealthResponse(BaseModel):
    """Health check response."""
    model_config = ConfigDict(extra="forbid")
    
    status: str
    strict_mode: bool
