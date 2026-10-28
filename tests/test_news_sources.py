"""Pruebas de la recolección de noticias (feeds de ejemplo escritos a mano)."""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import news_sources as n  # noqa: E402

RSS = """<?xml version="1.0"?><rss xmlns:media="http://search.yahoo.com/mrss/"><channel>
<item><title>Municipal vence a Comunicaciones en el clásico - Prensa Libre</title><link>https://news.google.com/a</link>
<pubDate>Tue, 27 Oct 2026 15:00:00 GMT</pubDate><source url="https://prensalibre.com">Prensa Libre</source></item>
<item><title>Rojos fichan delantero</title><link>https://www.prensalibre.com/deportes/x</link>
<description>&lt;p&gt;El CSD Municipal anunció su refuerzo.&lt;/p&gt;</description>
<pubDate>Mon, 26 Oct 2026 10:00:00 -0600</pubDate>
<media:content url="https://img.test/a.jpg" medium="image"/></item>
</channel></rss>"""

ATOM = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Municipal golea en el Trébol</title>
<link href="https://emisorasunidas.com/deportes/gol"/><updated>2026-10-25T12:00:00Z</updated><summary>Partido de Liga Nacional</summary></entry></feed>"""

BING = """<rss xmlns:News="https://www.bing.com/news/search"><channel><item><title>CSD Municipal presenta técnico</title>
<link>https://www.bing.com/news/apiclick.aspx?ref=FexRss&amp;url=https%3A%2F%2Fwww.soy502.com%2Fnota&amp;c=1</link>
<pubDate>Tue, 27 Oct 2026 08:00:00 GMT</pubDate><News:Source>Soy502</News:Source></item></channel></rss>"""

GDELT = json.dumps({"articles": [
    {"url": "https://nuestro.diario/m", "title": "Municipal gana en Liga Nacional", "seendate": "20261027T120000Z", "domain": "nuestro.diario"},
    {"url": "https://x.pe/a", "title": "Deportivo Municipal empata en Lima", "seendate": "20261027T120000Z", "domain": "x.pe"},
    {"url": "", "title": "sin url"}]})


def item(title, summary="", source="", url="https://example.com/a"):
    return {"title": title, "summary": summary, "source": source, "url": url}


class ParseTests(unittest.TestCase):
    def test_rss_strips_source_suffix_and_dates(self):
        items = n.parse_feed(RSS)
        self.assertEqual(items[0]["title"], "Municipal vence a Comunicaciones en el clásico")
        self.assertEqual(items[0]["source"], "Prensa Libre")
        self.assertEqual(items[0]["published"], "2026-10-27T15:00:00Z")
        self.assertEqual(items[1]["published"], "2026-10-26T16:00:00Z")  # -0600 convertido a UTC
        self.assertEqual(items[1]["summary"], "El CSD Municipal anunció su refuerzo.")
        self.assertEqual(items[1]["image"], "https://img.test/a.jpg")

    def test_atom_and_default_source(self):
        items = n.parse_feed(ATOM, "Emisoras Unidas")
        self.assertEqual((items[0]["url"], items[0]["source"], items[0]["published"]),
                         ("https://emisorasunidas.com/deportes/gol", "Emisoras Unidas", "2026-10-25T12:00:00Z"))

    def test_bing_real_url_and_source(self):
        i = n.parse_feed(BING)[0]
        self.assertEqual(i["url"], "https://www.soy502.com/nota")
        self.assertEqual(i["source"], "Soy502")

    def test_gdelt(self):
        items = n.parse_gdelt(GDELT)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["published"], "2026-10-27T12:00:00Z")

    def test_bad_xml_raises(self):
        with self.assertRaises(Exception):
            n.parse_feed("<html>no es un feed")


class RelevanceTests(unittest.TestCase):
    def test_accepts_guatemalan_municipal(self):
        for i in [
            item("Municipal vence a Comunicaciones en el clásico"),
            item("CSD Municipal presenta técnico"),
            item("Municipal golea en el Trébol", "Partido de Liga Nacional"),
            item("Club Social y Deportivo Municipal renueva a su portero"),
            item("Municipal ficha delantero", source="Prensa Libre"),
        ]:
            self.assertTrue(n.is_relevant(i), i["title"])

    def test_rejects_other_municipals_and_politics(self):
        for i in [
            item("Deportivo Municipal empata en Lima"),
            item("Municipal Limeño gana en El Salvador"),
            item("Pérez Zeledón y Municipal Grecia igualan"),
            item("Concejo Municipal aprueba presupuesto"),
            item("Municipalidad de Guatemala repara calles", source="Prensa Libre"),
            item("Policía Municipal de Tránsito multa a conductores", source="Prensa Libre"),
            item("Los Rojos de Cincinnati ganan"),
            item("Elecciones municipales en Honduras"),
            item("Municipal vs Verdes por la Copa", source="Algún Blog Extranjero"),  # sin contexto chapín
        ]:
            self.assertFalse(n.is_relevant(i), i["title"])

    def test_sports_feed_relaxes_title_rule(self):
        i = item("Los Rojos se refuerzan", "Municipal anunció a un delantero para el Apertura")
        self.assertFalse(n.is_relevant(i))
        self.assertTrue(n.is_relevant({**i, "source": "Prensa Libre"}, sports_feed=True))


class CollectTests(unittest.TestCase):
    def test_partial_failures_do_not_stop_collection(self):
        sources = [{"id": "a", "kind": "rss", "url": "u1", "name": ""},
                   {"id": "b", "kind": "rss", "url": "u2", "name": ""},
                   {"id": "c", "kind": "gdelt", "url": "u3", "name": ""},
                   {"id": "d", "kind": "rss", "url": "u4", "name": "Emisoras Unidas", "sports": True}]
        feeds = {"u1": RSS, "u3": GDELT, "u4": ATOM}

        def fetch(url):
            if url not in feeds:
                raise RuntimeError("caído")
            return feeds[url]
        items, status = n.collect(fetch, sources)
        self.assertTrue(status["a"].startswith("ok"))
        self.assertTrue(status["b"].startswith("error"))
        titles = {i["title"] for i in items}
        self.assertIn("Municipal vence a Comunicaciones en el clásico", titles)
        self.assertIn("Municipal gana en Liga Nacional", titles)
        self.assertIn("Municipal golea en el Trébol", titles)
        self.assertNotIn("Deportivo Municipal empata en Lima", titles)

    def test_default_sources_are_unique_and_https(self):
        srcs = n.build_sources()
        self.assertEqual(len({s["id"] for s in srcs}), len(srcs))
        self.assertTrue(all(s["url"].startswith("https://") for s in srcs))

    def test_drop_old(self):
        now = datetime(2026, 10, 28, tzinfo=timezone.utc)
        items = [{"published": "2026-10-20T00:00:00Z"}, {"published": "2026-01-01T00:00:00Z"}, {"published": ""}]
        self.assertEqual(len(n.drop_old(items, now, days=150)), 2)


if __name__ == "__main__":
    unittest.main()
