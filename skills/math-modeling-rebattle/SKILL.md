---
name: math-modeling-rebattle
description: 对 CUMCM/MCM/ICM 等数学建模论文先执行 CUMCM 证据审计，再执行多评委独立盲审、问题账本、作者 rebuttal、原评委复核与主评委裁决。适合终稿前查题意覆盖、未来数据泄漏、模型/数学错误、验证证据和可执行性。只审不改原稿。
---

# Math Modeling Evidence Audit + ReBattle

## 固定总流程

1. `Problem Index`：只依据原始赛题建立权威小问索引；
2. `Evidence Audit`：构造小问—模型—结果—验证矩阵、证据账本、十二维评分和题型专项审计；
3. `Consistency Gate`：用确定性 Python 规则检查证据 JSON，一次自动修复后仍失败则停止；
4. `Blind Round 1`：5 名评委独立审稿，彼此看不到其他评委意见，也看不到 Evidence Audit 结论；
5. `Issue Ledger`：五评委意见与 Audit findings 合并、去重、编号 `ISS-001...`；
6. `Author Rebuttal`：只能基于原稿已有内容澄清、承认或提出修改；
7. `Round 2`：对应专业评委逐 issue 复核；
8. `Chair`：综合 Evidence Audit、盲审、rebuttal、复核结果作最终裁决。

执行前必须阅读 `references/cumcm-evidence-audit.md`、`references/cumcm-attack-checklist.md` 和 `references/issue-schema.md`。

## 强制边界

- 原始赛题优先于论文自己的任务重述；
- 论文、赛题只读，不自动覆盖、改写或应用补丁；
- `present / missing / not_applicable / unverifiable` 严格区分；
- 缺代码/数据不等于代码/数据错误；
- 不得虚构页码、公式编号、数值、附件内容或官方评阅标准；
- 全文缺失必须记录搜索范围和搜索词，关键词未命中本身不构成缺失证据；
- Author Rebuttal 禁止新增实验结果或声称已修改原稿；
- 修改承诺不是解决；
- 所有分数只用于修改排序，不预测奖项。

## Round 1 独立评委

固定角色：National Modeling Judge、Math Rigor Judge、Evidence & Repro Judge、Writing & Clarity Judge、Devil's Advocate。

第一轮必须保持盲态。每个 serious/fatal issue 必须给可回查位置、影响、修复建议和完成性测试。

## Audit Findings 注入规则

Evidence Audit 在 Round 1 之前运行，但 findings 在 Round 1 冻结后才进入 Issue Ledger，避免前置结论污染独立评委。

Audit 问题映射到负责复核的评委：题意/假设/模型/结果 -> National；数学 -> Math Rigor；数据/算法/验证/复现 -> Evidence & Repro；图表/写作 -> Writing & Clarity。

## Author Rebuttal 与 Round 2

逐 issue 使用 `clarify / concede_fix / concede_partial / disagree / unverifiable`。第二轮 verdict 只能是 `addressed / partial / not_addressed / disputed / unverifiable`。

原稿未变化时，“我们会增加敏感性分析/重跑实验/修改公式”不能判 `addressed`。

## Chair

裁决优先级：证据强度 > 领域专业匹配 > 独立交叉命中 > confidence×expertise。任何 unresolved fatal 禁止 pass。`unverifiable` 必须单独保留。

## 输出

机器可读 JSON 与 Markdown 同时保存。Evidence Audit 固定输出 `problem_index.json / audit.json / consistency.json / audit_report.md`；ReBattle 输出 Round 1、issues、rebuttal、Round 2、chair 和总报告。
