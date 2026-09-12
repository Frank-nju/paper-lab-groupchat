from paper_lab.config import ModelSpec
from paper_lab.llm import _llm_config


def test_llm_config_has_bounded_timeout_and_no_hidden_retries(monkeypatch) -> None:
    monkeypatch.setenv("TEST_API_KEY", "test-key")
    monkeypatch.setenv("TEST_BASE_URL", "https://example.invalid")
    monkeypatch.setenv("PAPER_LAB_LLM_TIMEOUT_SECONDS", "37")

    config = _llm_config(
        ModelSpec("test", "deepseek-flash", "TEST_API_KEY", "TEST_BASE_URL")
    )

    model_config = config["config_list"][0]
    assert model_config["timeout"] == 37
    assert model_config["max_retries"] == 0
    assert "max_retries" not in config


def test_llm_config_uses_safe_default_timeout(monkeypatch) -> None:
    monkeypatch.setenv("TEST_API_KEY", "test-key")
    monkeypatch.delenv("PAPER_LAB_LLM_TIMEOUT_SECONDS", raising=False)

    config = _llm_config(ModelSpec("test", "deepseek-flash", "TEST_API_KEY", ""))

    model_config = config["config_list"][0]
    assert model_config["timeout"] == 180
    assert model_config["max_retries"] == 0
