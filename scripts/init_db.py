import sqlite3
from pathlib import Path

DB_PATH = Path("data/municipal.sqlite3")


def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id TEXT PRIMARY KEY,
                competition TEXT NOT NULL,
                season TEXT NOT NULL,
                matchday TEXT,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                kickoff_local TEXT,
                timezone TEXT NOT NULL DEFAULT 'America/Guatemala',
                venue TEXT,
                status TEXT NOT NULL DEFAULT 'scheduled'
                    CHECK (
                        status IN (
                            'scheduled',
                            'postponed',
                            'cancelled',
                            'completed'
                        )
                    ),
                home_score INTEGER,
                away_score INTEGER,
                source_url TEXT,
                sequence INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (
                    competition,
                    season,
                    matchday,
                    home_team,
                    away_team
                )
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS match_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT NOT NULL,
                changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                field_name TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                source_url TEXT,
                FOREIGN KEY (match_id)
                    REFERENCES matches(match_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                source_type TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_matches_kickoff
            ON matches(kickoff_local)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_matches_competition
            ON matches(competition, season)
        """)

    print(f"Base de datos preparada: {DB_PATH}")


if __name__ == "__main__":
    main()
