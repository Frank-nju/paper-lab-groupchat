from __future__ import annotations
import json
from pathlib import Path
from .audit_schemas import ProblemIndex, EvidenceAudit
from .audit_checker import check_audit_consistency, compute_score, AuditConsistencyError
from .audit_prompts import problem_index_prompt, evidence_audit_prompt, repair_audit_prompt
from .utils import dump_json

class EvidenceAuditRunner:
    def __init__(self, backend, model_key:str):
        self.backend=backend; self.model_key=model_key

    def run(self, *, paper:str, problem:str, out_dir:str|Path) -> tuple[ProblemIndex,EvidenceAudit,dict]:
        out=Path(out_dir); out.mkdir(parents=True, exist_ok=True)
        idx_raw=self.backend.complete(
            agent_name='problem_indexer', model_key=self.model_key,
            system_prompt='CUMCM original-problem indexer. Use only the original problem.',
            user_prompt=problem_index_prompt(problem))
        index=ProblemIndex.model_validate(idx_raw)
        dump_json(out/'problem_index.json', index.model_dump())

        audit_raw=self.backend.complete(
            agent_name='evidence_auditor', model_key=self.model_key,
            system_prompt='CUMCM evidence auditor. Evidence-first, conservative, no award prediction.',
            user_prompt=evidence_audit_prompt(problem,paper,index.model_dump()))
        try:
            audit=EvidenceAudit.model_validate(audit_raw)
            audit.score_summary=compute_score(audit)
            check=check_audit_consistency(index,audit)
        except Exception as exc:
            audit=None
            check={'passed':False,'errors':['schema validation failed: '+str(exc)],'warnings':[]}

        if not check['passed']:
            repaired_raw=self.backend.complete(
                agent_name='audit_repair', model_key=self.model_key,
                system_prompt='Repair only audit JSON consistency; do not invent evidence.',
                user_prompt=repair_audit_prompt(index.model_dump(), audit.model_dump(exclude={'score_summary'}) if audit is not None else audit_raw, check['errors']))
            audit=EvidenceAudit.model_validate(repaired_raw)
            audit.score_summary=compute_score(audit)
            check=check_audit_consistency(index,audit)

        dump_json(out/'audit.json',audit.model_dump())
        dump_json(out/'consistency.json',check)
        self._report(out,index,audit,check)
        if not check['passed']:
            raise AuditConsistencyError('CUMCM evidence audit consistency gate failed: '+'; '.join(check['errors']))
        return index,audit,check

    def _report(self,out,index,audit,check):
        s=audit.score_summary
        lines=['# CUMCM Evidence Audit','',
               '> 本审计用于论文修改排序，不是官方竞赛评分或获奖概率。','',
               '## 小问—模型—结果—验证矩阵','']
        lines.append('| 小问 | 状态 | 模型 | 论文位置 | 结果证据 | 验证证据 |')
        lines.append('|---|---|---|---|---|---|')
        for r in audit.matrix:
            lines.append(f'| {r.subproblem_id} | {r.status} | {"; ".join(r.models) or "—"} | {"; ".join(r.paper_locations) or "—"} | {", ".join(r.result_evidence_ids) or "—"} | {", ".join(r.validation_evidence_ids) or "—"} |')
        lines += ['','## 十二维评分','', '| 维度 | 权重 | 状态 | 0–4 | 置信度 |','|---|---:|---|---:|---|']
        for d in audit.dimensions:
            score='—' if d.score is None else str(d.score)
            lines.append(f'| {d.name} | {d.weight} | {d.status} | {score} | {d.confidence} |')
        if s:
            lines += ['',f'- 可评分覆盖率：{s.coverage_ratio:.1%}（{s.scored_weight}/{s.applicable_weight} 权重）']
            lines.append(f'- 内部归一分：{s.normalized_score:.2f}/100' if s.normalized_score is not None else '- 内部归一分：**不输出**（覆盖率不足 80%）')
        lines += ['','## 审计问题','']
        for i in audit.issues:
            lines += [f'### {i.id} · {i.severity} · {i.dimension}',i.judgment,'',f'- 事实：{i.fact}',f'- 位置：{i.location}',f'- 影响：{i.impact}',f'- 修改：{i.recommendation}',f'- 完成标准：{i.completion_test}','']
        if audit.unverifiable_items:
            lines += ['## 无法核验','']+[f'- {x}' for x in audit.unverifiable_items]+['']
        lines += ['## 一致性门禁','',f'- Passed: {check["passed"]}']
        for e in check['errors']: lines.append(f'- ERROR: {e}')
        (out/'audit_report.md').write_text('\n'.join(lines),encoding='utf-8')

def audit_issues_to_rebattle_seeds(audit: EvidenceAudit):
    from .schemas import Issue, Evidence
    severity_map={'fatal':'fatal','important':'serious','general':'moderate','polish':'minor'}
    judge_map={
        '任务理解与覆盖':'national_modeling_judge',
        '问题抽象与假设':'national_modeling_judge',
        '数据处理质量':'evidence_repro_judge',
        '模型选择与适配':'national_modeling_judge',
        '模型链与衔接':'national_modeling_judge',
        '数学表达与推导':'math_rigor_judge',
        '算法与求解':'evidence_repro_judge',
        '验证与稳健性':'evidence_repro_judge',
        '结果与可执行性':'national_modeling_judge',
        '图表证据':'writing_clarity_judge',
        '正文写作与论证':'writing_clarity_judge',
        '可复现性与规范':'evidence_repro_judge',
    }
    category_map={
        '任务理解与覆盖':'task_coverage','问题抽象与假设':'assumptions','数据处理质量':'data',
        '模型选择与适配':'model_selection','模型链与衔接':'model_chain','数学表达与推导':'math',
        '算法与求解':'solver','验证与稳健性':'validation','结果与可执行性':'results',
        '图表证据':'figures','正文写作与论证':'writing','可复现性与规范':'reproducibility',
    }
    conf={'high':.9,'medium':.7,'low':.45}
    by_id={e.id:e for e in audit.evidence}
    seeds=[]
    for a in audit.issues:
        ev=[]
        for eid in a.evidence_ids:
            x=by_id.get(eid)
            if not x: continue
            ev.append(Evidence(
                evidence_id=x.id, source_kind=x.source_kind, location=x.location,
                claim_type=x.claim_type, status=x.status,
                excerpt_or_description=x.excerpt_or_description,
                confidence=conf[x.confidence], search_scope=x.search_scope, search_terms=x.search_terms))
        detail='事实：'+a.fact+'\n判断：'+a.judgment
        if a.inference: detail+='\n推断：'+a.inference
        seeds.append(Issue(
            summary=a.judgment[:180], detail=detail, severity=severity_map[a.severity],
            category=category_map.get(a.dimension,'evidence_audit'),
            raised_by=[judge_map.get(a.dimension,'evidence_repro_judge')],
            origin=['cumcm_evidence_audit'], question_refs=a.subproblem_ids,
            evidence=ev, impact=a.impact, suggested_fix=a.recommendation,
            completion_test=a.completion_test, status='open'))
    return seeds
