"""Pruebas del detalle de partidos, jugadores, rival y vista previa.

Los resúmenes de ejemplo están escritos a mano con la forma que usa ESPN
(no son respuestas reales).
"""
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_site_data as b  # noqa: E402
import site_details as sd  # noqa: E402

MUNI, RIVAL = "7258", "99"


def side(tid, name, score=None):
    return {"id": tid, "name": name, "logo": "", "score": score}


def match(mid="1", state="post", hs=2, as_=1, start="2026-10-20T00:00:00Z", home=(MUNI, "Municipal"), away=(RIVAL, "Antigua GFC")):
    return {"id": mid, "state": state, "postponed": False, "start": start, "competition": "Liga Nacional de Guatemala",
            "slug": "gua.1", "clock": "", "venue": "", "home": side(*home, hs), "away": side(*away, as_)}


def ev(kind, minute, tid, names, clock=0, text=""):
    return {"type": {"type": kind}, "clock": {"displayValue": minute, "value": clock}, "team": {"id": tid, "displayName": "x"},
            "participants": [{"athlete": {"id": n[0], "displayName": n[1]}} for n in names], "text": text}


SUMMARY = {
    "keyEvents": [
        ev("yellow-card", "30'", MUNI, [("11", "Ruiz")], 1800),
        ev("goal---header", "12'", MUNI, [("10", "Pérez"), ("11", "Ruiz")], 720),
        ev("penalty---scored", "70'", RIVAL, [("50", "Gómez")], 4200),
        ev("own-goal", "80'", RIVAL, [("51", "López")], 4800),
        ev("substitution", "60'", MUNI, [("12", "Soto"), ("10", "Pérez")], 3600, "Cambio, Municipal. Soto por Pérez."),
        ev("kickoff", "0'", MUNI, [], 0),
        ev("red-card", "88'", RIVAL, [("52", "Díaz")], 5280),
    ],
    "rosters": [
        {"homeAway": "home", "team": {"id": MUNI, "displayName": "Municipal"}, "formation": "4-3-3", "roster": [
            {"starter": True, "jersey": "10", "athlete": {"id": "10", "displayName": "Pérez"}, "position": {"abbreviation": "DEL"}},
            {"starter": True, "jersey": "11", "athlete": {"id": "11", "displayName": "Ruiz"}, "position": {"abbreviation": "MED"}},
            {"starter": False, "jersey": "12", "athlete": {"id": "12", "displayName": "Soto"}, "subbedIn": {"didSub": True}},
            {"starter": False, "jersey": "13", "athlete": {"id": "13", "displayName": "Banca"}}]},
        {"homeAway": "away", "team": {"id": RIVAL, "displayName": "Antigua GFC"}, "formation": {"summary": "4-4-2"},
         "roster": [{"starter": True, "jersey": "9", "athlete": {"id": "50", "displayName": "Gómez"}}]},
    ],
    "boxscore": {"teams": [
        {"team": {"id": MUNI}, "statistics": [{"name": "possessionPct", "displayValue": "55.4"}, {"name": "totalShots", "displayValue": "14"}]},
        {"team": {"id": RIVAL}, "statistics": [{"name": "possessionPct", "displayValue": "44.6"}, {"name": "totalShots", "displayValue": "6"}, {"name": "x", "displayValue": "1"}]},
    ]},
}


