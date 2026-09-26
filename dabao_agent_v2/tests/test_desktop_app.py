"""Tests for the desktop shell without creating a real GUI window."""

from pathlib import Path

import desktop_app


class FakeProcess:
    def __init__(self, exit_code=None):
        self.exit_code = exit_code

    def poll(self):
        return self.exit_code


def test_find_project_root_from_environment(tmp_path, monkeypatch):
    (tmp_path / "app.py").write_text("", encoding="utf-8")
    monkeypatch.setenv("DABAO_PROJECT_ROOT", str(tmp_path))
    assert desktop_app.find_project_root() == tmp_path.resolve()


def test_wait_for_streamlit_ready(monkeypatch):
    monkeypatch.setattr(desktop_app, "service_is_ready", lambda: True)
    desktop_app.wait_for_streamlit(FakeProcess(), timeout=0.1)


def test_wait_for_streamlit_detects_early_exit(monkeypatch):
    monkeypatch.setattr(desktop_app, "service_is_ready", lambda: False)
    try:
        desktop_app.wait_for_streamlit(FakeProcess(exit_code=2), timeout=0.1)
    except RuntimeError as exc:
        assert "退出代码：2" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
