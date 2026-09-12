from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field

Severity = Literal["minor","moderate","serious","fatal"]
EvidenceStatus = Literal["present","missing","not_applicable","unverifiable"]
Verdict = Literal["addressed","partial","not_addressed","disputed","unverifiable"]

class Evidence(BaseModel):
    evidence_id: str = ""
    source_kind: str = "paper_text"
    location: str = "global"
    claim_type: Literal["fact","judgment","inference"] = "judgment"
    status: EvidenceStatus = "present"
    excerpt_or_description: str = ""
    confidence: float = Field(default=0.7, ge=0, le=1)
    search_scope: str = ""
    search_terms: list[str] = Field(default_factory=list)

class Issue(BaseModel):
    id: str = ""
    summary: str
    detail: str
    severity: Severity
    category: str
    raised_by: list[str] = Field(default_factory=list)
    origin: list[str] = Field(default_factory=lambda: ['review'])
    question_refs: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    impact: str = ""
    suggested_fix: str = ""
    completion_test: str = ""
    status: str = "open"

class Review(BaseModel):
    judge_type: str
    score: Optional[float] = Field(default=None, ge=0, le=100)
    confidence: int = Field(default=3, ge=1, le=5)
    expertise: int = Field(default=3, ge=1, le=5)
    strengths: list[str] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    question_coverage: dict[str,str] = Field(default_factory=dict)
    recommendation: str = "revise"

class RebuttalItem(BaseModel):
    issue_id: str
    stance: Literal["clarify","concede_fix","concede_partial","disagree","unverifiable"]
    response: str
    cited_locations: list[str] = Field(default_factory=list)
    promised_revision: str = ""

class Rebuttal(BaseModel):
    summary: str
    responses: list[RebuttalItem]

class ReReviewItem(BaseModel):
    issue_id: str
    verdict: Verdict
    rationale: str
    evidence_locations: list[str] = Field(default_factory=list)

class ReReview(BaseModel):
    judge_type: str
    issue_verdicts: list[ReReviewItem] = Field(default_factory=list)
    recommendation_after_rebuttal: str = "revise"

class ChairDecision(BaseModel):
    decision: str
    confidence: Literal["low","medium","high"] = "medium"
    overall_score: Optional[float] = Field(default=None, ge=0, le=100)
    blocking_issue_ids: list[str] = Field(default_factory=list)
    resolved_issue_ids: list[str] = Field(default_factory=list)
    disputed_issue_ids: list[str] = Field(default_factory=list)
    priority_fixes: list[str] = Field(default_factory=list)
    rationale: str
