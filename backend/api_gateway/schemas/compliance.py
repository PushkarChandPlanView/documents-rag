from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class ComplianceRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str
    params: dict[str, Any]
    severity: str

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        valid = {"keyword_required", "keyword_forbidden", "age_limit_days", "llm_check"}
        if v not in valid:
            raise ValueError(f"rule_type must be one of {valid}")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in {"critical", "high", "warning", "info"}:
            raise ValueError("severity must be one of: critical, high, warning, info")
        return v


class ComplianceRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    severity: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in {"critical", "high", "warning", "info"}:
            raise ValueError("severity must be one of: critical, high, warning, info")
        return v


class ComplianceRuleResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    rule_type: str
    params: dict[str, Any]
    severity: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LocationResponse(BaseModel):
    chunk_index: Optional[int] = None
    page_number: Optional[int] = None
    excerpt: str


class ComplianceRuleResultResponse(BaseModel):
    id: UUID
    rule_id: Optional[UUID] = None
    rule_name: str
    rule_type: str
    severity: str
    enforcement: str = "advisory"
    passed: bool
    detail: Optional[str] = None
    locations: Optional[list[LocationResponse]] = None

    model_config = {"from_attributes": True}


class ComplianceReportResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: str
    checked_at: datetime
    is_stale: bool = False
    insights: Optional[str] = None
    results: list[ComplianceRuleResultResponse] = []

    model_config = {"from_attributes": True}


class ComplianceStatsResponse(BaseModel):
    compliant: int = 0
    warning: int = 0
    non_compliant: int = 0
    unchecked: int = 0
    total_documents: int = 0


class ComplianceIssueFailedRule(BaseModel):
    rule_name: str
    severity: str
    enforcement: str = "advisory"
    detail: Optional[str] = None


class ComplianceIssueItem(BaseModel):
    document_id: UUID
    document_name: str
    report_id: UUID
    status: str
    checked_at: datetime
    is_stale: bool = False
    failing_rules: list[ComplianceIssueFailedRule] = []


class ComplianceIssuesResponse(BaseModel):
    items: list[ComplianceIssueItem]
    next_cursor: Optional[str] = None
    has_more: bool = False
