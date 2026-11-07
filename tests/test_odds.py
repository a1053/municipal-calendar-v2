"""Pruebas del modelo de probabilidades de liguilla (datos escritos a mano)."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import odds as o  # noqa: E402

NAMES = list("ABCDEFGHIJKL")


def table(pts, pj=14, gf=None, gc=None):
    return [{"team_id": str(i + 1), "name": n, "logo": None, "pos": i + 1, "pts": pts[i], "pj": pj,
             "gf": (gf or [20] * 12)[i], "gc": (gc or [20] * 12)[i], "dg": 0, "is_municipal": i == 0}
            for i, n in enumerate(NAMES)]


def event(gid, home, away, completed=False, date="2026-11-10T00:00Z"):
    return {"id": gid, "date": date, "status": {"type": {"completed": completed}},
            "competitions": [{"competitors": [{"homeAway": "home", "team": {"id": home}},
                                              {"homeAway": "away", "team": {"id": away}}]}]}


class OddsTests(unittest.TestCase):
    def test_probabilities_are_consistent(self):
        rows = table([28, 27, 24, 22, 20, 19, 17, 16, 14, 13, 10, 7])
        r = o.build_odds(rows, None, sims=3000)
        self.assertEqual(r["fixtures"], "aleatorio")
        self.assertEqual(r["fixtures_total"], 48)
        self.assertAlmostEqual(sum(t["p_qualify"] for t in r["teams"]), 600, delta=1.5)
        self.assertAlmostEqual(sum(t["p_direct"] for t in r["teams"]), 200, delta=1.5)
        self.assertAlmostEqual(sum(t["p_first"] for t in r["teams"]), 100, delta=1.5)
        for t in r["teams"]:
            self.assertAlmostEqual(sum(t["pos_dist"]), 100, delta=1.5)
        q = {t["name"]: t["p_qualify"] for t in r["teams"]}
        self.assertGreater(q["A"], q["F"])
        self.assertGreater(q["F"], q["L"])

    def test_clinched_and_eliminated(self):
        rows = table([60, 50, 40, 30, 20, 10, 5, 4, 3, 2, 1, 0], pj=20)
        r = o.build_odds(rows, None, sims=2000)
        by = {t["name"]: t for t in r["teams"]}
        self.assertEqual(by["A"]["p_qualify"], 100.0)
        self.assertEqual(by["A"]["p_direct"], 100.0)
        self.assertEqual(by["L"]["p_qualify"], 0.0)

    def test_deterministic_for_same_data(self):
        rows = table([28, 27, 24, 22, 20, 19, 17, 16, 14, 13, 10, 7])
        a, b = o.build_odds(rows, None, sims=500), o.build_odds(rows, None, sims=500)
        self.assertEqual(a["teams"], b["teams"])

    def test_better_attack_raises_odds(self):
        pts = [20] * 12
        weak = o.build_odds(table(pts, gf=[10] + [20] * 11), None, sims=4000)["teams"][0]["p_qualify"]
        strong = o.build_odds(table(pts, gf=[35] + [20] * 11), None, sims=4000)["teams"][0]["p_qualify"]
        self.assertGreater(strong, weak)

    def test_scoreboard_fixtures(self):
        ids = {str(i) for i in range(1, 13)}
        obj = {"events": [event("1", "1", "2"), event("2", "3", "4", completed=True),
                          event("3", "1", "99"), event("1", "1", "2")]}
        self.assertEqual(o.fixtures_from_scoreboard(obj, ids), [("1", "2")])

    def test_fill_missing_and_cap(self):
        rows = table([10] * 12, pj=20)  # 2 por equipo = 12 partidos
        rng = random.Random(1)
        known = [("1", "2")] * 5  # el calendario repetido no puede pasar de lo que falta
        fx, mode = o.complete_fixtures(rows, known, 22, rng)
        self.assertEqual(mode, "mixto")
        self.assertEqual(len(fx), 12)
        games = {}
        for h, a in fx:
            self.assertNotEqual(h, a)
            games[h] = games.get(h, 0) + 1
            games[a] = games.get(a, 0) + 1
        self.assertTrue(all(v == 2 for v in games.values()))
        full = [event(str(i), str(i % 12 + 1), str((i + 1) % 12 + 1)) for i in range(12)]
        fx, mode = o.complete_fixtures(rows, o.fixtures_from_scoreboard({"events": full}, {r["team_id"] for r in rows}), 22, rng)
        self.assertEqual(mode, "calendario")

    def test_bad_table(self):
        self.assertIsNone(o.build_odds(table([None] * 12), None))
        self.assertIsNone(o.build_odds(table([1] * 12)[:5], None))


if __name__ == "__main__":
    unittest.main()
