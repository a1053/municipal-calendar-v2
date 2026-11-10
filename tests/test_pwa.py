"""Revisa que la app instalable esté completa: manifiesto, íconos y service worker."""
import json
import re
import unittest
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"


class PwaTests(unittest.TestCase):
    def test_manifest_and_icons(self):
        m = json.loads((SITE / "manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(m["display"], "standalone")
        self.assertTrue(m["start_url"].startswith("."))
        sizes = {(i["sizes"], i.get("purpose", "any")) for i in m["icons"]}
        self.assertIn(("192x192", "any"), sizes)
        self.assertIn(("512x512", "maskable"), sizes)
        for i in m["icons"]:
            self.assertTrue((SITE / i["src"]).is_file(), i["src"])

    def test_index_links(self):
        html = (SITE / "index.html").read_text(encoding="utf-8")
        self.assertIn('rel="manifest" href="manifest.webmanifest"', html)
        for href in re.findall(r'(?:href|src)="(icons/[^"]+)"', html):
            self.assertTrue((SITE / href).is_file(), href)
        for js in re.findall(r'<script src="([^"]+)"', html):
            self.assertTrue((SITE / js).is_file(), js)

    def test_tabbar_and_menu_point_to_real_sections(self):
        html = (SITE / "index.html").read_text(encoding="utf-8")
        ids = set(re.findall(r'\sid="([^"]+)"', html))
        bar = re.search(r'<nav class="tabbar".*?</nav>', html, re.S).group(0)
        menu = re.search(r'<div class="more-menu".*?</div>', html, re.S).group(0)
        links = re.findall(r'href="#([^"/][^"]*)"', bar + menu)
        self.assertGreaterEqual(len(links), 8)
        for target in links:
            self.assertIn(target, ids, target)
        self.assertIn('href="#/calendario"', menu)
        self.assertIn('aria-controls="more-menu"', bar)

    def test_service_worker_shell_exists(self):
        sw = (SITE / "sw.js").read_text(encoding="utf-8")
        shell = re.search(r"const SHELL = \[(.*?)\];", sw, re.S).group(1)
        for path in re.findall(r'"([^"]+)"', shell):
            if path != "./":
                self.assertTrue((SITE / path).is_file(), path)
        self.assertIn("url.origin !== self.location.origin", sw)  # no toca otros sitios


if __name__ == "__main__":
    unittest.main()
