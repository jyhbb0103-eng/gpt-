"""Dabao Agent command-line entry point."""

import argparse
from agents.orchestrator import OrchestratorAgent


def main() -> int:
    parser = argparse.ArgumentParser(description="Dabao Agent 2.0")
    parser.add_argument("command", nargs="?", default="扫描今天强势板块")
    args = parser.parse_args()
    result = OrchestratorAgent().execute(args.command)
    print(result.message)
    if result.report_path:
        print(f"输出：{result.report_path}")
    return 0 if result.state.value in {"COMPLETED", "WAITING_USER"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