class ParseTests(unittest.TestCase):
    def test_events_classified_sorted_and_filtered(self):
        evs = sd.parse_events(SUMMARY)
        self.assertEqual([e["kind"] for e in evs], ["goal", "yellow", "sub", "goal", "own_goal", "red"])
        goal = evs[0]
        self.assertEqual((goal["player"], goal["assist"], goal["team_id"]), ("Pérez", "Ruiz", MUNI))
        self.assertTrue(evs[3]["penalty"])
        self.assertEqual(evs[2]["text"], "Cambio, Municipal. Soto por Pérez.")
        self.assertEqual(evs[1]["assist"], "")

    def test_lineups_formation_and_played(self):
        lu = sd.parse_lineups(SUMMARY)
        self.assertEqual([l["formation"] for l in lu], ["4-3-3", "4-4-2"])
        played = {p["name"]: p["played"] for p in lu[0]["players"]}
        self.assertEqual(played, {"Pérez": True, "Ruiz": True, "Soto": True, "Banca": False})

    def test_stats_aligned_by_team_and_labeled(self):
        st = sd.parse_stats(SUMMARY, MUNI, RIVAL)
        self.assertEqual([s["label"] for s in st], ["Posesión", "Tiros"])
        self.assertEqual((st[0]["home"], st[0]["away"], st[0]["home_v"]), ("55.4%", "44.6%", 55.4))
        self.assertEqual((st[1]["home"], st[1]["away"]), ("14", "6"))

    def test_summary_without_data(self):
        d = sd.parse_summary({}, match())
        self.assertFalse(d["has_data"])
        self.assertFalse(sd.parse_summary(None, match())["has_data"])


class PlayersTests(unittest.TestCase):
    def test_totals_across_matches(self):
        d = sd.parse_summary(SUMMARY, match())
        rows = sd.build_players([d, d], MUNI)
        by = {r["name"]: r for r in rows}
        self.assertEqual(rows[0]["name"], "Pérez")  # más goles primero
        self.assertEqual((by["Pérez"]["goals"], by["Pérez"]["pj"], by["Pérez"]["starts"]), (2, 2, 2))
        self.assertEqual((by["Ruiz"]["assists"], by["Ruiz"]["yellow"]), (2, 2))
        self.assertEqual((by["Soto"]["pj"], by["Soto"]["starts"]), (2, 0))
        self.assertEqual(by["Banca"]["pj"], 0)
        self.assertNotIn("Gómez", by)  # rival excluido

    def test_empty(self):
        self.assertEqual(sd.build_players([], MUNI), [])


class RivalTests(unittest.TestCase):
    def test_rival_block(self):
        nxt = match("9", "pre", None, None, home=(MUNI, "Municipal"), away=(RIVAL, "Antigua GFC"))
        season = [match("1", hs=2, as_=0), nxt]
        rival_events = {"a": match("a", hs=1, as_=1, start="2026-10-01T00:00:00Z", home=(RIVAL, "Antigua GFC"), away=("5", "Xelajú")),
                        "b": match("b", hs=0, as_=2, start="2026-10-08T00:00:00Z", home=("6", "Cobán"), away=(RIVAL, "Antigua GFC"))}
        standings = {"groups": [{"rows": [{"team_id": RIVAL, "pos": 3, "pts": 24, "pj": 12}]}]}
        r = sd.build_rival(nxt, MUNI, standings, rival_events, season)
        self.assertEqual((r["name"], r["pos"], r["pts"]), ("Antigua GFC", 3, 24))
        self.assertEqual([f["result"] for f in r["form"]], ["E", "G"])
        self.assertEqual(r["meetings"][0]["score"], "2-0")

    def test_no_data_returns_none(self):
        nxt = match("9", "pre", None, None)
        self.assertIsNone(sd.build_rival(nxt, MUNI, {}, {}, [nxt]))


