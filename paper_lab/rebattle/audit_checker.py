from __future__ import annotations
from collections import Counter, defaultdict
from .audit_rules import DIMENSION_WEIGHTS
from .audit_schemas import EvidenceAudit, ProblemIndex, ScoreSummary

class AuditConsistencyError(RuntimeError):
    pass

def compute_score(audit: EvidenceAudit) -> ScoreSummary:
    applicable = 0
    scored = 0
    weighted_points = 0.0
    for d in audit.dimensions:
        if d.status != 'not_applicable':
            applicable += d.weight
        if d.status not in ('not_applicable','unverifiable') and d.score is not None:
            scored += d.weight
            weighted_points += d.weight * (d.score / 4.0)
    coverage = (scored / applicable) if applicable else 0.0
    allowed = applicable > 0 and coverage >= 0.80
    normalized = (weighted_points / scored * 100.0) if allowed and scored else None
    return ScoreSummary(
        coverage_ratio=round(coverage, 4), scored_weight=scored,
        applicable_weight=applicable,
        normalized_score=round(normalized, 2) if normalized is not None else None,
        score_allowed=allowed,
        note='总分仅用于修改排序，不是官方竞赛分数或获奖概率。' if allowed else '可评分覆盖率低于80%，禁止输出总分。'
    )

def check_audit_consistency(index: ProblemIndex, audit: EvidenceAudit) -> dict:
    errors=[]; warnings=[]
    qids=[q.id for q in index.questions]
    if not qids: errors.append('problem_index 为空')
    if len(qids)!=len(set(qids)): errors.append('problem_index 存在重复小问 ID')

    rows=[r.subproblem_id for r in audit.matrix]
    if len(rows)!=len(set(rows)): errors.append('matrix 存在重复小问行')
    unknown=[x for x in rows if x not in set(qids)]
    if unknown: errors.append('matrix 含原题索引之外的小问: '+', '.join(unknown))
    missing_rows=[x for x in qids if x not in set(rows)]
    if missing_rows: errors.append('matrix 缺少原题小问: '+', '.join(missing_rows))

    eids=[e.id for e in audit.evidence]
    if len(eids)!=len(set(eids)): errors.append('evidence ID 重复')
    eset=set(eids)
    evidence_by_id={e.id:e for e in audit.evidence}

    for r in audit.matrix:
        refs=r.model_choice_evidence_ids+r.result_evidence_ids+r.validation_evidence_ids
        bad=[x for x in refs if x not in eset]
        if bad: errors.append(f'{r.subproblem_id} 引用了不存在的 evidence: {bad}')
        if r.status=='present' and not r.paper_locations:
            errors.append(f'{r.subproblem_id} status=present 但没有 paper_locations')

    expected=set(DIMENSION_WEIGHTS)
    names=[d.name for d in audit.dimensions]
    if set(names)!=expected or len(names)!=len(expected):
        errors.append('dimensions 必须恰好包含固定十二维且不得重复')
    for d in audit.dimensions:
        if d.name in DIMENSION_WEIGHTS and d.weight!=DIMENSION_WEIGHTS[d.name]:
            errors.append(f'{d.name} 权重应为 {DIMENSION_WEIGHTS[d.name]}，实际 {d.weight}')
        if d.status in ('not_applicable','unverifiable') and d.score is not None:
            errors.append(f'{d.name}: {d.status} 不得记分')
        if d.status=='missing' and d.score not in (0,None):
            errors.append(f'{d.name}: missing 应记 0 分')
        bad=[x for x in d.evidence_ids if x not in eset]
        if bad: errors.append(f'{d.name} 引用了不存在的 evidence: {bad}')
        if d.status=='present' and not d.evidence_ids:
            errors.append(f'{d.name}: present 维度没有证据')
        if d.status=='missing':
            globals_=[evidence_by_id[x] for x in d.evidence_ids if x in evidence_by_id and evidence_by_id[x].source_kind=='global_search' and evidence_by_id[x].status=='missing']
            if not globals_:
                errors.append(f'{d.name}: missing 维度缺少 global_search 缺失证据')
            elif not any(g.search_scope.strip() and g.search_terms for g in globals_):
                errors.append(f'{d.name}: 全局缺失证据必须记录 search_scope 和 search_terms')

    usage=defaultdict(list)
    for r in audit.matrix:
        for eid in set(r.model_choice_evidence_ids+r.result_evidence_ids+r.validation_evidence_ids):
            usage[eid].append(r)
    for eid, used in usage.items():
        if len(used)>1:
            for r in used:
                if not r.shared_evidence_rationale.strip():
                    errors.append(f'{eid} 跨小问复用，但 {r.subproblem_id} 未说明 shared_evidence_rationale')

    for i in audit.issues:
        bad=[x for x in i.evidence_ids if x not in eset]
        if bad: errors.append(f'audit issue {i.id or "(no id)"} 引用不存在的 evidence: {bad}')
        if i.severity in ('fatal','important'):
            if not i.location.strip(): errors.append(f'{i.id or "audit issue"} 缺 location')
            if not i.evidence_ids: errors.append(f'{i.id or "audit issue"} 缺 evidence_ids')
            if not i.impact.strip(): errors.append(f'{i.id or "audit issue"} 缺 impact')
            if not i.recommendation.strip(): errors.append(f'{i.id or "audit issue"} 缺 recommendation')
            if not i.completion_test.strip(): errors.append(f'{i.id or "audit issue"} 缺 completion_test')
        bad_q=[q for q in i.subproblem_ids if q not in set(qids)]
        if bad_q: errors.append(f'{i.id or "audit issue"} 引用了原题外小问: {bad_q}')

    if len(audit.priorities)>5: errors.append('priorities 最多 5 条')
    issue_ids={i.id for i in audit.issues if i.id}
    for p in audit.priorities:
        if p.issue_id not in issue_ids: errors.append(f'priority 引用了不存在的 issue {p.issue_id}')

    score=compute_score(audit)
    if audit.score_summary and audit.score_summary.normalized_score is not None and not score.score_allowed:
        errors.append('可评分覆盖率低于80%却输出了总分')
    return {'passed':not errors,'errors':errors,'warnings':warnings,'score_summary':score.model_dump()}
