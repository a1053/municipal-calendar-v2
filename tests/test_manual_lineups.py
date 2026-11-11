import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import manual_lineups as ml  # noqa: E402

ENTRY = {"date": "2026-10-28", "rival": "Comunicaciones", "formation": "4-3-1-2",
         "starters": [{"jersey": str(i), "name": f"J{i}"} for i in range(1, 12)],
         "bench": [{"jersey": "52", "name": "Aubrey David", "pos": "CEN", "marks": ["in", "goal"]}]}
M = {"home": {"id": "7258", "name": "Municipal"}, "away": {"id": "9", "name": "Comunicaciones"}}


class ManualLineupsTests(unittest.TestCase):
    def test_real_file_is_valid(self):
        entries = ml.load()
        self.assertTrue(entries)
        self.assertEqual(entries[0]["formation"], "4-3-1-2")
        self.assertEqual(sum(int(n) for n in entries[0]["formation"].split("-")), 10)

    def test_find_by_day_and_rival(self):
        at = datetime(2026, 10, 29, 2, 0, tzinfo=timezone.utc)      # 20:00 del 28 en Guatemala
        self.assertIs(ml.find([ENTRY], M, at, "7258"), ENTRY)
        other = {"home": M["home"], "away": {"id": "5", "name": "Antigua GFC"}}
        self.assertIsNone(ml.find([ENTRY], other, at, "7258"))
        far = datetime(2026, 11, 20, 2, 0, tzinfo=timezone.utc)
        self.assertIsNone(ml.find([ENTRY], M, far, "7258"))

    def test_apply_replaces_only_our_lineup(self):
        lus = [{"team_id": "7258", "players": []}, {"team_id": "9", "players": [1]}]
        out = ml.apply(lus, ENTRY, M, "7258")
        self.assertEqual([lu["team_id"] for lu in out], ["9", "7258"])
        mine = out[1]
        self.assertTrue(mine["manual"])
        self.assertEqual([p["place"] for p in mine["players"] if p["starter"]], list(range(1, 12)))
        self.assertTrue(mine["players"][-1]["played"])

    def test_rival_lineup_is_optional(self):
        entry = {**ENTRY, "rival_formation": "4-2-3-1", "rival_starters": [{"jersey": str(i), "name": f"R{i}"} for i in range(1, 12)]}
        out = ml.apply([{"team_id": "9", "players": [1]}], entry, M, "7258")
        by = {lu["team_id"]: lu for lu in out}
        self.assertEqual(by["9"]["formation"], "4-2-3-1")
        self.assertEqual(by["9"]["players"][0]["name"], "R1")
        self.assertEqual(by["9"]["home_away"], "away")
        self.assertEqual(by["7258"]["formation"], "4-3-1-2")

    def test_real_file_has_xelaju(self):
        e = [x for x in ml.load() if x["rival"] == "Xelajú"][0]
        self.assertEqual(sum(int(n) for n in e["rival_formation"].split("-")), 10)
        self.assertEqual(len(e["rival_bench"]), 9)

    def test_events_for_the_timeline(self):
        entry = {**ENTRY, "events": [
            {"min": "34'", "side": "rival", "kind": "goal", "player": "Yori", "assist": "Lemus"},
            {"min": "12'", "side": "me", "kind": "goal", "player": "Mena", "assist": "Muñoz"},
            {"min": "46'", "side": "me", "kind": "sub", "player": "A", "player_out": "B"}]}
        ev = ml.to_events(entry, M, "7258")
        self.assertEqual([e["min"] for e in ev], ["12'", "34'", "46'"])
        self.assertEqual((ev[0]["team_id"], ev[0]["assist"]), ("7258", "Muñoz"))
        self.assertEqual(ev[1]["team_id"], "9")
        self.assertEqual(ev[2]["text"], "Entra A, sale B")

    def test_merge_prefers_onefootball_and_adds_assists(self):
        manual = [{"min": "12'", "kind": "goal", "team_id": "7258", "player": "José Mena", "assist": "Rudy Muñoz"},
                  {"min": "99'", "kind": "yellow", "team_id": "7258", "player": "Solo A Mano"}]
        of = [{"min": "12'", "kind": "goal", "team_id": "7258", "player": "Jose Mena", "assist": ""},
              {"min": "60'", "kind": "sub", "team_id": "7258", "player": "John Méndez", "player_out": "Rudy Muñoz"}]
        out = ml.merge_events(of, manual)
        self.assertEqual(out[0]["assist"], "Rudy Muñoz")
        self.assertEqual(len(out), 2)                                   # lo que solo está a mano no entra
        self.assertEqual(ml.merge_events([], manual), manual)           # sin OneFootball, vale lo manual

    def test_names_come_from_official_lineup_by_jersey(self):
        official = [{"team_id": "9", "players": [{"name": "Juan Winter", "jersey": "77", "id": "5"}, {"name": "Otro", "jersey": "5"}, {"name": "Doble", "jersey": "5"}]}]
        entry = {**ENTRY, "rival_starters": [{"jersey": "77", "name": "Winter"}] + [{"jersey": str(i), "name": f"R{i}"} for i in range(5, 15)]}
        out = {lu["team_id"]: lu for lu in ml.apply([], entry, M, "7258", official)}
        names = [p["name"] for p in out["9"]["players"]]
        self.assertEqual(names[0], "Juan Winter")                        # camiseta 77: nombre de OneFootball
        self.assertIn("R5", names)                                       # camiseta repetida en la fuente: no se toca
        self.assertEqual(out["7258"]["players"][0]["name"], "J1")        # sin alineación oficial de ese equipo: lo escrito a mano

    def test_real_file_guastatoya(self):
        e = [x for x in ml.load() if x["rival"] == "Guastatoya"][0]
        self.assertEqual(sum(int(n) for n in e["formation"].split("-")), 10)
        self.assertEqual(sum(int(n) for n in e["rival_formation"].split("-")), 10)
        self.assertEqual(sum(1 for x in e["events"] if x["kind"] == "goal"), 2)

    def test_load_ignores_bad_files(self):
        self.assertEqual(ml.load(Path("/no/existe.json")), [])


if __name__ == "__main__":
    unittest.main()
