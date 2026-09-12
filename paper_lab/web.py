"""本地浏览器群聊界面与 HTTP API。"""

from __future__ import annotations

import argparse
import copy
import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock
from typing import Any, Callable
from urllib.parse import urlsplit

from dotenv import load_dotenv

from .config import ProjectConfig, load_config
from .evidence_rounds import EvidenceRoundController
from .llm import OnlineConfigError
from .rounds import RoundController
from .storage import read_paper


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "web"
DEFAULT_TASK = "审查论文并形成可执行修改意见"
STATIC_FILES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/app.js": "app.js",
    "/styles.css": "styles.css",
}


class WebSession:
    """把已有审批状态机包装成线程安全的网页会话。"""

    def __init__(
        self,
        config: ProjectConfig,
        paper_path: Path,
        problem_text: str,
        task: str = DEFAULT_TASK,
        offline: bool = False,
        evidence_pack_dir: Path | None = None,
    ) -> None:
        self.config = config
        self.default_task = task.strip() or DEFAULT_TASK
        self._lock = RLock()
        controller_class: type[RoundController] = RoundController
        controller_kwargs: dict[str, Any] = {}
        if evidence_pack_dir is not None:
            controller_class = EvidenceRoundController
            controller_kwargs["evidence_pack_dir"] = Path(evidence_pack_dir)
        self.controller = controller_class(
            config=config,
            paper_path=Path(paper_path),
            problem_text=problem_text,
            task=self.default_task,
            offline=offline,
            **controller_kwargs,
        )

    def status(self) -> dict[str, Any]:
        with self._lock:
            snapshot = copy.deepcopy(self.controller.status())
            snapshot["session_dir"] = str(self.controller.session_dir)
            snapshot["default_task"] = self.default_task
            if hasattr(self.controller, "evidence_pack_dir"):
                snapshot["evidence_pack_dir"] = str(
                    self.controller.evidence_pack_dir
                )
            return snapshot

    def start(self, task: str | None = None) -> dict[str, Any]:
        with self._lock:
            if self.controller.current is not None:
                raise RuntimeError("当前已有轮次，请使用“下一轮”或先完成当前审批")
            self.controller.task = self._task(task)
            self.controller.start_round()
            return self.status()

    def next_round(self, task: str | None = None) -> dict[str, Any]:
        with self._lock:
            if self.controller.current is None:
                raise RuntimeError("还没有已审批轮次，请先开始第一轮")
            if self.controller.current["status"] != "approved":
                raise RuntimeError("当前轮次尚未审批，不能进入下一轮")
            if task and task.strip():
                self.controller.task = task.strip()
            self.controller.start_round()
            return self.status()

    def approve(self, approved_by: str = "human") -> dict[str, Any]:
        with self._lock:
            self.controller.approve(approved_by.strip() or "human")
            return self.status()

    def worker_rework(self, feedback: str) -> dict[str, Any]:
        with self._lock:
            self.controller.redo_worker(self._required_text(feedback, "低价模型返工意见"))
            return self.status()

    def human_rework(self, feedback: str) -> dict[str, Any]:
        with self._lock:
            self.controller.request_human_rework(
                self._required_text(feedback, "人工返工意见")
            )
            return self.status()

    def human_submit(self, result: str) -> dict[str, Any]:
        with self._lock:
            self.controller.submit_human_rework(
                self._required_text(result, "人工返工结果")
            )
            return self.status()

    def _task(self, task: str | None) -> str:
        selected = (task or self.default_task).strip()
        if not selected:
            raise ValueError("任务不能为空")
        return selected

    @staticmethod
    def _required_text(value: str, label: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError(f"{label}不能为空")
        return text


class WebApplication:
    """网页 API 的无框架应用对象，便于测试和嵌入其他启动器。"""

    def __init__(self, session: WebSession) -> None:
        self.session = session

    def dispatch(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        payload = payload or {}
        if method == "GET" and path == "/api/status":
            return self.session.status()
        if method != "POST":
            raise LookupError("找不到接口")
        actions: dict[str, Callable[..., dict[str, Any]]] = {
            "/api/start": lambda: self.session.start(payload.get("task")),
            "/api/next": lambda: self.session.next_round(payload.get("task")),
            "/api/approve": lambda: self.session.approve(
                str(payload.get("approved_by", "human"))
            ),
            "/api/worker-rework": lambda: self.session.worker_rework(
                str(payload.get("feedback", ""))
            ),
            "/api/human-rework": lambda: self.session.human_rework(
                str(payload.get("feedback", ""))
            ),
            "/api/human-submit": lambda: self.session.human_submit(
                str(payload.get("result", ""))
            ),
        }
        action = actions.get(path)
        if action is None:
            raise LookupError("找不到接口")
        return action()


class WebHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], application: WebApplication):
        self.application = application
        super().__init__(server_address, WebRequestHandler)


