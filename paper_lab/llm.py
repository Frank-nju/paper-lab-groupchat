"""AG2 经典 GroupChat 适配层。"""

from __future__ import annotations

import os
from typing import Any

from .config import ModelSpec, ProjectConfig
from .workflow import extract_agent_messages


class OnlineConfigError(RuntimeError):
    """在线模型配置缺失或 AG2 不可用。"""


def _request_timeout_seconds() -> int:
    raw = os.getenv("PAPER_LAB_LLM_TIMEOUT_SECONDS", "180").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 180


def _llm_config(spec: ModelSpec) -> dict[str, Any]:
    api_key = os.getenv(spec.api_key_env, "").strip()
    if not api_key:
        raise OnlineConfigError(
            f"未设置 {spec.api_key_env}，请编辑 .env；也可以使用 --offline。"
        )
    item: dict[str, Any] = {
        "api_type": "openai",
        "model": spec.model,
        "api_key": api_key,
        # AG2 不认识自定义模型名时会警告；价格未知时明确按 0 计。
        "price": [0, 0],
        # 这两个是 OpenAI 配置项，必须放在 config_list 的模型项内。
        "timeout": _request_timeout_seconds(),
        "max_retries": 0,
    }
    base_url = os.getenv(spec.base_url_env, "").strip()
    if base_url:
        item["base_url"] = base_url
    return {
        "config_list": [item],
        "temperature": spec.temperature,
    }


def run_ag2_review(config: ProjectConfig, paper_text: str, task: str) -> list[dict[str, Any]]:
    """固定 GPT6 → Fable51 → CheapWorker 顺序运行一次群聊。"""
    try:
        from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent
    except ImportError as exc:
        raise OnlineConfigError("缺少 AG2，请先安装 requirements.txt。") from exc

    gpt6 = AssistantAgent(
        name="GPT6",
        system_message=(
            "你是 GPT-6 建模方法论审查员。与 Fable51 地位完全对等；本轮只输出一句中文，"
            "聚焦问题建模、假设、指标和可验证性，不写列表，不改文件，不执行代码。"
        ),
        llm_config=_llm_config(config.gpt6),
        human_input_mode="NEVER",
        code_execution_config=False,
    )
    fable = AssistantAgent(
        name="Fable51",
        system_message=(
            "你是 Fable 5.1 数学推导审查员。与 GPT6 地位完全对等；本轮只输出一句中文，"
            "聚焦变量、公式、约束、边界、单位和证明链条，不写列表，不改文件，不执行代码。"
        ),
        llm_config=_llm_config(config.fable51),
        human_input_mode="NEVER",
        code_execution_config=False,
    )
    cheap = AssistantAgent(
        name="CheapWorker",
        system_message=(
            "你是低价模型执行员，读取 GPT6 与 Fable51 各一句意见后输出一句中文执行结论，"
            "说明要改什么、如何验证，并把原稿视为只读，不覆盖原稿、不执行代码。"
        ),
        llm_config=_llm_config(config.cheap),
        human_input_mode="NEVER",
        code_execution_config=False,
    )
    user = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",
        code_execution_config=False,
    )

    def select_next(last_speaker: Any, groupchat: Any) -> Any:
        if last_speaker is user:
            return gpt6
        if last_speaker is gpt6:
            return fable
        if last_speaker is fable:
            return cheap
        return None

    groupchat = GroupChat(
        agents=[user, gpt6, fable, cheap],
        messages=[],
        max_round=4,
        speaker_selection_method=select_next,
        allow_repeat_speaker=False,
        send_introductions=False,
    )
    manager = GroupChatManager(groupchat=groupchat, llm_config=False)
    prompt = (
        f"任务：{task}\n\n论文内容（只读）：\n{paper_text}\n\n"
        "按固定顺序完成：GPT6一句、Fable51一句、CheapWorker一句。"
    )
    user.initiate_chat(manager, message=prompt, clear_history=True, silent=False)
    records = extract_agent_messages(groupchat.messages)
    if len(records) != 3:
        names = [item.get("name") for item in groupchat.messages]
        raise OnlineConfigError(f"群聊未完成三角色闭环，实际消息角色：{names}")
    records[-1]["source_opinions"] = [records[0]["content"], records[1]["content"]]
    records[-1]["paper_unchanged"] = True
    return records
