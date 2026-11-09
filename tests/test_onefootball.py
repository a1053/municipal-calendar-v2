"""Pruebas del complemento de OneFootball (páginas de ejemplo escritas a mano, no reales)."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_site_data as b  # noqa: E402
import onefootball as of  # noqa: E402


def player(name, n):
    return {"name": name, "nickName": name, "jerseyNumber": n, "image": {}, "link": {}}


def match_html(kick="2026-09-14T01:00:00Z", hs="2", as_="2", period=11, events=True, lineup=True, home="CSD Municipal", away="CD Malacateco"):
    evs = [
        {"teamSide": 1, "name": "Gol", "timeline": "38'", "type": {"$case": "goal", "goal": {"type": 0, "scorer": {"name": "Elicer Quiñónes"}}}},
        {"teamSide": 0, "name": "Penalti", "timeline": "90'+3", "type": {"$case": "goal", "goal": {"type": 2, "scorer": {"name": "Pedro Altán"}}}},
        {"teamSide": 0, "name": "Tarjeta amarilla", "timeline": "62'", "type": {"$case": "card", "card": {"type": 0, "player": {"name": "César Archila"}}}},
        {"teamSide": 1, "name": "Tarjeta roja", "timeline": "70'", "type": {"$case": "card", "card": {"type": 2, "player": {"name": "José Longo"}}}},
        {"teamSide": 0, "name": "Sustitución", "timeline": "46'", "type": {"$case": "substitution", "substitution": {"playerIn": {"name": "José Martínez"}, "playerOut": {"name": "Alejandro Cabeza"}}}},
        {"teamSide": 0, "name": "Otra cosa", "timeline": "50'", "type": {"$case": "var", "var": {}}},
    ]
    flat = lambda ps: {"$case": "flat", "flat": {"players": ps}}  # noqa: E731
    lu = {"title": "ALINEACIONES", "variant": {"$case": "lineup", "lineup": {
        "homeTeam": {"teamName": home, "variant": flat([player("Carlos Aguilar", 23), player("Pedro Altán", 10)])},
        "awayTeam": {"teamName": away, "variant": flat([player("Jonathan Castañon", 12)])}}}} if lineup else \
        {"variant": {"$case": "empty", "empty": {"message": "aún no"}}}
    nd = {"props": {"pageProps": {"containers": [
        {"x": {"matchScore": {"competition": {"name": "Liga Nacional de Guatemala"}, "kickoff": {"utcTimestamp": kick},
                              "timePeriod": "Fin del partido" if period == 11 else "", "period": period,
                              "homeTeam": {"name": home, "score": hs}, "awayTeam": {"name": away, "score": as_}}}},
        {"x": {"matchEvents": {"events": evs if events else []}}},
        {"x": {"matchLineup": lu}}]}}}
    return f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(nd)}</script></html>'


def team_html(*ids):
    return "<html>" + "".join(f'<a href="/es/partido/{i}">x</a>' for i in ids) + "</html>"


def espn(mid="10", start="2026-09-14T01:00:00Z", state="post", home=("7258", "Municipal"), away=("99", "Malacateco")):
    return {"id": mid, "start": start, "state": state, "postponed": False, "slug": "gua.1", "competition": "Liga", "clock": "", "venue": "",
            "home": {"id": home[0], "name": home[1], "score": 2, "logo": ""}, "away": {"id": away[0], "name": away[1], "score": 2, "logo": ""}}


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.m = of.parse_match(of._next_data(match_html()), "5")

    def test_match_basics(self):
        m = self.m
        self.assertEqual((m["home"], m["away"], m["hs"], m["as"], m["finished"]), ("CSD Municipal", "CD Malacateco", 2, 2, True))
        self.assertEqual(m["url"], "https://onefootball.com/es/partido/5")

    def test_events_use_the_same_shape_as_espn(self):
        ev = self.m["events"]
        self.assertEqual([e["min"] for e in ev], ["38'", "46'", "62'", "70'", "90'+3"])  # en orden de minuto
        self.assertEqual([e["sort"] for e in ev], sorted(e["sort"] for e in ev))
        kinds = {(e["kind"], e["player"]) for e in ev}
        self.assertIn(("goal", "Elicer Quiñónes"), kinds)
        self.assertIn(("yellow", "César Archila"), kinds)
        self.assertIn(("red", "José Longo"), kinds)
        pen = next(e for e in ev if e["player"] == "Pedro Altán")
        self.assertTrue(pen["penalty"])
        self.assertEqual(pen["sort"], 90.003)
        sub = next(e for e in ev if e["kind"] == "sub")
        self.assertEqual(sub["text"], "Entra José Martínez, sale Alejandro Cabeza")
        self.assertEqual(len(ev), 5)  # el tipo desconocido se ignora

    def test_lineups(self):
        lu = self.m["lineups"]
        self.assertEqual([x["home_away"] for x in lu], ["home", "away"])
        self.assertEqual(lu[0]["players"][0]["jersey"], "23")
        self.assertTrue(all(p["starter"] for x in lu for p in x["players"]))

    def test_lineups_not_published_yet(self):
        m = of.parse_match(of._next_data(match_html(lineup=False)), "6")
        self.assertEqual(m["lineups"], [])

    def test_junk_page(self):
        self.assertIsNone(of._next_data("<html></html>"))
        self.assertIsNone(of.parse_match({"props": {}}, "1"))


class LinkTests(unittest.TestCase):
    def test_links_by_time_and_team_names(self):
        o = of.parse_match(of._next_data(match_html()), "5")
        self.assertEqual(list(of.link([espn()], [o])), ["10"])

    def test_no_link_when_time_or_team_differ(self):
        o = of.parse_match(of._next_data(match_html()), "5")
        self.assertEqual(of.link([espn(start="2026-09-20T01:00:00Z")], [o]), {})
        self.assertEqual(of.link([espn(away=("98", "Antigua GFC"))], [o]), {})
        self.assertEqual(of.link([espn(state="pre")], [o]), {})


class CollectTests(unittest.TestCase):
    def fetcher(self, calls):
        pages = {"/resultados": team_html(5), "/partidos": team_html(6), "": team_html(5)}

        def fetch(url):
            calls.append(url)
            if "/partido/5" in url:
                return match_html()
            if "/partido/6" in url:
                return match_html(kick="2026-12-01T01:00:00Z", hs="-", as_="-", period=1, events=False, lineup=False)
            return pages[url.replace(of.BASE + of.TEAM_PATH, "")]
        return fetch

    def test_collect_links_retags_and_caches(self):
        calls = []
        res, cache = of.collect([espn()], None, fetch=self.fetcher(calls), sleep=lambda s: None)
        self.assertEqual(list(res), ["10"])
        r = res["10"]
        self.assertEqual({e["team_id"] for e in r["events"]}, {"7258", "99"})   # ids de ESPN
        self.assertEqual(r["lineups"][0]["team_id"], "7258")
        self.assertEqual(r["lineups"][1]["team"], "Malacateco")
        self.assertIn("5", cache["matches"])
        # segunda corrida: el partido terminado y completo no se vuelve a pedir
        calls.clear()
        of.collect([espn()], cache, fetch=self.fetcher(calls), sleep=lambda s: None)
        self.assertFalse([c for c in calls if "/partido/5" in c])
        self.assertTrue([c for c in calls if "/partido/6" in c])  # el pendiente sí se revisa

    def test_failures_never_raise(self):
        def boom(url):
            raise OSError("sin red")
        res, cache = of.collect([espn()], {"matches": {"5": of.parse_match(of._next_data(match_html()), "5")}}, fetch=boom, sleep=lambda s: None)
        self.assertEqual(list(res), ["10"])   # sigue sirviendo lo guardado
        self.assertIn("5", cache["matches"])


class BuildTests(unittest.TestCase):
    NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)

    def test_build_details_adds_of_without_touching_espn_keys(self):
        m = espn()
        extra = {"of_id": "5", "url": "u", "finished": True, "events": [{"kind": "goal"}], "lineups": []}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(b, "_get_json", return_value={}):
            out = Path(d)
            b.build_details([m], {}, out, self.NOW, {}, {"10": extra})
            page = json.loads((out / "match" / "10.json").read_text(encoding="utf-8"))
        self.assertEqual(page["of"], extra)
        self.assertEqual((page["events"], page["lineups"], page["stats"], page["commentary"]), ([], [], [], []))  # ESPN intacto
        self.assertTrue(m["detail"])


if __name__ == "__main__":
    unittest.main()
