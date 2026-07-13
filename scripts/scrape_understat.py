"""
Enrichit alter11.db avec les statistiques xG (expected goals) et xA (expected
assists) depuis Understat — une source indépendante d'Opta, donc non affectée
par la coupure FBref de janvier 2026.

xG/xA sont des métriques de QUALITÉ des occasions (pas juste le volume) —
elles distinguent un joueur qui marque beaucoup grâce à de la finition pure
d'un joueur qui se procure vraiment de bonnes occasions. Complémentaire aux
8 variables actuelles de l'ALTERSCORE, qui ne mesurent que le volume brut
(tirs/90, buts/90).

Ce script enrichit la base mais NE MODIFIE PAS la formule ALTERSCORE — c'est
une décision à prendre à part, une fois les données vérifiées.

Usage :
    python scripts/scrape_understat.py

Prérequis :
    pip install soccerdata pandas rapidfuzz
"""

import sqlite3
from pathlib import Path

import pandas as pd
import soccerdata as sd
from rapidfuzz import fuzz

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "alter11.db"

LEAGUES = [
    "ENG-Premier League", "ESP-La Liga", "FRA-Ligue 1",
    "GER-Bundesliga", "ITA-Serie A",
]
SEASON = "2526"  # même convention que les autres scripts de cette saison


def scrape_understat() -> pd.DataFrame:
    print("Scraping Understat (xG/xA)...")
    understat = sd.Understat(leagues=LEAGUES, seasons=[SEASON])
    df = understat.read_player_season_stats().reset_index()
    print(f"  {df.shape}")
    print(f"  Colonnes disponibles : {df.columns.tolist()}")
    return df


def update_db(df_understat: pd.DataFrame, db_path: Path):
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        for col in ["xg", "xa", "npxg"]:
            try:
                cur.execute(f"ALTER TABLE fact_stats ADD COLUMN {col} REAL")
            except sqlite3.OperationalError:
                pass  # colonne déjà présente

        dim_player = pd.read_sql("SELECT player_id, player_name FROM dim_player", conn)
        noms_db = dim_player["player_name"].tolist()

        # Détection souple des noms de colonnes (Understat peut nommer
        # différemment selon la version de soccerdata : 'xG'/'xg', etc.)
        col_player = next((c for c in df_understat.columns if c.lower() == "player"), None)
        col_xg = next((c for c in df_understat.columns if c.lower() == "xg"), None)
        col_xa = next((c for c in df_understat.columns if c.lower() == "xa"), None)
        col_npxg = next((c for c in df_understat.columns if c.lower() in ("npxg", "np_xg")), None)

        if not col_player or not col_xg:
            raise KeyError(
                f"Colonnes attendues introuvables. player={col_player}, xg={col_xg}\n"
                f"Colonnes disponibles : {df_understat.columns.tolist()}"
            )

        matched, non_matched = 0, 0
        for _, row in df_understat.iterrows():
            nom = row[col_player]
            best_name, best_score = None, 0
            for candidat in noms_db:
                score = fuzz.ratio(str(nom).lower(), candidat.lower())
                if score > best_score:
                    best_name, best_score = candidat, score
            if best_score < 88:
                non_matched += 1
                continue

            player_id = dim_player.loc[dim_player["player_name"] == best_name, "player_id"].iloc[0]
            cur.execute(
                "UPDATE fact_stats SET xg = ?, xa = ?, npxg = ? WHERE player_id = ?",
                (
                    row[col_xg],
                    row[col_xa] if col_xa else None,
                    row[col_npxg] if col_npxg else None,
                    int(player_id),
                )
            )
            matched += 1

        conn.commit()

    print(f"\n✅ {matched} joueurs mis à jour, {non_matched} non trouvés (score de matching < 88)")


def main():
    df_understat = scrape_understat()
    update_db(df_understat, DB_PATH)


if __name__ == "__main__":
    main()
