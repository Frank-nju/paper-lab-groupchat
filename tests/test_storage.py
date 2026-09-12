from pathlib import Path

from paper_lab.storage import SessionLogger, read_paper


def test_read_paper_supports_utf8_text(tmp_path: Path) -> None:
    paper_path = tmp_path / "paper.md"
    paper_path.write_text("中文论文", encoding="utf-8")

    assert read_paper(paper_path) == "中文论文"


def test_session_logger_writes_jsonl_and_markdown(tmp_path: Path) -> None:
    logger = SessionLogger(tmp_path)
    logger.record("GPT6", "建议保留模型。")
    jsonl_path, markdown_path = logger.close()

    assert jsonl_path.exists()
    assert markdown_path.exists()
    assert "建议保留模型" in markdown_path.read_text(encoding="utf-8")
