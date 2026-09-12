"""项目配置与跨平台路径处理。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """配置内容无效。"""


@dataclass(frozen=True)
class ModelSpec:
    name: str
    model: str
    api_key_env: str
    base_url_env: str
    temperature: float = 0.2


@dataclass(frozen=True)
class ProjectConfig:
    root: Path
    data_dir: Path
    output_dir: Path
    log_dir: Path
    paper_file: str
    gpt6: ModelSpec
    fable51: ModelSpec
    cheap: ModelSpec
    max_paper_chars: int = 80_000

    @property
    def paper_path(self) -> Path:
        return self.data_dir / self.paper_file

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


def _model_spec(data: dict[str, Any], default: ModelSpec) -> ModelSpec:
    section = data.get(default.name, {})
    if not isinstance(section, dict):
        raise ConfigError(f"models.{default.name} 必须是对象")
    return ModelSpec(
        name=default.name,
        model=str(section.get("model", default.model)),
        api_key_env=str(section.get("api_key_env", default.api_key_env)),
        base_url_env=str(section.get("base_url_env", default.base_url_env)),
        temperature=float(section.get("temperature", default.temperature)),
    )


def default_config(root: Path) -> ProjectConfig:
    return ProjectConfig(
        root=root,
        data_dir=root / "data",
        output_dir=root / "outputs",
        log_dir=root / "logs",
        paper_file="candidate_paper.pdf",
        gpt6=ModelSpec("gpt6", "gpt-6", "GPT6_API_KEY", "GPT6_BASE_URL"),
        fable51=ModelSpec(
            "fable51", "fable-5.1", "FABLE51_API_KEY", "FABLE51_BASE_URL"
        ),
        cheap=ModelSpec(
            "cheap", "cheap-model", "CHEAP_API_KEY", "CHEAP_BASE_URL"
        ),
    )


def _resolve(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def load_config(path: Path) -> ProjectConfig:
    """读取 YAML 配置；配置路径采用相对于项目根目录的形式。"""
    root = path.resolve().parent
    base = default_config(root)
    if not path.exists():
        return base

    try:
        import yaml
    except ImportError as exc:
        raise ConfigError("缺少 PyYAML，请先安装 requirements.txt") from exc

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as exc:
        raise ConfigError(f"无法读取配置文件：{path}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("config.yaml 顶层必须是对象")

    project = raw.get("project", {})
    workflow = raw.get("workflow", {})
    models = raw.get("models", {})
    if not isinstance(project, dict) or not isinstance(workflow, dict):
        raise ConfigError("project/workflow 必须是对象")
    if not isinstance(models, dict):
        raise ConfigError("models 必须是对象")

    return ProjectConfig(
        root=root,
        data_dir=_resolve(root, str(project.get("data_dir", base.data_dir))),
        output_dir=_resolve(root, str(project.get("output_dir", base.output_dir))),
        log_dir=_resolve(root, str(project.get("log_dir", base.log_dir))),
        paper_file=str(project.get("paper_file", base.paper_file)),
        gpt6=_model_spec(models, base.gpt6),
        fable51=_model_spec(models, base.fable51),
        cheap=_model_spec(models, base.cheap),
        max_paper_chars=int(workflow.get("max_paper_chars", base.max_paper_chars)),
    )

