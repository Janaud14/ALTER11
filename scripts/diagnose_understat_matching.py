"""
Diagnostic du matching Understat <-> dim_player : pour chaque joueur de la
base qui n'a pas de xG (non matché), affiche le meilleur candidat Understat
trouvé et son score de similarité — pour voir si c'est un vrai problème de
nom (corrigeable) ou une vraie absence de données.

Deux améliorations par rapport à un simple fuzz.ratio :
  1. Normalisation des accents/diacritiques avant comparaison (Yıldız vs
     Yildiz, Stanišić vs Stanisic...) — gère un gros paquet de faux négatifs.
  2. Score combiné ratio + partial_ratio, comme pour le matching Transfermarkt
     — gère les doubles noms de famille (Mbappé vs Mbappe-Lottin).

Usage :
    python scripts/diagnose_understat_matching.py
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


def normalise(nom: str) -> str:
    """Retire les accents/diacritiques (Yıldız -> Yildiz, Stanišić -> Stanisic)."""
    nfkd = unicodedata.normalize("NFKD", nom)
    sans_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Cas particuliers non couverts par NFKD (ı turc, ł polonais, etc.)
    remplacements = {"ı": "i", "İ": "I", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D"}
    for old, new in remplacements.items():
        sans_accents = sans_accents.replace(old, new)
    return sans_accents.lower()


def score_matching(nom_a: str, nom_b: str) -> float:
    """Score sur le nom seul (accents normalisés)."""
    a, b = normalise(nom_a), normalise(nom_b)
    return fuzz.ratio(a, b)


def score_combine(nom_a: str, club_a: str, nom_b: str, club_b: str) -> float:
    """Score combiné nom (70%) + club (30%) — même logique que le matching
    Transfermarkt. Permet d'accepter un score de nom plus bas si le club
    confirme, et élimine les faux positifs du style 'Rayan' tout court qui
    matchait à tort 2 joueurs différents sur le seul critère du nom."""
    score_nom = score_matching(nom_a, nom_b)
    score_club = fuzz.partial_ratio(normalise(club_a), normalise(club_b))
    return score_nom * 0.7 + score_club * 0.3


def main():
    print("Scraping Understat (depuis le cache si déjà fait)...")
    understat = sd.Understat(leagues=LEAGUES, seasons=[SEASON])
    df_understat = understat.read_player_season_stats().reset_index()
    candidats = list(zip(df_understat["player"], df_understat["team"]))

    with sqlite3.connect(DB_PATH) as conn:
        non_matches = pd.read_sql("""
            SELECT p.player_name, t.team_name, p.age, p.position
            FROM dim_player p
            JOIN dim_team t ON p.team_id = t.team_id
            JOIN fact_stats f ON f.player_id = p.player_id
            WHERE f.xg IS NULL AND f.minutes >= 200
            ORDER BY p.player_name
        """, conn)

    print(f"\n{len(non_matches)} joueurs (minutes >= 200) sans xG — diagnostic nom+club :\n")

    recuperables, incertains, absents = [], [], []

    for _, row in non_matches.iterrows():
        nom, club = row["player_name"], row["team_name"]
        best_name, best_club, best_score = None, None, 0
        for cand_nom, cand_club in candidats:
            score = score_combine(nom, club, cand_nom, cand_club)
            if score > best_score:
                best_name, best_club, best_score = cand_nom, cand_club, score

        if best_score >= 90:
            statut = "🟢 récupérable (nom+club)"
            recuperables.append((nom, best_name, best_score))
        elif best_score >= 75:
            statut = "🟡 incertain, à vérifier"
            incertains.append((nom, best_name, best_score))
        else:
            statut = "🔴 probablement absent"
            absents.append(nom)

        print(f"{statut} | {nom} ({club}) → '{best_name}' ({best_club}) score={best_score:.0f}")

    print(f"\n📊 Résumé : {len(recuperables)} récupérables (nom+club >= 90), "
          f"{len(incertains)} incertains (75-89, à vérifier à l'œil), "
          f"{len(absents)} probablement absents (< 75)")


if __name__ == "__main__":
    main()
