"""Save and optionally run generated Python after conservative AST safety checks."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from config.agent_config import GENERATED_CODE_TIMEOUT_SECONDS
from tools.file_tool import FileTool


class PythonTool:
    BLOCKED_CALLS = {"eval", "exec", "compile", "__import__", "system", "popen", "rmtree", "unlink", "remove", "rmdir"}
    BLOCKED_MODULES = {"subprocess", "ctypes", "winreg", "socket"}

    def validate(self, code: str) -> tuple[bool, str]:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return False, f"Python 语法错误：{exc}"
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = [item.name.split(".")[0] for item in node.names] if isinstance(node, ast.Import) else [(node.module or "").split(".")[0]]
                if any(module in self.BLOCKED_MODULES for module in modules):
                    return False, f"禁止导入高风险模块：{modules}"
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
                if name in self.BLOCKED_CALLS:
                    return False, f"禁止调用高风险函数：{name}"
        return True, "安全检查通过"

    def save(self, filename: str, code: str) -> Path:
        valid, message = self.validate(code)
        if not valid:
            raise ValueError(message)
        target = FileTool().safe_output("generated", filename if filename.endswith(".py") else f"{filename}.py")
        target.write_text(code, encoding="utf-8")
        return target

    def test_run(self, path: Path) -> dict[str, str | int]:
        result = subprocess.run([sys.executable, str(path)], cwd=path.parent, capture_output=True, text=True, timeout=GENERATED_CODE_TIMEOUT_SECONDS, check=False)
        return {"returncode": result.returncode, "stdout": result.stdout[-4000:], "stderr": result.stderr[-4000:]}

