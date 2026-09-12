from pathlib import Path
import time
from threading import Event

from paper_lab.config import default_config
from paper_lab.web import WEB_ROOT, WebSession


def make_session(tmp_path: Path) -> WebSession:
    return WebSession(
        config=default_config(tmp_path),
        paper_path=tmp_path / "paper.txt",
        problem_text="原始赛题",
        offline=True,
    )


def wait_for_status(session: WebSession, expected: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    last = session.status()
    while time.monotonic() < deadline:
        last = session.status()
        if last["status"] == expected:
            return last
        if last["status"] == "error":
            raise AssertionError(f"后台任务失败：{last.get('error')}")
        time.sleep(0.01)
    raise AssertionError(f"状态未到达 {expected}：{last}")


def test_web_session_runs_round_and_exposes_messages(tmp_path: Path) -> None:
    session = make_session(tmp_path)

    initial = session.start("审查模型证据链")
    assert initial["status"] in {"processing", "awaiting_approval"}
    result = wait_for_status(session, "awaiting_approval")

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
    wait_for_status(session, "awaiting_approval")

    try:
        session.next_round("第二轮")
    except RuntimeError as exc:
        assert "审批" in str(exc)
    else:
        raise AssertionError("网页会话不应绕过审批进入下一轮")

    session.approve("human")
    result = session.next_round("第二轮")
    assert result["status"] in {"processing", "awaiting_approval"}
    result = wait_for_status(session, "awaiting_approval")
    assert result["round_number"] == 2
    assert result["task"] == "第二轮"


def test_web_session_supports_two_rework_routes(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    session.start("审查")
    first = wait_for_status(session, "awaiting_approval")
    advanced = first["messages"][:4]

    worker_retry = session.worker_rework("补充完成性测试")
    assert worker_retry["status"] in {"processing", "awaiting_approval"}
    worker_retry = wait_for_status(session, "awaiting_approval")
    assert worker_retry["messages"][:4] == advanced

    session.human_rework("人工先补充证据位置")
    human_retry = session.human_submit("已补充证据位置和验证条件")
    assert human_retry["status"] == "awaiting_approval"
    assert human_retry["messages"][-1]["speaker"] == "Human"


def test_web_status_is_available_during_background_job(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    entered = Event()
    release = Event()
    original_start = session.controller.start_round

    def slow_start_round() -> dict:
        entered.set()
        if not release.wait(2):
            raise AssertionError("测试后台任务超时")
        return original_start()

    session.controller.start_round = slow_start_round
    initial = session.start("慢任务")
    assert initial["status"] == "processing"
    assert entered.wait(1)
    assert session.status()["status"] == "processing"
    release.set()
    wait_for_status(session, "awaiting_approval")


def test_web_assets_are_present(tmp_path: Path) -> None:
    assert (WEB_ROOT / "index.html").exists()
    assert (WEB_ROOT / "app.js").exists()
    assert (WEB_ROOT / "styles.css").exists()
    assert "paper-lab" in (WEB_ROOT / "index.html").read_text(encoding="utf-8")
