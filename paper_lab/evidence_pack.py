"""证据包公共 API：全量本地索引与均衡的小问级模型上下文。"""

from __future__ import annotations

import json
from pathlib import Path

from . import evidence_pack_public_core as _public


build_evidence_pack = _public.build_evidence_pack
load_evidence_pack = _public.load_evidence_pack


def review_context(pack_dir: Path, max_chars: int = 24_000) -> str:
    """按小问均分预算，保证每个 Q 都有题意、定位证据和附件索引。"""
    pack_dir = Path(pack_dir)
    manifest = load_evidence_pack(pack_dir)
    if not manifest.get("quality", {}).get("gate"):
        raise ValueError("证据包质量门禁未通过，禁止直接喂给评审模型")
    question_ids = manifest["problem"]["question_ids"]
    header = (
        f"证据包状态：{manifest['status']}，来源数：{len(manifest['sources'])}\n"
        "所有引用必须保留 evidence_id 或文件页码；不能把未列出的内容当作事实。"
    )
    remaining = max(1, max_chars - len(header) - 2)
    per_question = max(2_500, remaining // max(1, len(question_ids)))
    blocks = [header]
    for question_id in question_ids:
        path = pack_dir / "question_packs" / f"{question_id}.json"
        item = json.loads(path.read_text(encoding="utf-8"))
        block = [
            f"===== {question_id} · {item['problem']['location']} =====",
            item["problem"]["text"][:1_200],
        ]
        for evidence in item.get("evidence", [])[:4]:
            block.append(
                f"[{evidence['evidence_id']} · {evidence['location']}]\n"
                f"{evidence['text'][:700]}"
            )
        attachments = json.dumps(item.get("attachments", []), ensure_ascii=False)
        block.append("附件摘要（全量见 attachment_manifest.json）：" + attachments[:1_000])
        blocks.append("\n".join(block)[:per_question])
    return "\n".join(blocks)


__all__ = ["build_evidence_pack", "load_evidence_pack", "review_context"]

