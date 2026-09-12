from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field

EvidenceStatus = Literal['present','missing','not_applicable','unverifiable']
Confidence = Literal['high','medium','low']

class ProblemIndexItem(BaseModel):
    id: str
    label: str
    requirement: str
    required_outputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    evaluation_criteria: list[str] = Field(default_factory=list)
    source_location: str

class ProblemIndex(BaseModel):
    questions: list[ProblemIndexItem]
    notes: list[str] = Field(default_factory=list)
    confidence: Confidence = 'high'

class AuditEvidence(BaseModel):
    id: str
    claim_type: Literal['fact','judgment','inference']
    source_kind: Literal['problem','paper_text','formula','figure','table','appendix','code','data','prior_report','global_search']
    location: str
    excerpt_or_description: str = ''
    supports: str
    status: EvidenceStatus
    confidence: Confidence = 'medium'
    search_scope: str = ''
    search_terms: list[str] = Field(default_factory=list)

class MatrixRow(BaseModel):
    subproblem_id: str
    requirement: str
    paper_locations: list[str] = Field(default_factory=list)
    models: list[str] = Field(default_factory=list)
    model_choice_evidence_ids: list[str] = Field(default_factory=list)
    result_evidence_ids: list[str] = Field(default_factory=list)
    validation_evidence_ids: list[str] = Field(default_factory=list)
    status: EvidenceStatus
    shared_evidence_rationale: str = ''
    confidence: Confidence = 'medium'

class DimensionRating(BaseModel):
    name: str
    weight: int
    status: EvidenceStatus
    score: Optional[int] = Field(default=None, ge=0, le=4)
    reason: str
    why_not_next_level: str = ''
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = 'medium'

class ProblemTypeReview(BaseModel):
    subproblem_id: str
    primary_type: str
    secondary_types: list[str] = Field(default_factory=list)
    mandatory_checks: list[str] = Field(default_factory=list)
    required_validation: list[str] = Field(default_factory=list)
    executable_output: list[str] = Field(default_factory=list)
    not_applicable_items: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    confidence: Confidence = 'medium'

class AuditIssue(BaseModel):
    id: str = ''
    severity: Literal['fatal','important','general','polish']
    dimension: str
    subproblem_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    location: str
    fact: str
    judgment: str
    inference: str = ''
    impact: str
    recommendation: str
    completion_test: str
    confidence: Confidence = 'medium'

class PriorityItem(BaseModel):
    rank: int = Field(ge=1, le=5)
    issue_id: str
    action: str
    benefit: str
    completion_test: str

class AuditScope(BaseModel):
    performed: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    confidence: Confidence = 'medium'
    confidence_reason: str = ''

class ScoreSummary(BaseModel):
    coverage_ratio: float = Field(ge=0, le=1)
    scored_weight: int = 0
    applicable_weight: int = 0
    normalized_score: Optional[float] = Field(default=None, ge=0, le=100)
    score_allowed: bool = False
    note: str = ''

class EvidenceAudit(BaseModel):
    scope: AuditScope
    matrix: list[MatrixRow]
    evidence: list[AuditEvidence]
    dimensions: list[DimensionRating]
    problem_type_review: list[ProblemTypeReview] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    issues: list[AuditIssue] = Field(default_factory=list)
    priorities: list[PriorityItem] = Field(default_factory=list)
    unverifiable_items: list[str] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)
    score_summary: Optional[ScoreSummary] = None
