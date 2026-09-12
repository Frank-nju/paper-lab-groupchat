from __future__ import annotations
import os, json, hashlib
from typing import Any
from .utils import extract_json

class Backend:
    def complete(self, *, agent_name:str, model_key:str, system_prompt:str, user_prompt:str) -> dict:
        raise NotImplementedError

class MockBackend(Backend):
    """Deterministic offline backend for workflow tests; not a semantic paper reviewer."""
    def complete(self, *, agent_name, model_key, system_prompt, user_prompt):
        if agent_name=='problem_indexer':
            return {"questions":[{"id":"Q1","label":"问题一","requirement":"完成示例建模任务","required_outputs":["结果"],"constraints":["满足题设约束"],"evaluation_criteria":["结果可核验"],"source_location":"原始赛题：问题一"}],"notes":[],"confidence":"high"}
        if agent_name=='evidence_auditor':
            from .audit_rules import DIMENSION_WEIGHTS
            dims=[]
            for name,w in DIMENSION_WEIGHTS.items():
                dims.append({"name":name,"weight":w,"status":"present","score":3,"reason":"mock evidence supports a mostly complete dimension","why_not_next_level":"mock does not demonstrate a full boundary-tested closure","evidence_ids":["E001"],"confidence":"high"})
            return {
                "scope":{"performed":["full-text evidence audit","question mapping","12-dimension review"],"excluded":[],"confidence":"high","confidence_reason":"deterministic mock"},
                "matrix":[{"subproblem_id":"Q1","requirement":"完成示例建模任务","paper_locations":["全文示例"],"models":["mock model"],"model_choice_evidence_ids":["E001"],"result_evidence_ids":["E001"],"validation_evidence_ids":["E001"],"status":"present","shared_evidence_rationale":"","confidence":"high"}],
                "evidence":[{"id":"E001","claim_type":"fact","source_kind":"paper_text","location":"全文示例","excerpt_or_description":"mock evidence","supports":"结构与结果存在","status":"present","confidence":"high","search_scope":"","search_terms":[]}],
                "dimensions":dims,
                "problem_type_review":[{"subproblem_id":"Q1","primary_type":"其他综合题","secondary_types":[],"mandatory_checks":["约束"],"required_validation":["基线","可行性"],"executable_output":["结果"],"not_applicable_items":[],"evidence_ids":["E001"],"confidence":"medium"}],
                "strengths":["示例结构完整"],
                "issues":[{"id":"A-I01","severity":"important","dimension":"验证与稳健性","subproblem_ids":["Q1"],"evidence_ids":["E001"],"location":"全文示例","fact":"mock 仅有基础验证描述","judgment":"核心假设需要更明确验证","inference":"稳健性不足可能影响结论可信度","impact":"可能影响主要结论可信度","recommendation":"增加假设依据和检验","completion_test":"给出可回查的基线/敏感性证据","confidence":"high"}],
                "priorities":[{"rank":1,"issue_id":"A-I01","action":"补验证","benefit":"提升可信度","completion_test":"出现可回查验证证据"}],
                "unverifiable_items":[],"known_limitations":["mock backend不执行真实语义审稿"]}
        if agent_name=='audit_repair':
            raise AssertionError('valid mock audit should not require repair')
        if agent_name.startswith('r1_'):
            jt=agent_name[3:]
            sev='serious' if jt in ('national_modeling_judge','devil_advocate_judge') else 'moderate'
            return {"judge_type":jt,"score":72,"confidence":4,"expertise":4,"strengths":["结构完整"],
                    "question_coverage":{"问题一":"covered"},"issues":[{"summary":"核心假设需要更明确验证","detail":"离线 smoke test 生成的示例问题。","severity":sev,"category":"methods","raised_by":[jt],"question_refs":["问题一"],"evidence":[{"location":"global","claim_type":"judgment","status":"present","excerpt_or_description":"mock","confidence":.8}],"impact":"可能影响主要结论可信度","suggested_fix":"增加假设依据和检验","completion_test":"给出可回查证据"}],"recommendation":"revise"}
        if agent_name=='author_rebuttal':
            import re
            ids=re.findall(r'ISS-\d{3}',user_prompt)
            ids=list(dict.fromkeys(ids))
            return {"summary":"承认需要补强证据。","responses":[{"issue_id":i,"stance":"concede_fix","response":"该问题成立，将在修订稿补强论证。","cited_locations":[],"promised_revision":"补充证据"} for i in ids]}
        if agent_name.startswith('r2_'):
            jt=agent_name[3:]
            import re
            ids=list(dict.fromkeys(re.findall(r'ISS-\d{3}',user_prompt)))
            return {"judge_type":jt,"issue_verdicts":[{"issue_id":i,"verdict":"not_addressed","rationale":"原稿尚未实际修改。","evidence_locations":[]} for i in ids],"recommendation_after_rebuttal":"revise"}
        if agent_name=='chair_judge':
            import re
            ids=list(dict.fromkeys(re.findall(r'ISS-\d{3}',user_prompt)))
            return {"decision":"major_revise","confidence":"high","overall_score":72,"blocking_issue_ids":ids[:3],"resolved_issue_ids":[],"disputed_issue_ids":[],"priority_fixes":["先关闭 serious/fatal issues"],"rationale":"离线 smoke test：承诺修改不等于原稿已解决。"}
        raise ValueError(agent_name)

class AG2Backend(Backend):
    def __init__(self, model_cfgs: dict[str,dict[str,Any]]):
        try:
            from autogen import ConversableAgent
        except Exception as e:
            raise RuntimeError('AG2 not installed. pip install -r requirements.txt') from e
        self.ConversableAgent=ConversableAgent
        self.model_cfgs=model_cfgs
        self.agents={}

    def _llm_config(self, key):
        c=self.model_cfgs[key]
        api_key=os.getenv(c.get('api_key_env',''), '')
        base_url=os.getenv(c.get('base_url_env',''), '')
        item={"model":c['model'],"api_key":api_key}
        if base_url: item['base_url']=base_url
        return {"config_list":[item],"temperature":c.get('temperature',0.1),"cache_seed":None}

    def complete(self, *, agent_name, model_key, system_prompt, user_prompt):
        key=(agent_name,model_key,hash(system_prompt))
        agent=self.agents.get(key)
        if agent is None:
            agent=self.ConversableAgent(name=agent_name, system_message=system_prompt,
                llm_config=self._llm_config(model_key), human_input_mode='NEVER',
                code_execution_config=False)
            self.agents[key]=agent
        reply=agent.generate_reply(messages=[{"role":"user","content":user_prompt}])
        if isinstance(reply, dict): reply=reply.get('content', reply)
        return extract_json(reply)
