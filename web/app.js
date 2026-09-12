const state = { lastJson: "", timer: null };

const $ = (id) => document.getElementById(id);
const labels = {
  idle: "空闲",
  awaiting_approval: "等待审批",
  approved: "已审批",
  human_rework_required: "等待人工返工",
};
const stageLabels = {
  independent: "独立观点",
  synthesis: "阅读后综合",
  execution: "质量控制执行",
  worker_rework: "廉价模型返工",
  human_rework: "人工返工",
};

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `请求失败（${response.status}）`);
  return data;
}

function statusText(status) { return labels[status] || status || "空闲"; }

function showToast(message = "") {
  $("toast").textContent = message;
  if (message) window.setTimeout(() => { if ($("toast").textContent === message) $("toast").textContent = ""; }, 5000);
}

function setBusy(busy) {
  document.querySelectorAll("button").forEach((button) => { button.disabled = busy; });
}

function renderMessage(message) {
  const article = document.createElement("article");
  const speakerClass = String(message.speaker || "").toLowerCase().replace(/[^a-z0-9]/g, "");
  article.className = `message ${speakerClass}`;
  const meta = document.createElement("div");
  meta.className = "message-meta";
  const speaker = document.createElement("span");
  speaker.className = "speaker";
  speaker.textContent = message.speaker || "未知角色";
  const stage = document.createElement("span");
  stage.className = "stage";
  stage.textContent = `${stageLabels[message.stage] || message.stage || "消息"} · 第${message.round || "?"}轮`;
  meta.append(speaker, stage);
  const content = document.createElement("p");
  content.className = "message-content";
  content.textContent = message.content || "";
  article.append(meta, content);
  return article;
}

function render(data) {
  const signature = JSON.stringify(data);
  if (signature === state.lastJson) return;
  state.lastJson = signature;
  const status = data.status || "idle";
  $("status-pill").textContent = statusText(status);
  $("status-pill").className = `status-pill ${status === "awaiting_approval" ? "waiting" : status === "approved" ? "approved" : status === "human_rework_required" ? "human" : ""}`;
  $("round-label").textContent = data.round_number ? `第 ${data.round_number} 轮` : "尚未开始";
  $("info-status").textContent = statusText(status);
  $("session-dir").textContent = data.session_dir || "尚未生成";
  if (data.default_task && !$('task-input').value.trim()) $("task-input").value = data.default_task;
  const messages = data.messages || [];
  $("empty-state").hidden = messages.length > 0;
  const list = $("message-list");
  list.replaceChildren(...messages.map(renderMessage));
  $("start-button").disabled = data.round_number !== undefined;
  $("next-button").disabled = status !== "approved";
  $("approve-button").disabled = status !== "awaiting_approval";
  $("worker-button").disabled = status !== "awaiting_approval";
  $("human-button").disabled = status !== "awaiting_approval";
  $("submit-human-button").disabled = status !== "human_rework_required";
}

async function refresh() {
  try { render(await request("/api/status")); }
  catch (error) { showToast(error.message); }
}

async function act(path, body, clearIds = []) {
  setBusy(true);
  showToast("");
  try {
    render(await request(path, { method: "POST", body: JSON.stringify(body) }));
    clearIds.forEach((id) => { $(id).value = ""; });
  } catch (error) {
    showToast(error.message);
    if (error.message) refresh();
  } finally { setBusy(false); }
}

$("start-button").addEventListener("click", () => act("/api/start", { task: $("task-input").value }));
$("next-button").addEventListener("click", () => act("/api/next", { task: $("task-input").value }));
$("approve-button").addEventListener("click", () => act("/api/approve", { approved_by: "human" }));
$("worker-button").addEventListener("click", () => act("/api/worker-rework", { feedback: $("worker-feedback").value }, ["worker-feedback"]));
$("human-button").addEventListener("click", () => act("/api/human-rework", { feedback: $("human-feedback").value }, ["human-feedback"]));
$("submit-human-button").addEventListener("click", () => act("/api/human-submit", { result: $("human-result").value }, ["human-result"]));

refresh();
state.timer = window.setInterval(refresh, 1500);
