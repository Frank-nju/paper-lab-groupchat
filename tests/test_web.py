from pathlib import Path

from paper_lab.config import default_config
from paper_lab.web import WEB_ROOT, WebSession


def make_session(tmp_path: Path) -> WebSession:
    return WebSession(
        config=default_config(tmp_path),
        paper_path=tmp_path / "paper.txt",
        problem_text="原始赛题",
        offline=True,
    )


def test_web_session_runs_round_and_exposes_messages(tmp_path: Path) -> None:
    session = make_session(tmp_path)

    result = session.start("审查模型证据链")

    assert result["status"] == "awaiting_approval"
    assert [item["speaker"] for item in result["messages"]] == [
        "GPT6",
        "Fable51",
        "GPT6",
        "Fable51",
        "CheapWorker",
    ]
    assert result["session_dir"]


def test_web_session_approval_unlocks_next_round(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    session.start("第一轮")

    try:
        session.next_round("第二轮")
    except RuntimeError as exc:
        assert "审批" in str(exc)
    else:
        raise AssertionError("网页会话不应绕过审批进入下一轮")

    session.approve("human")
    result = session.next_round("第二轮")
    assert result["round_number"] == 2
    assert result["task"] == "第二轮"


def test_web_session_supports_two_rework_routes(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    first = session.start("审查")
    advanced = first["messages"][:4]

    worker_retry = session.worker_rework("补充完成性测试")
    assert worker_retry["messages"][:4] == advanced
    assert worker_retry["status"] == "awaiting_approval"

    session.human_rework("人工先补充证据位置")
    human_retry = session.human_submit("已补充证据位置和验证条件")
    assert human_retry["status"] == "awaiting_approval"
    assert human_retry["messages"][-1]["speaker"] == "Human"


def test_web_assets_are_present(tmp_path: Path) -> None:
    assert (WEB_ROOT / "index.html").exists()
    assert (WEB_ROOT / "app.js").exists()
    assert (WEB_ROOT / "styles.css").exists()
    assert "paper-lab" in (WEB_ROOT / "index.html").read_text(encoding="utf-8")
