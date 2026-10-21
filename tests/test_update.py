import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import update_calendar as uc  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "calendar.html"
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.found, self.how = uc.parse_matches(FIXTURE.read_text(encoding="utf-8"))

    def test_parses_all_matches(self):
        self.assertEqual(self.how, "html")
        self.assertEqual(len(self.found), 8)

    def test_times_converted_to_utc(self):
        # 3:00 PM en Guatemala (UTC-6) = 21:00 UTC
        self.assertEqual(self.found["401879570"]["start"], "2026-10-21T21:00:00Z")
        # 8:00 PM -> 02:00 UTC del día siguiente
        self.assertEqual(self.found["401879597"]["start"], "2026-10-29T02:00:00Z")

    def test_home_away(self):
        m = self.found["401879570"]
        self.assertEqual((m["home"], m["away"]), ("Deportivo Mixco", "Municipal"))
        m = self.found["401879605"]
        self.assertEqual((m["home"], m["away"]), ("Municipal", "Aurora FC"))

    def test_reschedule_bumps_sequence(self):
        db = uc.merge({}, self.found, NOW)
        moved = {k: dict(v) for k, v in self.found.items()}
        moved["401879570"]["start"] = "2026-10-22T02:00:00Z"
        db2 = uc.merge(db, moved, NOW)
        self.assertEqual(db["401879570"]["seq"], 0)
        self.assertEqual(db2["401879570"]["seq"], 1)
        self.assertEqual(db2["401879588"]["seq"], 0)  # sin cambios

    def test_removed_future_match_dropped_past_kept(self):
        db = uc.merge({}, self.found, NOW)
        later = datetime(2026, 10, 25, tzinfo=timezone.utc)  # ya pasaron 21 y 24
        remaining = {k: v for k, v in self.found.items() if k not in ("401879570", "401879640")}
        db2 = uc.merge(db, remaining, later)
        self.assertIn("401879570", db2)      # jugado: se conserva
        self.assertNotIn("401879640", db2)   # futuro y ya no listado: se elimina

    def test_ics_is_valid_shape(self):
        ics = uc.build_ics(uc.merge({}, self.found, NOW))
        self.assertTrue(ics.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(ics.endswith("END:VCALENDAR\r\n"))
        self.assertEqual(ics.count("BEGIN:VEVENT"), 8)
        self.assertIn("DTSTART:20261021T210000Z", ics)
        self.assertIn("SUMMARY:Municipal vs Aurora FC", ics)
        for line in ics.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)

    def test_json_extraction(self):
        obj = {"page": {"events": [{
            "id": "401879999", "date": {"date": "2026-12-05T01:00Z"},
            "opponent": {"displayName": "Xelajú MC"}, "homeAwayFlag": "@",
            "league": {"name": "Liga Nacional de Guatemala"}}]}}
        found = uc.matches_from_json(obj)
        m = found["401879999"]
        self.assertEqual((m["home"], m["away"]), ("Xelajú MC", "Municipal"))
        self.assertEqual(m["start"], "2026-12-05T01:00:00Z")

    def test_api_extraction(self):
        api = {"events": [{
            "id": "401879570", "date": "2026-10-21T21:00Z",
            "competitions": [{
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": "Deportivo Mixco"}},
                    {"homeAway": "away", "team": {"displayName": "Municipal"}}],
                "venue": {"fullName": "Estadio Cementos Progreso"}}]}]}
        m = uc.matches_from_api(api, "Liga Nacional de Guatemala")["401879570"]
        self.assertEqual((m["home"], m["away"]), ("Deportivo Mixco", "Municipal"))
        self.assertEqual(m["start"], "2026-10-21T21:00:00Z")
        ics = uc.build_ics(uc.merge({}, {"401879570": m}, NOW))
        self.assertIn("LOCATION:Estadio Cementos Progreso", ics)


if __name__ == "__main__":
    unittest.main()
