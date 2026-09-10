from pathlib import Path
import pandas as pd

from core.cancellation import CancellationToken
from tools.excel_tool import ExcelTool


def test_excel_read_and_cleanup(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "input.csv"
    pd.DataFrame({" name ": ["a", "a", "b"], "value": [2, 2, 1]}).to_csv(source, index=False)
    tool = ExcelTool(CancellationToken())
    monkeypatch.setattr(tool.files, "safe_output", lambda folder, filename: tmp_path / filename)
    result = tool.cleanup(str(source), sort_column="value")
    assert Path(result["output"]).exists()
    assert result["sheets"][0]["removed"] == 1

