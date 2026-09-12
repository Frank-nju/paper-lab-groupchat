# 两条并行路线

本项目保留两种可以独立使用的工作方式。两条路线共用本地证据包、CUMCM 评审知识库和低价模型的质量控制规则。

## 路线 A：本地证据包 + 审批式群聊

先在本机只读解析赛题、论文和附件：

```powershell
py -3 -m paper_lab.pack_cli `
  --problem data\problem_statement.pdf `
  --paper data\candidate_paper.pdf `
  --attachment "E:\path\to\attachments.zip" `
  --out outputs\evidence_packs\case01
```

只有 `quality.gate=true` 才能启动证据包群聊：

```powershell
py -3 -m paper_lab.evidence_cli --offline `
  --evidence-pack outputs\evidence_packs\case01
```

证据包会保留：

- 原始文件 SHA-256、文件格式和来源 URI；
- 赛题页级文本、准确的小问索引和字符定位；
- 论文页级文本、证据片段、页码、图表/公式锚点；
- Excel/CSV/JSON/NPY/NPZ 的结构、行列、缺失、数值范围和样例摘要；
- 每个 Q 的问题包。全量附件清单留在本地，小问包只取相关摘要，避免重复占满模型上下文。

任何扫描页、未解析附件或无法识别小问都会阻断 gate，不会让模型在缺证据的情况下继续审计。

## 路线 B：高级模型留在原生 Agent，人工传话

准备两份独立提示：

```powershell
py -3 -m paper_lab.relay_cli prepare `
  --evidence-pack outputs\evidence_packs\case01 `
  --out outputs\native_relay\case01
```

把 `prompts\GPT6.md` 和 `prompts\Fable51.md` 分别交给两个原生 Agent。把它们的完整回复保存为文本后提交：

```powershell
py -3 -m paper_lab.relay_cli submit --out outputs\native_relay\case01 --role GPT6 --file gpt6.md
py -3 -m paper_lab.relay_cli submit --out outputs\native_relay\case01 --role Fable51 --file fable51.md
py -3 -m paper_lab.relay_cli assemble --out outputs\native_relay\case01
```

最后的 `worker_packet.md` 只交给廉价模型执行 Issue Ledger、证据状态、返工动作和完成性测试；它不能修改原稿，也不能把高级模型的意见直接判成已解决。人工仍负责审批、打回廉价模型或提交人工返工。

## 质量边界

证据包是只读派生物，不会修改原始赛题、附件或论文。`question_packs/` 是模型上下文，`attachment_manifest.json` 和页级 JSONL 是完整审计底稿；如果模型需要更多内容，应依据 `source_id`、`evidence_id` 和页码回查本地文件，而不是让模型凭记忆补全。

