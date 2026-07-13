"""
Exporte tous les joueurs de dim_player (sans filtre) vers un CSV, pour
faciliter le travail manuel (ex: repérage des noms à corriger pour le
matching Understat).

Usage :
    python scripts/export_all_players.py
"""

import csv
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "alter11.db"
OUTPUT_PATH = ROOT_DIR / "tous_les_joueurs.csv"


def main():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.player_name, t.team_name, t.competition, p.age, p.position,
                   f.minutes, f.xg
            FROM dim_player p
            JOIN dim_team t ON p.team_id = t.team_id
            LEFT JOIN fact_stats f ON f.player_id = p.player_id
            ORDER BY p.player_name
        """)
        rows = cur.fetchall()
        colonnes = [desc[0] for desc in cur.description]

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(colonnes)
        writer.writerows(rows)

    print(f"✅ {len(rows)} joueurs exportés vers {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
