"""Pruebas del plantel (datos de ejemplo escritos a mano con la forma de ESPN, no respuestas reales)."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import roster as r  # noqa: E402


def ath(name, pos, jersey, age=25, country="Guatemala", head=None, injuries=None, height=70.0, weight=160.0, **extra):
    a = {"id": name[:3], "displayName": name, "shortName": name, "jersey": jersey, "age": age, "citizenship": country,
         "position": {"abbreviation": pos, "displayName": "x"}, "headshot": head, "injuries": injuries or [],
         "flag": {"href": "https://f/gua.png", "alt": country}, "height": height, "weight": weight, "status": {"type": "active"}}
    a.update(extra)
    return a


RAW = {"season": {"displayName": "2026-27 Liga Nacional de Guatemala"}, "athletes": [
    ath("Delantero Uno", "F", "9", country="Trinidad and Tobago", head={"href": "https://h/9.png"}),
    ath("Portero Uno", "G", "1", height=75.0, weight=174.0),
    ath("Medio Cabeza", "M", "10", age=None, country=None),
    ath("Defensa Dos", "D", "3", injuries=[{"status": "Out", "shortComment": "Esguince de tobillo"}]),
    ath("Defensa Uno", "D", "2"),
    ath("Sin Número", "D", "", age=3),
    {"displayName": ""}, "raro",
]}


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.p = r.parse_roster(RAW)
        self.by = {x["name"]: x for x in self.p}

    def test_orders_by_position_then_number(self):
        self.assertEqual([x["name"] for x in self.p],
                         ["Portero Uno", "Defensa Uno", "Defensa Dos", "Sin Número", "Medio Cabeza", "Delantero Uno"])

    def test_fields(self):
        gk = self.by["Portero Uno"]
        self.assertEqual((gk["pos"], gk["pos_group"], gk["jersey"], gk["age"]), ("Portero", "Porteros", "1", 25))
        self.assertEqual((gk["height_cm"], gk["weight_kg"]), (191, 79))   # 75 pulgadas, 174 libras
        fw = self.by["Delantero Uno"]
        self.assertEqual((fw["country"], fw["photo"]), ("Trinidad y Tobago", "https://h/9.png"))
        self.assertEqual(gk["photo"], "")

    def test_missing_or_absurd_data_is_left_out(self):
        self.assertIsNone(self.by["Medio Cabeza"]["age"])
        self.assertEqual(self.by["Medio Cabeza"]["country"], "")
        self.assertIsNone(self.by["Sin Número"]["age"])   # 3 años no es una edad real
        self.assertEqual(self.by["Sin Número"]["jersey"], "")

    def test_injury(self):
        self.assertEqual(self.by["Defensa Dos"]["injury"], "Esguince de tobillo")
        self.assertEqual(self.by["Defensa Uno"]["injury"], "")
        generic = r.parse_roster({"athletes": [ath("X Y", "D", "4", injuries=[{"foo": 1}])]})
        self.assertEqual(generic[0]["injury"], "Lesionado")

    def test_grouped_shape_and_empty(self):
        grouped = {"athletes": [{"position": "Goalkeepers", "items": [ath("Portero Uno", "G", "1")]}]}
        self.assertEqual([x["name"] for x in r.parse_roster(grouped)], ["Portero Uno"])
        for bad in (None, {}, {"athletes": None}, {"athletes": []}):
            self.assertEqual(r.parse_roster(bad), [])


class StatsTests(unittest.TestCase):
    def players(self):
        return [
            {"name": "Delantero Uno", "pj": 5, "starts": 4, "goals": 3, "assists": 1, "yellow": 1, "red": 0,
             "comps": {"Liga": {"pj": 3, "starts": 2, "goals": 2, "assists": 1, "yellow": 1, "red": 0}}},
            {"name": "Elvi Gerardo Elington Cayetano", "pj": 2, "starts": 2, "goals": 0, "assists": 0, "yellow": 0, "red": 0, "comps": {}},
        ]

    def test_exact_and_fuzzy_match(self):
        roster = r.parse_roster({"athletes": [ath("Delantero Uno", "F", "9"), ath("Elvi Elington", "M", "8"), ath("Otro Jugador", "D", "4")]})
        out = {x["name"]: x for x in r.attach_stats(roster, self.players())}
        self.assertEqual(out["Delantero Uno"]["stats"]["goals"], 3)
        self.assertEqual(out["Delantero Uno"]["comps"]["Liga"]["goals"], 2)
        self.assertEqual(out["Elvi Elington"]["stats"]["pj"], 2)      # "Elvi Elington" = "Elvi Gerardo Elington Cayetano"
        self.assertEqual(out["Otro Jugador"]["stats"], dict.fromkeys(r.STAT_KEYS, 0))
        self.assertEqual(out["Otro Jugador"]["comps"], {})

    def test_one_stats_row_goes_to_one_player_only(self):
        roster = r.parse_roster({"athletes": [ath("Delantero Uno", "F", "9"), ath("Delantero Uno", "F", "19")]})
        goals = sorted(x["stats"]["goals"] for x in r.attach_stats(roster, self.players()))
        self.assertEqual(goals, [0, 3])

    def test_json_serializable(self):
        json.dumps(r.attach_stats(r.parse_roster(RAW), self.players()))


if __name__ == "__main__":
    unittest.main()
