"""Excel/CSV professional Agent."""

from core.cancellation import CancellationToken
from tools.excel_tool import ExcelTool


class OfficeAgent:
    def __init__(self, cancellation: CancellationToken) -> None:
        self.tool = ExcelTool(cancellation)

    def execute(self, path: str) -> dict:
        if not path:
            raise ValueError("请先上传 Excel 或 CSV 文件，再输入“整理这个 Excel”。")
        return self.tool.cleanup(path)

