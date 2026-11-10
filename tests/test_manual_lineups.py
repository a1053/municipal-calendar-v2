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

    def test_load_ignores_bad_files(self):
        self.assertEqual(ml.load(Path("/no/existe.json")), [])


if __name__ == "__main__":
    unittest.main()
