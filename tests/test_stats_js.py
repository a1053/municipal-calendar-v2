"""Corre las pruebas de site/stats.js con Node (se omite si Node no está instalado)."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("node"), "Node no está instalado")
class StatsJsTests(unittest.TestCase):
    def test_stats_js(self):
        r = subprocess.run(["node", str(ROOT / "tests" / "stats.test.js")], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("OK", r.stdout)


if __name__ == "__main__":
    unittest.main()
