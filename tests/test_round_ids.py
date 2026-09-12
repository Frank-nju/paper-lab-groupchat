from pathlib import Path

from paper_lab.config import default_config
from paper_lab.rounds import RoundController


def test_round_message_ids_are_unique(tmp_path: Path) -> None:
    config = default_config(tmp_path)
    controller = RoundController(
        config=config,
        paper_path=tmp_path / "paper.txt",
        problem_text="原始赛题",
        task="审查",
        offline=True,
    )

    messages = controller.start_round()["messages"]
    ids = [item["message_id"] for item in messages]

    assert len(ids) == len(set(ids))
