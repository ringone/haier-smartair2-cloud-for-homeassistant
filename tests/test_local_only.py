"""Local-only regressions run in isolation from legacy global HA stubs."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LocalOnlyTests(unittest.TestCase):
    def test_local_only_behaviors(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tests" / "local_only_worker.py")],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
