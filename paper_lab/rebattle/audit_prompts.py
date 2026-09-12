import json
from .audit_rules import DIMENSION_WEIGHTS, DIMENSION_GUIDANCE, SCORE_ANCHORS, PROBLEM_TYPES

INDEX_SCHEMA = r'''{
  "questions":[{
    "id":"Q1","label":"问题一","requirement":"...",
    "required_outputs":["..."],"constraints":["..."],"evaluation_criteria":["..."],
    "source_location":"原始赛题中的可回查位置/标题/原句附近"
  }],
  "notes":["..."],"confidence":"high/medium/low"
}'''

def problem_index_prompt(problem:str) -> str:
    return f'''你是 CUMCM 原始赛题索引员。你的唯一任务是从【原始赛题】建立权威小问索引。
硬规则：
1. 原题是唯一主索引；不要根据论文、模型编号、附件编号、图表或代码推断额外小问。
2. 保留原题顺序；ID 用 Q1/Q2/...，label 尽量保留“问题一”等原表述。
3. 每问提取 requirement、required_outputs、constraints、evaluation_criteria。
4. source_location 只能写原题中真实可回查的位置；若输入没有页码，不得虚构页码，可写“问题二首段”等。
5. 不能确定的约束放 notes，并降低 confidence，不要猜。
6. 输出严格 JSON。

【原始赛题】
{problem}

输出结构：
{INDEX_SCHEMA}'''

AUDIT_SCHEMA = r'''{
  "scope":{"performed":["..."],"excluded":["..."],"confidence":"high","confidence_reason":"..."},
  "matrix":[{
    "subproblem_id":"Q1","requirement":"...","paper_locations":["..."],"models":["..."],
    "model_choice_evidence_ids":["E001"],"result_evidence_ids":["E002"],"validation_evidence_ids":["E003"],
    "status":"present/missing/not_applicable/unverifiable","shared_evidence_rationale":"","confidence":"high/medium/low"
  }],
  "evidence":[{
    "id":"E001","claim_type":"fact/judgment/inference","source_kind":"problem/paper_text/formula/figure/table/appendix/code/data/prior_report/global_search",
    "location":"真实可回查位置或 global","excerpt_or_description":"短摘录或忠实描述","supports":"支持什么判断",
    "status":"present/missing/not_applicable/unverifiable","confidence":"high/medium/low",
    "search_scope":"仅 global_search 缺失证据填写","search_terms":["仅 global_search 缺失证据填写"]
  }],
  "dimensions":[{
    "name":"任务理解与覆盖","weight":10,"status":"present/missing/not_applicable/unverifiable","score":0,
    "reason":"...","why_not_next_level":"...","evidence_ids":["E001"],"confidence":"high/medium/low"
  }],
  "problem_type_review":[{
    "subproblem_id":"Q1","primary_type":"...","secondary_types":[],"mandatory_checks":["..."],
    "required_validation":["..."],"executable_output":["..."],"not_applicable_items":[],"evidence_ids":["E..."],"confidence":"medium"
  }],
  "strengths":["..."],
  "issues":[{
    "id":"A-I01","severity":"fatal/important/general/polish","dimension":"...","subproblem_ids":["Q1"],
    "evidence_ids":["E..."],"location":"...","fact":"...","judgment":"...","inference":"...",
    "impact":"...","recommendation":"...","completion_test":"...","confidence":"high/medium/low"
  }],
  "priorities":[{"rank":1,"issue_id":"A-I01","action":"...","benefit":"...","completion_test":"..."}],
  "unverifiable_items":["..."],"known_limitations":["..."]
}'''

def evidence_audit_prompt(problem:str, paper:str, problem_index:dict) -> str:
    dims='\n'.join(f'- {k}（{w}）: {DIMENSION_GUIDANCE[k]}' for k,w in DIMENSION_WEIGHTS.items())
    ptypes=' / '.join(PROBLEM_TYPES)
    return f'''你是 CUMCM 数学建模论文的证据审计员。你在 ReBattle 前执行结构化 Evidence Audit，不做奖项预测。

【不可违反的证据政策】
- 每个检查项只能是 present / missing / not_applicable / unverifiable。
- 搜索没命中不等于 missing。全文缺失必须检查预期章节、对应小问、摘要、结论、附录，并记录 search_scope 与同义搜索词 search_terms。
- 缺代码/数据、公式不可读、图表不可读时应标 unverifiable，不能据此判错或记 0。
- 原题是唯一小问索引；matrix 必须且只能覆盖给定 problem_index。
- 跨小问复用同一 evidence_id 时，每个相关 matrix 行都要解释 shared_evidence_rationale。
- 证据 location 必须真实可回查。输入无页码时不得虚构页码，可用章节标题、公式附近文字、表/图标题、全文范围。
- 验证必须形成“对象 + 基准/真值/约束 + 指标 + 结果 + 对结论影响”的链；收敛图、拟合图、随机模拟、作者自评单独出现都不够。
- serious/fatal 等价的重大问题在 audit 中分别用 important/fatal，必须给 evidence、location、impact、recommendation、completion_test。
- score 只用 0..4 锚点：{SCORE_ANCHORS}
- not_applicable/unverifiable 的 score 必须为 null；missing 通常为 0。
- 不要计算总分；程序会依据 80% 可评分覆盖率规则确定是否允许总分。

【固定十二维及权重】
{dims}

【题型分类候选】
{ptypes}

【原始赛题】
{problem}

【权威小问索引】
{json.dumps(problem_index, ensure_ascii=False)}

【待审论文】
{paper}

输出严格 JSON，结构如下：
{AUDIT_SCHEMA}'''

def repair_audit_prompt(problem_index:dict, raw_audit:dict, errors:list[str]) -> str:
    fixed_dims=json.dumps(DIMENSION_WEIGHTS, ensure_ascii=False)
    return f'''你是证据审计 JSON 修复器。不得新增论文中不存在的事实，只修复结构/一致性问题。
必须保持原始审计的实质判断，除非错误本身证明该字段自相矛盾。
尤其注意：missing 全局缺失证据必须有 global_search + search_scope + search_terms；unverifiable/not_applicable 不得记分；十二维名称和权重必须固定；matrix 只能覆盖 problem_index。
输出完整、严格 JSON，不要解释。

PROBLEM_INDEX={json.dumps(problem_index, ensure_ascii=False)}
ERRORS={json.dumps(errors, ensure_ascii=False)}
FIXED_DIMENSIONS_AND_WEIGHTS={fixed_dims}
RAW_AUDIT={json.dumps(raw_audit, ensure_ascii=False)}
'''
