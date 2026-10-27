"""Pruebas del generador de datos del sitio.

Los JSON de ejemplo están escritos a mano con la forma que usa la API de ESPN
(no son respuestas reales). Si ESPN cambia la forma, el workflow lo avisará.
"""
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_site_data as b  # noqa: E402


def comp(score_h, score_a, state="post", completed=True, name="STATUS_FULL_TIME", as_obj=True):
    wrap = (lambda v: {"value": float(v), "displayValue": str(v)}) if as_obj else (lambda v: str(v))
    return {
        "id": "1", "date": "2026-10-18T23:00Z",
        "competitions": [{
            "venue": {"fullName": "Estadio El Trébol"},
            "status": {"displayClock": "90'", "type": {"state": state, "completed": completed,
                                                       "name": name, "shortDetail": "FT"}},
            "competitors": [
                {"homeAway": "home", "score": wrap(score_h) if score_h is not None else None,
                 "team": {"id": "7258", "displayName": "Municipal", "logos": [{"href": "http://x/m.png"}]}},
                {"homeAway": "away", "score": wrap(score_a) if score_a is not None else None,
                 "team": {"id": "99", "displayName": "Antigua GFC", "logo": "http://x/a.png"}},
            ],
        }],
    }


class EventsTests(unittest.TestCase):
    def test_score_as_object_and_string(self):
        for as_obj in (True, False):
            out = b.events_from_api({"events": [comp(2, 1, as_obj=as_obj)]}, "Liga")
            m = out["1"]
            self.assertEqual((m["home"]["score"], m["away"]["score"]), (2, 1))
            self.assertEqual(b.result_for_municipal(m), "G")
            self.assertEqual(m["home"]["logo"], "http://x/m.png")
            self.assertEqual(m["away"]["logo"], "http://x/a.png")

    def test_loss_draw_and_away_perspective(self):
        m = b.events_from_api({"events": [comp(0, 3)]}, "L")["1"]
        self.assertEqual(b.result_for_municipal(m), "P")
        m = b.events_from_api({"events": [comp(1, 1)]}, "L")["1"]
        self.assertEqual(b.result_for_municipal(m), "E")
        m["home"], m["away"] = m["away"], m["home"]  # ahora Municipal es visitante
        m["home"]["score"], m["away"]["score"] = 3, 0
        self.assertEqual(b.result_for_municipal(m), "P")

    def test_upcoming_has_no_score_or_result(self):
        ev = comp(None, None, state="pre", completed=False, name="STATUS_SCHEDULED")
        m = b.events_from_api({"events": [ev]}, "L")["1"]
        self.assertEqual(m["state"], "pre")
        self.assertIsNone(m["home"]["score"])
        self.assertIsNone(b.result_for_municipal(m))

    def test_postponed_flag_and_live(self):
        ev = comp(None, None, state="post", completed=False, name="STATUS_POSTPONED")
        self.assertTrue(b.events_from_api({"events": [ev]}, "L")["1"]["postponed"])
        live = comp(1, 0, state="in", completed=False, name="STATUS_FIRST_HALF")
        self.assertEqual(b.events_from_api({"events": [live]}, "L")["1"]["state"], "in")

    def test_skips_malformed(self):
        self.assertEqual(b.events_from_api({"events": [{"id": "5"}, {"id": "6", "competitions": [{}]}]}, "L"), {})
        self.assertEqual(b.events_from_api(None, "L"), {})


class StandingsTests(unittest.TestCase):
    def entry(self, tid, name, pts, gd, rank=None):
        stats = [{"name": "points", "value": pts}, {"name": "pointDifferential", "value": gd},
                 {"name": "gamesPlayed", "value": 10}, {"name": "wins", "value": 5},
                 {"name": "ties", "value": 2}, {"name": "losses", "value": 3},
                 {"name": "pointsFor", "value": 15}, {"name": "pointsAgainst", "value": 9}]
        if rank:
            stats.append({"name": "rank", "value": rank})
        return {"team": {"id": tid, "displayName": name, "logos": [{"href": "l"}]}, "stats": stats}

    def test_orders_and_highlights(self):
        obj = {"children": [{"name": "Apertura 2026", "standings": {"entries": [
            self.entry("1", "Xelajú", 20, 4), self.entry("7258", "Municipal", 25, 8), self.entry("3", "Cobán", 20, 6)]}}]}
        g = b.standings_from_api(obj)
        rows = g[0]["rows"]
        self.assertEqual([r["name"] for r in rows], ["Municipal", "Cobán", "Xelajú"])
        self.assertEqual([r["pos"] for r in rows], [1, 2, 3])
        self.assertTrue(rows[0]["is_municipal"])
        self.assertFalse(rows[1]["is_municipal"])
        self.assertEqual((rows[0]["pj"], rows[0]["pts"], rows[0]["dg"]), (10, 25, 8))

    def test_uses_espn_rank_when_present_and_flat_shape(self):
        obj = {"standings": {"entries": [self.entry("1", "A", 30, 9, rank=2), self.entry("7258", "Municipal", 10, -1, rank=1)]}}
        rows = b.standings_from_api(obj)[0]["rows"]
        self.assertEqual(rows[0]["name"], "Municipal")

    def test_empty(self):
        self.assertEqual(b.standings_from_api({}), [])


RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Municipal golea a Antigua en el Apertura - Prensa Libre</title><link>http://g/1</link>
<pubDate>Mon, 26 Oct 2026 15:00:00 GMT</pubDate><source>Prensa Libre</source></item>
<item><title>Deportivo Municipal vence a Alianza Lima - Libero</title><link>http://g/2</link>
<pubDate>Mon, 26 Oct 2026 16:00:00 GMT</pubDate><source>Libero</source></item>
<item><title>Clima en Guatemala - Otro</title><link>http://g/3</link>
<pubDate>Mon, 26 Oct 2026 16:00:00 GMT</pubDate><source>Otro</source></item>
</channel></rss>"""


class NewsTests(unittest.TestCase):
    def test_google_filters_peru_and_unrelated(self):
        items = b.google_news(RSS)
        self.assertEqual([i["title"] for i in items], ["Municipal golea a Antigua en el Apertura"])
        self.assertEqual(items[0]["source"], "Prensa Libre")
        self.assertEqual(items[0]["published"], "2026-10-26T15:00:00Z")

    def test_espn_news_flags_municipal(self):
        obj = {"articles": [
            {"headline": "Rojos listos", "description": "Municipal prepara", "published": "2026-10-25T10:00:00Z",
             "links": {"web": {"href": "http://e/1"}}, "images": [{"url": "http://img"}]},
            {"headline": "Fecha 14", "description": "Resumen", "published": "2026-10-24T10:00:00Z",
             "links": {"web": {"href": "http://e/2"}}, "categories": [{"type": "team", "teamId": 7258}]},
            {"headline": "Antigua gana", "description": "x", "links": {"web": {"href": "http://e/3"}}},
            {"headline": "sin link"}]}
        items = b.espn_news(obj)
        self.assertEqual([i["municipal"] for i in items], [True, True, False])
        self.assertEqual(items[0]["image"], "http://img")

    def test_merge_dedupes_and_sorts(self):
        a = [{"title": "Municipal gana!", "published": "2026-10-01T00:00:00Z"}]
        c = [{"title": "Municipal   gana", "published": "2026-10-02T00:00:00Z"},
             {"title": "Otra", "published": "2026-10-03T00:00:00Z"}]
        out = b.merge_news(a, c)
        self.assertEqual([i["title"] for i in out], ["Otra", "Municipal   gana"])


class BuildTests(unittest.TestCase):
    NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)

    def run_build(self, fetch_api, get_json, prev=None):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(b.cal, "fetch_api", fetch_api), \
                mock.patch.object(b, "_get_json", get_json), \
                mock.patch("requests.get", side_effect=RuntimeError("sin red")), \
                mock.patch.object(b.cal, "load_db", return_value={}):
            code = b.build(Path(d) / "data", prev, self.NOW)
            files = {p.name: p.read_text(encoding="utf-8") for p in (Path(d) / "data").glob("*.json")}
        return code, files

    def test_aborts_without_matches(self):
        code, files = self.run_build(lambda *a: None, lambda *a: None)
        self.assertEqual(code, 1)
        self.assertEqual(files, {})

    def test_aborts_on_api_error(self):
        def boom(*a):
            raise RuntimeError("ESPN caído")
        code, files = self.run_build(boom, lambda *a: None)
        self.assertEqual(code, 1)
        self.assertEqual(files, {})

    def test_publishes_with_optional_sources_down(self):
        def fetch(slug, fixtures=False):
            return {"events": [comp(2, 1)]} if slug == "gua.1" and not fixtures else None

        def get_json(url):
            raise RuntimeError("sin red")
        code, files = self.run_build(fetch, get_json)
        self.assertEqual(code, 0)
        self.assertEqual(set(files), {"matches.json", "standings.json", "news.json", "meta.json"})
        self.assertIn('"standings": "error"', files["meta.json"])
        self.assertIn('"result": "G"', files["matches.json"])

    def test_reuses_previous_standings_when_stale(self):
        def fetch(slug, fixtures=False):
            return {"events": [comp(2, 1)]} if slug == "gua.1" and not fixtures else None

        with tempfile.TemporaryDirectory() as prev:
            (Path(prev) / "standings.json").write_text('{"groups":[{"name":"A","rows":[{"name":"X"}]}],"stale":false}')
            code, files = self.run_build(fetch, mock.Mock(side_effect=RuntimeError("x")), Path(prev))
        self.assertEqual(code, 0)
        self.assertIn('"stale": true', files["standings.json"])
        self.assertIn('"standings": "stale"', files["meta.json"])


if __name__ == "__main__":
    unittest.main()
