"""论文读取与会话记录。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def read_paper(path: Path, max_chars: int | None = None) -> str:
    """读取文本或 PDF；PDF 提取失败时返回可诊断的占位信息。"""
    if not path.exists():
        raise FileNotFoundError(f"论文文件不存在：{path}")
    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader

            pages = PdfReader(str(path)).pages
            text = "\n".join(page.extract_text() or "" for page in pages)
        except ImportError:
            text = f"[PDF未提取：请安装 pypdf 后重新运行] {path.name}"
        except Exception as exc:  # PDF 结构差异需要保留可诊断信息
            text = f"[PDF提取失败：{type(exc).__name__}] {path.name}"
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
    if max_chars is not None:
        return text[:max_chars]
    return text


class SessionLogger:
    """同时生成 JSONL 和 Markdown，方便复盘或转交廉价模型。"""

    def __init__(self, log_dir: Path) -> None:
        self.log_dir = log_dir
        self.started_at = datetime.now().astimezone()
        self.records: list[dict[str, Any]] = []

    def record(self, speaker: str, content: str, **metadata: Any) -> None:
        self.records.append(
            {
                "timestamp": datetime.now().astimezone().isoformat(),
                "speaker": speaker,
                "content": content,
                **metadata,
            }
        )

    def close(self) -> tuple[Path, Path]:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = self.started_at.strftime("%Y%m%d_%H%M%S")
        jsonl_path = self.log_dir / f"session_{stamp}.jsonl"
        markdown_path = self.log_dir / f"session_{stamp}.md"
        with jsonl_path.open("w", encoding="utf-8", newline="\n") as stream:
            for record in self.records:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        lines = [
            "# 论文群聊会话",
            "",
            f"开始时间：{self.started_at.isoformat()}",
            "",
        ]
        for record in self.records:
            lines.extend(
                [
                    f"## {record['speaker']}",
                    "",
                    str(record["content"]),
                    "",
                ]
            )
        markdown_path.write_text("\n".join(lines), encoding="utf-8")
        return jsonl_path, markdown_path


def write_execution_report(output_dir: Path, records: list[dict[str, Any]]) -> Path:
    """把廉价模型的最终执行意见单独落盘，不触碰原稿。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"execution_{stamp}.md"
    cheap = next((item for item in records if item["speaker"] == "CheapWorker"), None)
    lines = [
        "# 廉价模型执行结果",
        "",
        "> 本文件是执行草案；原始论文不会被覆盖。",
        "",
        cheap["content"] if cheap else "未找到廉价模型输出。",
        "",
    ]
    if cheap and cheap.get("source_opinions"):
        lines.append("## 上游意见")
        lines.append("")
        lines.extend(f"- {item}" for item in cheap["source_opinions"])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

