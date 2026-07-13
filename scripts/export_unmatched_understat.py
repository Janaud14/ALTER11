"""
Exporte la liste des joueurs sans xG (non matchés avec Understat) vers un
CSV, avec une colonne vide "match_understat" à remplir à la main en
comparant avec joueurs_understat.csv (généré par export_understat_players.py).

Usage :
    python scripts/export_unmatched_understat.py
"""

import csv
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "alter11.db"
OUTPUT_PATH = ROOT_DIR / "joueurs_non_matches_understat.csv"


def main():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.player_name, t.team_name, t.competition, p.age, p.position
            FROM dim_player p
            JOIN dim_team t ON p.team_id = t.team_id
            JOIN fact_stats f ON f.player_id = p.player_id
            WHERE f.xg IS NULL AND f.minutes >= 200
            ORDER BY p.player_name
        """)
        rows = cur.fetchall()

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["player_name", "team_name", "competition", "age", "position", "match_understat"])
        for row in rows:
            writer.writerow(list(row) + [""])  # colonne match_understat vide, à remplir

    print(f"✅ {len(rows)} joueurs non matchés exportés vers {OUTPUT_PATH}")
    print("   Remplis la colonne 'match_understat' avec le nom exact trouvé dans joueurs_understat.csv")


if __name__ == "__main__":
    main()