class ShareTests(unittest.TestCase):
    NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)

    def test_next_match_text_in_guatemala_time(self):
        nxt = match("9", "pre", None, None, start="2026-10-29T02:00:00Z")  # 8:00 p. m. del 28 en Guatemala
        t = sd.share_text([match("1"), nxt], self.NOW)
        self.assertEqual(t["kicker"], "Próximo partido")
        self.assertIn("miércoles 28 de octubre, 8:00 p. m.", t["small"])
        self.assertEqual(t["big"], "Municipal vs Antigua GFC")

    def test_live_wins_over_next_and_last_result_fallback(self):
        live = match("2", "in", 1, 0)
        live["clock"] = "63'"
        t = sd.share_text([live, match("9", "pre", None, None, start="2026-10-29T02:00:00Z")], self.NOW)
        self.assertEqual((t["kicker"], t["big"]), ("En vivo 63'", "Municipal 1 - 0 Antigua GFC"))
        t = sd.share_text([match("1")], self.NOW)
        self.assertEqual(t["kicker"], "Último resultado")

    def test_png_and_inject(self):
        t = sd.share_text([match("1")], self.NOW)
        with tempfile.TemporaryDirectory() as d:
            png = Path(d) / "og.png"
            self.assertTrue(sd.make_og_png(png, t))
            from PIL import Image
            self.assertEqual(Image.open(png).size, (1200, 630))
            idx = Path(d) / "index.html"
            idx.write_text("<head><!--og-->\n<meta property=\"og:title\" content=\"x\">\n<!--/og--></head>", encoding="utf-8")
            sd.inject_og(idx, "https://a.github.io/repo", {**t, "title": 'Título "con comillas"'}, True)
            html = idx.read_text(encoding="utf-8")
            self.assertRegex(html, r'content="https://a\.github\.io/repo/og\.png\?v=[0-9a-f]{8}"')
            self.assertIn("&quot;con comillas&quot;", html)
            self.assertEqual(html.count("<!--og-->"), 1)
            sd.inject_og(idx, "https://a.github.io/repo/", t, False)  # idempotente, sin imagen
            self.assertNotIn("og:image", idx.read_text(encoding="utf-8"))


class BuildDetailsTests(unittest.TestCase):
    NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)

    def test_end_to_end_writes_match_pages_players_and_og(self):
        def comp(mid, date, state, hs, as_):
            wrap = lambda v: None if v is None else {"value": float(v)}
            return {"id": mid, "date": date, "competitions": [{"status": {"type": {"state": state, "completed": state == "post", "name": ""}},
                    "competitors": [{"homeAway": "home", "score": wrap(hs), "team": {"id": MUNI, "displayName": "Municipal"}},
                                    {"homeAway": "away", "score": wrap(as_), "team": {"id": RIVAL, "displayName": "Antigua GFC"}}]}]}

        def fetch(slug, fixtures=False):
            if slug != "gua.1":
                return None
            return {"events": [comp("2", "2026-11-05T02:00Z", "pre", None, None)]} if fixtures else {"events": [comp("1", "2026-10-20T00:00Z", "post", 2, 1)]}

        def get_json(url):
            if "/summary?event=1" in url:
                return SUMMARY
            if "/summary?event=2" in url:
                return {}
            if "standings" in url:
                return {"children": [{"standings": {"entries": []}}]}
            raise RuntimeError("sin red")

        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(b.cal, "fetch_api", fetch), mock.patch.object(b, "_get_json", get_json), \
                mock.patch("requests.get", side_effect=RuntimeError("sin red")), mock.patch.object(b.cal, "load_db", return_value={}):
            idx = Path(d) / "site" / "index.html"
            idx.parent.mkdir()
            idx.write_text("<head><!--og--><!--/og--></head>", encoding="utf-8")
            out = idx.parent / "data"
            code = b.build(out, None, self.NOW, site_url="https://a.github.io/repo", index_path=idx)
            self.assertEqual(code, 0)
            self.assertTrue((out / "match" / "1.json").exists())
            self.assertTrue((idx.parent / "og.png").exists())
            self.assertIn("Próximo partido: Municipal vs Antigua GFC", idx.read_text(encoding="utf-8"))
            import json
            matches = json.loads((out / "matches.json").read_text(encoding="utf-8"))["matches"]
            self.assertEqual({m["id"]: m.get("detail") for m in matches}, {"1": True, "2": True})  # 2 tiene rival
            players = json.loads((out / "players.json").read_text(encoding="utf-8"))["players"]
            self.assertEqual(players[0]["name"], "Pérez")
            nxt = json.loads((out / "match" / "2.json").read_text(encoding="utf-8"))
            self.assertEqual(nxt["rival"]["meetings"][0]["score"], "2-1")


if __name__ == "__main__":
    unittest.main()
