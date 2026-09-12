# paper-lab-groupchat

这是迁移到 Windows 本机的数学建模论文评审群聊，底层使用 AG2 0.9.10；附件中的 `math-modeling-rebattle` 已作为高级模型知识库和独立 Evidence Audit 模块融合进来。

## 新的审批式轮次

每一轮不再限制“一人一句”，固定流程是：

```text
GPT-6        独立观点 1
Fable 5.1   独立观点 1
GPT-6        阅读 Fable 后综合观点 2
Fable 5.1   阅读 GPT-6 后综合观点 2
廉价模型     读取以上四条，执行证据审计、Issue Ledger 和返工清单
人工         审批 / 打回廉价模型 / 要求人工返工
```

GPT-6 和 Fable 5.1 仍然完全对等；第一条消息互相隔离，第二条消息互读吸收。高级模型接收：

- 原题唯一小问索引原则；
- CUMCM 四态证据：`present / missing / not_applicable / unverifiable`；
- 小问—模型—结果—验证矩阵；
- 十二维评分与 80% 可评分覆盖率门槛；
- 未来数据泄露、状态守恒、信息时序、硬约束、baseline、敏感性和极端情景攻击清单；
- Issue 必须包含位置、影响、修改方案和完成性测试。

知识库位于 `skills/math-modeling-rebattle/`，只作为审查原则使用，原稿和赛题仍然只读。

## 审批与返工

程序在每轮廉价模型输出后停在 `awaiting_approval`，不会自动进入下一轮：

```text
/approve                         审批当前轮
/next                            审批后开始下一轮
/return cheap 补充完成性测试       只让廉价模型重做
/return human 先补充证据           进入人工返工
/submit human 我已补充……           提交人工返工结果，重新等待审批
/status                          查看状态
```

高级模型不会被单独打回；若需要重新讨论，应审批后启动下一轮。所有轮次、返工前版本和审批状态写入 `outputs/round_sessions/`。

## Windows 使用

```powershell
cd E:\CUMCM2026Problems\C题\paper-lab-groupchat
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\run_windows.ps1
```

没有完整 API Key 时自动使用离线演示；也可以直接执行：

```powershell
.\.venv\Scripts\python.exe main.py --offline --interactive
```

## 本地浏览器群聊

想要使用聊天式界面，可以启动本地网页服务：

```powershell
py -3 -m paper_lab.web --offline --port 8765 `
  --paper data\candidate_paper.pdf `
  --problem data\problem_statement.pdf
```

打开 <http://127.0.0.1:8765>。网页显示 GPT6、Fable51、廉价模型和人工消息，并提供开始第一轮、审批、下一轮、廉价模型返工和人工返工按钮。所有内容仍然写入 `outputs/round_sessions/`，不会覆盖论文原稿。

已有证据包时，可以使用：

```powershell
py -3 -m paper_lab.web --offline `
  --evidence-pack outputs\evidence_packs\<case> `
  --problem data\problem_statement.pdf
```

网页详细说明见 [`docs/web-ui.md`](docs/web-ui.md)。

## Linux/macOS 使用

```bash
cd paper-lab-groupchat
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
chmod +x run_linux.sh
./run_linux.sh
```

脚本用项目自身目录解析路径，不依赖 Linux `/` 或 Windows 盘符。

## CUMCM Evidence Audit / 完整 ReBattle

附件里的确定性审计和完整 ReBattle 已放在 `paper_lab/rebattle/`，配置模板是 `config.rebattle.example.yaml`。

只跑证据审计：

```powershell
py -3 -m paper_lab.rebattle.cli --mock `
  --audit-only `
  --paper data/candidate_paper.pdf `
  --problem data/problem_statement.pdf `
  --config config.rebattle.example.yaml `
  --out outputs/runs/audit01
```

它会输出原题索引、证据矩阵、十二维审计、`consistency.json` 和报告；Consistency Gate 不通过时不会继续。

## 文件边界

- `data/`：论文与赛题，只读输入。
- `skills/math-modeling-rebattle/`：高级模型知识库。
- `paper_lab/rebattle/`：Evidence Audit、Issue Ledger 和完整 ReBattle 模块。
- `outputs/round_sessions/`：审批式轮次、返工历史和 JSONL/Markdown 记录。
- `main.py.legacy` 与 `*.before-*.bak`：迁移前入口/文档的可恢复备份。

## 验证

```powershell
py -3 -m pytest
```

测试覆盖双阶段消息顺序、审批门禁、定向返工、知识库加载、Evidence Audit、Consistency Gate、Issue Ledger 和本地网页 API 状态机；测试不调用真实 API。
