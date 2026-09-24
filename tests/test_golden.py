"""Регрессия: вывод CLI для всех шаблонов и Tier совпадает с эталоном."""

import subprocess
import sys
import unittest
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "golden"
ROOT = GOLDEN_DIR.parent.parent


class TestGoldenCli(unittest.TestCase):
    def test_cli_output_matches_golden(self):
        files = sorted(GOLDEN_DIR.glob("cli_*_tier*.txt"))
        self.assertTrue(files)
        for path in files:
            template, tier = path.stem.removeprefix("cli_").rsplit("_tier", 1)
            with self.subTest(template=template, tier=tier):
                out = subprocess.run(
                    [sys.executable, "-m", "kontur", "--cli", "--template", template, "--tier", tier],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    cwd=ROOT,
                    check=False,
                )
                self.assertEqual(out.stdout + out.stderr, path.read_text(encoding="utf-8"))
