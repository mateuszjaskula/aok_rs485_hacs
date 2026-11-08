"""Check the UI action-to-motor opcode routing without Home Assistant installed."""
import ast
from pathlib import Path
import unittest

COVER_PATH = Path(__file__).resolve().parents[1] / "custom_components" / "aok_rs485" / "cover.py"

class TestCoverDirection(unittest.TestCase):
    def test_open_close_actions_reversed_only_at_cover_layer(self):
        tree = ast.parse(COVER_PATH.read_text(encoding="utf-8"))
        cover = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AokCover")
        for method_name, expected_frame, expected_direction in (
            ("async_open_cover", "close_frame", "opening"),
            ("async_close_cover", "open_frame", "closing"),
            ("async_stop_cover", "stop_frame", None),
        ):
            method = next(m for m in cover.body if isinstance(m, ast.AsyncFunctionDef) and m.name == method_name)
            send = next(n for n in ast.walk(method) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "_send")
            self.assertEqual(send.args[0].func.id, expected_frame)
            self.assertEqual(ast.literal_eval(send.args[1]), expected_direction)

if __name__ == "__main__":
    unittest.main()
