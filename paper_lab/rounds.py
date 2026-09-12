"""公开轮次 API：状态判定和消息追踪的稳定适配层。"""

from __future__ import annotations

from uuid import uuid4

from . import rounds_impl as _impl


def _worker_decision(content: str) -> str:
    lowered = content.lower()
    if any(
        token in lowered
        for token in ("needs_rework", "需要返工", "不通过", "未通过", "建议打回")
    ):
        return "needs_rework"
    return "ready_for_approval"


def _message(speaker: str, stage: str, content: str, round_number: int, **metadata):
    return {
        "message_id": f"R{round_number}-{stage}-{speaker}-{uuid4().hex[:8]}",
        "timestamp": _impl._now(),
        "round": round_number,
        "speaker": speaker,
        "stage": stage,
        "content": content.strip(),
        **metadata,
    }


_impl._worker_decision = _worker_decision
_impl._message = _message
RoundController = _impl.RoundController
load_reviewer_knowledge = _impl.load_reviewer_knowledge

__all__ = ["RoundController", "load_reviewer_knowledge"]
