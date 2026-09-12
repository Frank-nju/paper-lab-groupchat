"""固定顺序的三模型论文优化流程。"""

from __future__ import annotations

import re
from typing import Any


ROUND_PLAN = ["GPT6", "Fable51", "CheapWorker"]


def build_round_plan() -> list[str]:
    """返回固定顺序，保证 GPT-6 与 Fable 5.1 对等发言。"""
    return ROUND_PLAN.copy()


def compact_to_one_sentence(text: str) -> str:
    """把模型输出压成一句，避免讨论意见变成多段传话。"""
    normalized = " ".join(line.strip() for line in text.splitlines() if line.strip())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return "未形成有效意见。"
    match = re.match(r"^(.+?[。！？!?])", normalized)
    if match:
        return match.group(1).strip()
    return normalized.rstrip("。！？!? ") + "。"


def _message(speaker: str, content: str, **extra: Any) -> dict[str, Any]:
    sentence = compact_to_one_sentence(content)
    return {
        "speaker": speaker,
        "content": sentence,
        "sentence_count": 1,
        **extra,
    }


def run_offline_review(paper_text: str, task: str = "审查论文并提出最重要的修改意见") -> list[dict[str, Any]]:
    """离线演示，不请求外部 API，也不修改论文。"""
    paper_size = len(paper_text)
    gpt6 = _message(
        "GPT6",
        f"从建模方法论看，应围绕“{task}”优先核对问题定义、假设与评价指标的一致性（当前读入约{paper_size}字符）。",
        mode="offline",
    )
    fable = _message(
        "Fable51",
        "从数学推导看，应逐式检查变量定义、约束边界、单位量纲和结论是否能由模型与数据共同推出。",
        mode="offline",
    )
    cheap = _message(
        "CheapWorker",
        "读取GPT6与Fable51的意见后，先生成可执行修改清单并保存到outputs，同时保持原稿只读不覆盖。",
        mode="offline",
        source_opinions=[gpt6["content"], fable["content"]],
        paper_unchanged=True,
    )
    return [gpt6, fable, cheap]


def extract_agent_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从 AG2 群聊消息中提取三位角色的首条有效意见。"""
    aliases = {
        "GPT6": {"GPT6", "gpt6", "GPT6Reviewer"},
        "Fable51": {"Fable51", "fable51", "FableReviewer"},
        "CheapWorker": {"CheapWorker", "cheap", "LowCostWorker"},
    }
    selected: list[dict[str, Any]] = []
    for expected in ROUND_PLAN:
        for item in messages:
            name = str(item.get("name", ""))
            if name in aliases[expected] and item.get("content"):
                content = compact_to_one_sentence(str(item["content"]))
                selected.append(
                    {
                        "speaker": expected,
                        "content": content,
                        "sentence_count": 1,
                        "mode": "online",
                    }
                )
                break
    return selected

