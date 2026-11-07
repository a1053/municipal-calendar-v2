"""Corre las pruebas de los módulos JS de site/ con Node (se omite si Node no está instalado)."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(shutil.which("node"), "Node no está instalado")
class SiteJsTests(unittest.TestCase):
    def test_js_modules(self):
        files = sorted((ROOT / "tests").glob("*.test.js"))
        self.assertTrue(files)
        for f in files:
            with self.subTest(f.name):
                r = subprocess.run(["node", str(f)], capture_output=True, text=True, cwd=ROOT)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertIn("OK", r.stdout)


if __name__ == "__main__":
    unittest.main()
