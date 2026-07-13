"""
Exporte la liste brute des joueurs Understat (5 grands championnats,
2025-2026) vers un CSV, pour comparaison manuelle avec tous_les_joueurs.csv
(généré par export_all_players.py) — utile pour compléter le matching à la
main sur les cas que le script automatique n'a pas su rapprocher.

Usage :
    python scripts/export_understat_players.py
"""

import csv
from pathlib import Path

import soccerdata as sd

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT_DIR / "joueurs_understat.csv"

LEAGUES = [
    "ENG-Premier League", "ESP-La Liga", "FRA-Ligue 1",
    "GER-Bundesliga", "ITA-Serie A",
]
SEASON = "2526"


def main():
    print("Scraping Understat (depuis le cache si déjà fait)...")
    understat = sd.Understat(leagues=LEAGUES, seasons=[SEASON])
    df = understat.read_player_season_stats().reset_index()

    cols = ["player", "team", "league", "position", "minutes", "goals", "xg"]
    cols = [c for c in cols if c in df.columns]
    df_export = df[cols].sort_values("player")

    df_export.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"✅ {len(df_export)} joueurs Understat exportés vers {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
