from pathlib import Path

from paper_lab.config import default_config
from paper_lab.rounds import RoundController, load_reviewer_knowledge


def test_round_has_two_advanced_messages_then_worker(tmp_path: Path) -> None:
    config = default_config(tmp_path)
    controller = RoundController(
        config=config,
        paper_path=tmp_path / "paper.txt",
        problem_text="原始赛题",
        task="审查模型证据链",
        offline=True,
    )

    result = controller.start_round()

    assert [item["speaker"] for item in result["messages"]] == [
        "GPT6",
        "Fable51",
        "GPT6",
        "Fable51",
        "CheapWorker",
    ]
    assert [item["stage"] for item in result["messages"][:4]] == [
        "independent",
        "independent",
        "synthesis",
        "synthesis",
    ]
    assert result["status"] == "awaiting_approval"


def test_next_round_requires_approval(tmp_path: Path) -> None:
    config = default_config(tmp_path)
    controller = RoundController(
        config=config,
        paper_path=tmp_path / "paper.txt",
        problem_text="原始赛题",
        task="审查",
        offline=True,
    )
    controller.start_round()

    try:
        controller.start_round()
    except RuntimeError as exc:
        assert "审批" in str(exc)
    else:
        raise AssertionError("未审批时不应进入下一轮")

    controller.approve("human")
    next_result = controller.start_round()
    assert next_result["round_number"] == 2


def test_only_worker_or_human_can_be_sent_back(tmp_path: Path) -> None:
    config = default_config(tmp_path)
    controller = RoundController(
        config=config,
        paper_path=tmp_path / "paper.txt",
        problem_text="原始赛题",
        task="审查",
        offline=True,
    )
    first = controller.start_round()
    advanced = first["messages"][:4]

    worker_retry = controller.redo_worker("补充完成性测试")
    assert worker_retry["messages"][:4] == advanced
    assert worker_retry["status"] == "awaiting_approval"

    controller.request_human_rework("人工决定先补充证据")
    human_retry = controller.submit_human_rework("人工补充了证据位置和验证条件")
    assert human_retry["status"] == "awaiting_approval"
    assert human_retry["messages"][-1]["speaker"] == "Human"


def test_knowledge_bundle_contains_audit_rules(tmp_path: Path) -> None:
    knowledge = load_reviewer_knowledge(tmp_path)

    assert "present" in knowledge
    assert "unverifiable" in knowledge
    assert "global_search" in knowledge
