# 本地网页群聊

网页界面是一个只监听本机的轻量浏览器入口，不需要单独安装前端框架。它复用终端入口的审批状态机：GPT6 和 Fable51 先独立发言，再互读综合；廉价模型读取四条消息后执行；人工审批前不能进入下一轮。

## 启动

在项目目录执行：

```powershell
cd E:\CUMCM2026Problems\C题\paper-lab-groupchat
py -3 -m paper_lab.web --offline --port 8765 `
  --paper data\candidate_paper.pdf `
  --problem data\problem_statement.pdf
```

然后打开：<http://127.0.0.1:8765>

没有 API Key 时也可以使用 `--offline` 演示完整状态机。配置好 `.env` 后，去掉 `--offline` 即可尝试在线运行；如果三组 Key 不完整，程序会自动回退到离线模式。

## 使用已通过门禁的证据包

证据包不会上传到公开仓库，但可以在本机直接使用：

```powershell
py -3 -m paper_lab.web --offline `
  --evidence-pack outputs\evidence_packs\c_case_20260912_v6 `
  --problem data\problem_statement.pdf
```

证据包质量门禁未通过时，网页服务会拒绝启动，避免把不完整的预处理结果伪装成完整论文上下文。

## 页面操作

- **开始第一轮**：创建本地会话并生成四条高级模型消息与一条廉价模型消息。
- **通过当前轮**：仅改变审批状态，不会修改论文原稿。
- **审批后开始下一轮**：只有通过后才能点击。
- **只重做廉价模型**：保留四条高级消息，廉价模型重新执行。
- **进入人工返工 / 提交人工结果**：在网页中完成一次人工返工后重新等待审批。

所有消息和审批状态仍然写入 `outputs\round_sessions\`，论文与赛题保持只读。
