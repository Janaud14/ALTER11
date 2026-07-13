"""
Applique le matching Understat (nom+club) sur les joueurs qui n'avaient pas
été matchés par le script principal (scrape_understat.py, seuil strict).

Ces correspondances ont été vérifiées ligne par ligne à l'œil par
l'utilisateur après un premier passage de diagnose_understat_matching.py —
ce script applique tout, sauf la liste noire ci-dessous (faux positifs
identifiés manuellement).

Usage :
    python scripts/apply_understat_manual_matches.py
"""

import sqlite3
import unicodedata
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
SEASON = "2526"

# Faux positifs identifiés manuellement — vérifiés ligne par ligne, à ne
# JAMAIS matcher automatiquement même si le score semble bon.
LISTE_NOIRE = {
    "Kevin Carlos",
    "Alexandre Alemão",
    "Fabián Ruiz Peña",
    "Jonny Castro",
    "Raúl Asencio",
    "Ísak Jóhannesson",
}


def normalise(nom: str) -> str:
    nfkd = unicodedata.normalize("NFKD", nom)
    sans_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    remplacements = {"ı": "i", "İ": "I", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D"}
    for old, new in remplacements.items():
        sans_accents = sans_accents.replace(old, new)
    return sans_accents.lower()


def score_combine(nom_a: str, club_a: str, nom_b: str, club_b: str) -> float:
    score_nom = fuzz.ratio(normalise(nom_a), normalise(nom_b))
    score_club = fuzz.partial_ratio(normalise(club_a), normalise(club_b))
    return score_nom * 0.7 + score_club * 0.3


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

        non_matches = pd.read_sql("""
            SELECT p.player_id, p.player_name, t.team_name
            FROM dim_player p
            JOIN dim_team t ON p.team_id = t.team_id
            JOIN fact_stats f ON f.player_id = p.player_id
            WHERE f.xg IS NULL AND f.minutes >= 200
            ORDER BY p.player_name
        """, conn)

        print(f"{len(non_matches)} joueurs à traiter, {len(LISTE_NOIRE)} en liste noire\n")

        matched, blacklisted, absents = 0, 0, 0

        for _, row in non_matches.iterrows():
            nom, club, player_id = row["player_name"], row["team_name"], row["player_id"]

            if nom in LISTE_NOIRE:
                blacklisted += 1
                print(f"⛔ {nom} — en liste noire, ignoré")
                continue

            best_row, best_score = None, 0
            for _, cand in df_understat.iterrows():
                score = score_combine(nom, club, cand["player"], cand["team"])
                if score > best_score:
                    best_row, best_score = cand, score

            if best_row is None:
                absents += 1
                continue

            cur.execute(
                "UPDATE fact_stats SET xg = ?, xa = ?, npxg = ?, np_goals = ?, xg_buildup = ? "
                "WHERE player_id = ?",
                (
                    best_row[col_xg],
                    best_row[col_xa] if col_xa else None,
                    best_row[col_npxg] if col_npxg else None,
                    best_row[col_np_goals] if col_np_goals else None,
                    best_row[col_xg_buildup] if col_xg_buildup else None,
                    int(player_id),
                )
            )
            matched += 1
            print(f"✅ {nom} → {best_row['player']} ({best_row['team']}) score={best_score:.0f}")

        conn.commit()

    print(f"\n📊 {matched} joueurs mis à jour, {blacklisted} ignorés (liste noire), "
          f"{absents} sans candidat trouvé")


if __name__ == "__main__":
    main()
