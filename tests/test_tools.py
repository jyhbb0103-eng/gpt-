import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import tools


class ToolTests(unittest.TestCase):
    def test_calculate(self):
        self.assertEqual(tools.calculate("(25 + 3) * 4")["result"], 112)

    def test_calculator_rejects_code(self):
        with self.assertRaises(ValueError):
            tools.calculate("__import__('os').system('echo unsafe')")

    def test_notes_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(tools, "NOTES_DIR", Path(temp_dir)):
                tools.write_note("计划", "学习智能体")
                self.assertEqual(tools.read_note("计划")["content"], "学习智能体")
                self.assertEqual(tools.list_notes()["notes"], ["计划"])


if __name__ == "__main__":
    unittest.main()