class WebRequestHandler(BaseHTTPRequestHandler):
    server: WebHTTPServer
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/api/status":
            self._api_call("GET", path, None)
            return
        filename = STATIC_FILES.get(path)
        if filename is None:
            self._send_json(404, {"error": "找不到页面"})
            return
        file_path = WEB_ROOT / filename
        try:
            content = file_path.read_bytes()
        except OSError as exc:
            self._send_json(500, {"error": f"网页资源读取失败：{exc}"})
            return
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:  # noqa: N802
        length_text = self.headers.get("Content-Length", "0")
        try:
            length = int(length_text)
        except ValueError:
            self._send_json(400, {"error": "无效的请求体长度"})
            return
        if length > 1_000_000:
            self._send_json(413, {"error": "请求体过大"})
            return
        try:
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8") or "{}")
            if not isinstance(payload, dict):
                raise ValueError("请求体必须是 JSON 对象")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self._send_json(400, {"error": f"请求体不是有效 JSON：{exc}"})
            return
        self._api_call("POST", urlsplit(self.path).path, payload)

    def _api_call(
        self, method: str, path: str, payload: dict[str, Any] | None
    ) -> None:
        try:
            result = self.server.application.dispatch(method, path, payload)
        except LookupError as exc:
            self._send_json(404, {"error": str(exc)})
        except (RuntimeError, ValueError, FileNotFoundError) as exc:
            self._send_json(
                409,
                {"error": str(exc), "status": self.server.application.session.status()},
            )
        except (OnlineConfigError, OSError) as exc:
            self._send_json(500, {"error": str(exc)})
        else:
            self._send_json(200, result)

    def _send_json(self, status: int, payload: Any) -> None:
        content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("[paper-lab-web] " + (format % args) + "\n")


def create_server(application: WebApplication, host: str = "127.0.0.1", port: int = 8765) -> WebHTTPServer:
    return WebHTTPServer((host, port), application)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="paper-lab 本地浏览器群聊界面")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--paper", type=Path, help="覆盖配置中的论文路径")
    parser.add_argument(
        "--problem",
        type=Path,
        default=Path("data/problem_statement.pdf"),
        help="原始赛题路径",
    )
    parser.add_argument("--evidence-pack", type=Path, help="使用已通过门禁的证据包")
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument("--offline", action="store_true", help="不请求 API，运行离线演示")
    parser.add_argument("--host", default="127.0.0.1", help="默认只监听本机")
    parser.add_argument("--port", type=int, default=8765)
    return parser


def _resolve_config_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def _resolve_path(root: Path, path: Path | None, default: Path) -> Path:
    selected = default if path is None else path
    return selected if selected.is_absolute() else root / selected


def main() -> int:
    args = _parser().parse_args()
    config_path = _resolve_config_path(args.config)
    load_dotenv(config_path.parent / ".env")
    config = load_config(config_path)
    paper_path = _resolve_path(config.root, args.paper, config.paper_path)
    problem_path = _resolve_path(
        config.root, args.problem, Path("data/problem_statement.pdf")
    )
    evidence_pack = (
        _resolve_path(config.root, args.evidence_pack, Path(""))
        if args.evidence_pack
        else None
    )
    offline = args.offline
    if not offline and not all(
        os.getenv(spec.api_key_env, "").strip()
        for spec in (config.gpt6, config.fable51, config.cheap)
    ):
        print("未检测到完整 API Key，网页自动切换离线模式；配置 .env 后可在线运行。")
        offline = True
    try:
        problem_text = read_paper(problem_path, config.max_paper_chars)
        session = WebSession(
            config=config,
            paper_path=paper_path,
            problem_text=problem_text,
            task=args.task,
            offline=offline,
            evidence_pack_dir=evidence_pack,
        )
        server = create_server(WebApplication(session), args.host, args.port)
    except (FileNotFoundError, OnlineConfigError, OSError, ValueError) as exc:
        print(f"网页启动失败：{exc}", file=sys.stderr)
        return 1
    print(f"paper-lab 网页已启动：http://{args.host}:{args.port}")
    print("按 Ctrl+C 停止服务。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n网页服务已停止。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
