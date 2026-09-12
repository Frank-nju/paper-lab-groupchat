from __future__ import annotations
import json
from pathlib import Path
from .schemas import Review, Rebuttal, ReReview, ChairDecision
from .ledger import build_issue_ledger
from .prompts import JUDGE_PROFILES, judge_prompt, rebuttal_prompt, rereview_prompt, chair_prompt
from .utils import dump_json
from .audit import EvidenceAuditRunner, audit_issues_to_rebattle_seeds

class ReBattleEngine:
    def __init__(self, backend, model_map:dict, difficulty='strict'):
        self.backend=backend; self.model_map=model_map; self.difficulty=difficulty

    def run(self, paper:str, problem:str, out_dir:str):
        out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)

        # CUMCM Evidence Audit is a hard preflight gate before any reviewer battle.
        audit_model=self.model_map.get('audit_model', self.model_map['chair_model'])
        problem_index,audit,audit_check=EvidenceAuditRunner(self.backend,audit_model).run(
            paper=paper, problem=problem, out_dir=out/'evidence_audit')
        audit_seed_issues=audit_issues_to_rebattle_seeds(audit)

        reviews=[]
        # Blind round: prompts contain only paper/problem, never other judge outputs or audit findings.
        for jt in JUDGE_PROFILES:
            raw=self.backend.complete(agent_name='r1_'+jt, model_key=self.model_map['judges'][jt],
                system_prompt=JUDGE_PROFILES[jt], user_prompt=judge_prompt(jt,paper,problem,self.difficulty))
            raw['judge_type']=jt
            review=Review.model_validate(raw); reviews.append(review)
            dump_json(out/'round1'/f'{jt}.json', review.model_dump())

        # Only after all blind reviews are frozen do audit findings join the issue ledger.
        issues=build_issue_ledger(reviews, seed_issues=audit_seed_issues)
        dump_json(out/'issues.json', [x.model_dump() for x in issues])
        issues_json=json.dumps([x.model_dump() for x in issues],ensure_ascii=False)

        rb_raw=self.backend.complete(agent_name='author_rebuttal', model_key=self.model_map['rebuttal_model'],
            system_prompt='Author rebuttal simulator; read-only.', user_prompt=rebuttal_prompt(paper,problem,issues_json))
        rebuttal=Rebuttal.model_validate(rb_raw)
        dump_json(out/'rebuttal.json', rebuttal.model_dump())

        rereviews=[]
        for jt in JUDGE_PROFILES:
            assigned=[x.model_dump() for x in issues if jt in x.raised_by]
            raw=self.backend.complete(agent_name='r2_'+jt, model_key=self.model_map['judges'][jt],
                system_prompt=JUDGE_PROFILES[jt], user_prompt=rereview_prompt(jt,paper,problem,json.dumps(assigned,ensure_ascii=False),json.dumps(rebuttal.model_dump(),ensure_ascii=False)))
            raw['judge_type']=jt
            rr=ReReview.model_validate(raw); rereviews.append(rr)
            dump_json(out/'round2'/f'{jt}.json', rr.model_dump())

        audit_for_chair={
            'score_summary': audit.score_summary.model_dump() if audit.score_summary else None,
            'dimensions':[d.model_dump() for d in audit.dimensions],
            'audit_issues':[i.model_dump() for i in audit.issues],
            'consistency_gate':audit_check,
        }
        chair_raw=self.backend.complete(agent_name='chair_judge', model_key=self.model_map['chair_model'],
            system_prompt='Chief mathematical-modeling judge.',
            user_prompt=chair_prompt(json.dumps([r.model_dump() for r in reviews],ensure_ascii=False),issues_json,json.dumps(rebuttal.model_dump(),ensure_ascii=False),json.dumps([r.model_dump() for r in rereviews],ensure_ascii=False),json.dumps(audit_for_chair,ensure_ascii=False)))
        chair=ChairDecision.model_validate(chair_raw)
        dump_json(out/'chair_decision.json', chair.model_dump())
        self._report(out,reviews,issues,rebuttal,rereviews,chair,audit)
        return chair

    def _report(self,out,reviews,issues,rebuttal,rereviews,chair,audit):
        lines=['# Math Modeling ReBattle Report','',f'**Decision:** {chair.decision}',f'**Confidence:** {chair.confidence}',f'**Chair internal score:** {chair.overall_score}','', '> 所有分数仅用于修改排序，不是官方 CUMCM 评分或获奖概率。','']
        s=audit.score_summary
        lines += ['## CUMCM Evidence Audit gate']
        if s:
            lines.append(f'- Evidence coverage: {s.coverage_ratio:.1%} ({s.scored_weight}/{s.applicable_weight} weight)')
            lines.append(f'- 12D normalized score: {s.normalized_score:.2f}/100' if s.normalized_score is not None else '- 12D normalized score: not emitted (coverage < 80%)')
        lines.append('- Full audit: `evidence_audit/audit_report.md`')
        lines += ['', '## Blocking issues']
        if not chair.blocking_issue_ids: lines.append('- None')
        for iid in chair.blocking_issue_ids:
            x=next((i for i in issues if i.id==iid),None)
            lines.append(f'- **{iid}** [{x.severity if x else "?"}] {x.summary if x else ""}')
        lines += ['', '## Issue ledger']
        for x in issues:
            lines += [f'### {x.id} · {x.severity} · {x.category}',x.summary,'',f'- Origin: {", ".join(x.origin)}',f'- Raised/verified by: {", ".join(x.raised_by)}',f'- Impact: {x.impact}',f'- Fix: {x.suggested_fix}',f'- Completion test: {x.completion_test}','']
        lines += ['## Chair rationale','',chair.rationale,'','## Priority fixes']
        lines += [f'{i}. {v}' for i,v in enumerate(chair.priority_fixes,1)]
        (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
