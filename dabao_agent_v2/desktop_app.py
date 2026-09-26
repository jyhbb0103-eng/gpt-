"""Windows desktop shell for the existing Streamlit workspace.

This module only manages the local Streamlit process and embeds its page in a
pywebview window. It does not change any Agent or stock-analysis behavior.
"""

from __future__ import annotations

import argparse
import ctypes
import http.client
import logging
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import IO

APP_TITLE = "大宝 Agent 2.0"
APP_HOST = "127.0.0.1"
APP_PORT = 8501
APP_URL = f"http://{APP_HOST}:{APP_PORT}"
STARTUP_TIMEOUT_SECONDS = 30.0


def find_project_root() -> Path:
    """Locate the project whether run from source or a PyInstaller dist folder."""
    configured = os.getenv("DABAO_PROJECT_ROOT")
    executable_dir = Path(sys.executable).resolve().parent
    source_dir = Path(__file__).resolve().parent
    candidates = [
        Path(configured).expanduser() if configured else None,
        executable_dir,
        executable_dir.parent,
        Path.cwd(),
        source_dir,
        source_dir.parent,
    ]
    checked: set[Path] = set()
    for candidate in candidates:
        if candidate is None:
            continue
        resolved = candidate.resolve()
        if resolved in checked:
            continue
        checked.add(resolved)
        if (resolved / "app.py").is_file():
            return resolved
    raise FileNotFoundError("未找到 app.py。请把大宝Agent.exe 放到项目根目录后再启动。")


def project_python(project_root: Path) -> Path:
    """Return the Python executable from this project's virtual environment."""
    configured = os.getenv("DABAO_PROJECT_PYTHON")
    if configured:
        python_path = Path(configured).expanduser().resolve()
    elif os.name == "nt":
        python_path = project_root / ".venv" / "Scripts" / "python.exe"
    else:
        python_path = project_root / ".venv" / "bin" / "python"
    if not python_path.is_file():
        raise FileNotFoundError(f"未找到项目虚拟环境：{python_path}")
    return python_path


def configure_logging(project_root: Path) -> tuple[logging.Logger, Path]:
    """Create the required desktop startup log."""
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "desktop_startup.log"
    logger = logging.getLogger("dabao.desktop")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger, log_path


def port_is_open(host: str = APP_HOST, port: int = APP_PORT) -> bool:
    """Return True when another process is already listening on the port."""
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


def service_is_ready(url: str = APP_URL) -> bool:
    """Check Streamlit directly, bypassing system HTTP/SOCKS proxy settings."""
    del url  # The desktop service always uses the fixed loopback host and port.
    connection = http.client.HTTPConnection(APP_HOST, APP_PORT, timeout=1.0)
    try:
        connection.request(
            "GET",
            "/_stcore/health",
            headers={"User-Agent": "DabaoDesktop/2.0", "Connection": "close"},
        )
        response = connection.getresponse()
        return response.status == 200 and response.read(20).strip().lower() == b"ok"
    except (OSError, http.client.HTTPException):
        return False
    finally:
        connection.close()


def start_streamlit(project_root: Path, log_stream: IO[bytes]) -> subprocess.Popen[bytes]:
    """Start Streamlit without opening an external browser or console window."""
    python_path = project_python(project_root)
    command = [
        str(python_path),
        "-m",
        "streamlit",
        "run",
        "app.py",
        "--server.address",
        APP_HOST,
        "--server.port",
        str(APP_PORT),
        "--server.headless",
        "true",
        "--server.fileWatcherType",
        "none",
        "--browser.gatherUsageStats",
        "false",
    ]
    creation_flags = 0
    if os.name == "nt":
        creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    environment = os.environ.copy()
    environment["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    return subprocess.Popen(
        command,
        cwd=project_root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=log_stream,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )


def wait_for_streamlit(
    process: subprocess.Popen[bytes],
    timeout: float = STARTUP_TIMEOUT_SECONDS,
) -> None:
    """Wait until Streamlit responds, failing early if its process exits."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        exit_code = process.poll()
        if exit_code is not None:
            raise RuntimeError(f"Streamlit 提前退出，退出代码：{exit_code}")
        if service_is_ready():
            return
        time.sleep(0.4)
    raise TimeoutError("等待 Streamlit 启动超过 30 秒。")


def stop_process_tree(process: subprocess.Popen[bytes] | None) -> None:
    """Stop only the Streamlit process tree created by this launcher."""
    if process is None or process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            process.terminate()
    else:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def show_startup_error() -> None:
    """Display the required Chinese error without depending on pywebview."""
    message = "大宝 Agent 启动失败，请查看日志。"
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(0, message, APP_TITLE, 0x10)
    else:
        print(message, file=sys.stderr)


def open_desktop_window() -> None:
    """Open the existing Streamlit UI inside a resizable native window."""
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError("未安装 pywebview，请先运行桌面版依赖安装或构建脚本。") from exc
    webview.create_window(
        title=APP_TITLE,
        url=APP_URL,
        width=1400,
        height=900,
        resizable=True,
    )
    webview.start()


def run(self_test: bool = False) -> int:
    """Start Streamlit, optionally validate it, and always clean up afterward."""
    process: subprocess.Popen[bytes] | None = None
    log_stream: IO[bytes] | None = None
    logger: logging.Logger | None = None
    try:
        # Ensure pywebview and any inherited Python networking bypass proxies for
        # the loopback-only Streamlit service.
        os.environ["NO_PROXY"] = "127.0.0.1,localhost"
        os.environ["no_proxy"] = "127.0.0.1,localhost"
        project_root = find_project_root()
        logger, log_path = configure_logging(project_root)
        logger.info("桌面启动器开始运行，项目目录：%s", project_root)
        if port_is_open():
            raise RuntimeError(f"端口 {APP_PORT} 已被其他程序占用，请先关闭原来的大宝窗口。")
        log_stream = log_path.open("ab", buffering=0)
        process = start_streamlit(project_root, log_stream)
        logger.info("已启动 Streamlit 子进程 PID=%s", process.pid)
        wait_for_streamlit(process)
        logger.info("Streamlit 已就绪：%s", APP_URL)
        if self_test:
            logger.info("桌面启动器自检通过")
            return 0
        open_desktop_window()
        logger.info("桌面窗口已关闭")
        return 0
    except Exception:
        if logger is not None:
            logger.exception("桌面启动失败")
        show_startup_error()
        return 1
    finally:
        stop_process_tree(process)
        if logger is not None:
            logger.info("Streamlit 子进程已清理")
        if log_stream is not None:
            log_stream.close()
        if logger is not None:
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dabao Agent desktop launcher")
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="start Streamlit, verify HTTP readiness, then exit without opening a window",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(self_test=parse_args().self_test))
