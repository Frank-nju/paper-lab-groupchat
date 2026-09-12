"""基于通过门禁证据包的群聊评审适配器。"""

from __future__ import annotations

import json
from pathlib import Path

from .evidence_pack import load_evidence_pack, review_context
from .rounds import RoundController


class EvidenceRoundController(RoundController):
    """复用审批状态机，但把整篇原稿替换成带定位的证据上下文。"""

    def __init__(self, *args, evidence_pack_dir: Path, **kwargs) -> None:
        self.evidence_pack_dir = Path(evidence_pack_dir)
        manifest = load_evidence_pack(self.evidence_pack_dir)
        if not manifest.get("quality", {}).get("gate"):
            raise ValueError("证据包质量门禁未通过，不能启动证据包群聊")
        super().__init__(*args, **kwargs)

    def _read_paper(self) -> str:
        return review_context(self.evidence_pack_dir, self.config.max_paper_chars)

    def _persist(self) -> None:
        super()._persist()
        state_path = self.session_dir / "session_state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["evidence_pack_dir"] = str(self.evidence_pack_dir)
        state["context_mode"] = "evidence_pack_retrieval"
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

