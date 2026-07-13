"""
Applique les 6 dernières correspondances Understat, identifiées à la main
par l'utilisateur après vérification (les cas où le matching automatique,
même nom+club, se trompait de joueur ou ne trouvait rien).

Usage :
    python scripts/apply_final_understat_matches.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
import soccerdata as sd

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "alter11.db"

LEAGUES = [
    "ENG-Premier League", "ESP-La Liga", "FRA-Ligue 1",
    "GER-Bundesliga", "ITA-Serie A",
]
SEASON = "2526"

# nom dans dim_player -> nom exact confirmé côté Understat
CORRESPONDANCES_MANUELLES = {
    "Kevin Carlos": "Kevin Omoruyi",
    "Raúl Asencio": "Raùl",
    "Fabián Ruiz Peña": "Fabián",
    "Alexandre Alemão": "Alemão",
    "Jonny Castro": "Jonny",
    "Ísak Jóhannesson": "Ísak Bergmann Jóhannesson",
}


def main():
    print("Scraping Understat (depuis le cache si déjà fait)...")
    understat = sd.Understat(leagues=LEAGUES, seasons=[SEASON])
    df_understat = understat.read_player_season_stats().reset_index()

    col_xg = next((c for c in df_understat.columns if c.lower() == "xg"), None)
    col_xa = next((c for c in df_understat.columns if c.lower() == "xa"), None)
    col_npxg = next((c for c in df_understat.columns if c.lower() in ("npxg", "np_xg")), None)
    col_np_goals = next((c for c in df_understat.columns if c.lower() in ("np_goals", "npg")), None)
    col_xg_buildup = next((c for c in df_understat.columns if c.lower() in ("xg_buildup", "xgbuildup")), None)

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        dim_player = pd.read_sql("SELECT player_id, player_name FROM dim_player", conn)

        matched, non_trouves = 0, []

        for nom_base, nom_understat in CORRESPONDANCES_MANUELLES.items():
            candidat_understat = df_understat[df_understat["player"] == nom_understat]
            if candidat_understat.empty:
                non_trouves.append((nom_base, nom_understat, "introuvable côté Understat"))
                continue

            joueur_base = dim_player[dim_player["player_name"] == nom_base]
            if joueur_base.empty:
                non_trouves.append((nom_base, nom_understat, "introuvable dans dim_player"))
                continue

            player_id = int(joueur_base["player_id"].iloc[0])
            row = candidat_understat.iloc[0]

            cur.execute(
                "UPDATE fact_stats SET xg = ?, xa = ?, npxg = ?, np_goals = ?, xg_buildup = ? "
                "WHERE player_id = ?",
                (
                    row[col_xg],
                    row[col_xa] if col_xa else None,
                    row[col_npxg] if col_npxg else None,
                    row[col_np_goals] if col_np_goals else None,
                    row[col_xg_buildup] if col_xg_buildup else None,
                    player_id,
                )
            )
            matched += 1
            print(f"✅ {nom_base} → {nom_understat}")

        conn.commit()

    print(f"\n📊 {matched} joueurs mis à jour")
    if non_trouves:
        print("⚠️ Problèmes :")
        for nom_base, nom_understat, raison in non_trouves:
            print(f"   {nom_base} → '{nom_understat}' : {raison}")


if __name__ == "__main__":
    main()
