"""
Diagnostic : pour chaque joueur sans photo, montre ce que la recherche
Transfermarkt renvoie réellement — aucun résultat ? un candidat proche mais
mal scoré (accent, tiret) ? un vrai blocage réseau ?

Usage :
    python scripts/diagnose_missing_photos.py
"""

import sqlite3
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "alter11.db"
PHOTOS_DIR = ROOT_DIR / "data" / "photos"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def joueurs_sans_photo():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT p.player_name, t.team_name
            FROM dim_player p
            JOIN dim_team t ON p.team_id = t.team_id
            JOIN fact_stats f ON f.player_id = p.player_id
            WHERE f.minutes >= 200 AND p.age <= 20
            ORDER BY p.player_name
        """)
        candidats = cur.fetchall()

    manquants = []
    for nom, club in candidats:
        chemin = PHOTOS_DIR / f"{nom.replace(' ', '_')}.png"
        if not chemin.exists():
            manquants.append((nom, club))
    return manquants


def diagnostiquer(nom, club):
    query = nom.replace(" ", "+")
    url = f"https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={query}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        return f"❌ Requête échouée : {e}"

    soup = BeautifulSoup(r.text, "lxml")
    tables = soup.find_all("table", {"class": "items"})
    if not tables:
        return "🔴 Aucun résultat de recherche du tout (page vide)"

    rows = tables[0].find_all("tr", {"class": ["odd", "even"]})
    if not rows:
        return "🔴 Table de résultats vide"

    candidats_trouves = []
    for row in rows:
        tds = row.find_all("td")
        if len(tds) < 9:
            continue
        tm_name = tds[2].get_text(strip=True)
        tm_club = tds[3].get_text(strip=True)
        score_name = fuzz.token_sort_ratio(nom.lower(), tm_name.lower())
        score_club = fuzz.partial_ratio(club.lower(), tm_club.lower())
        score_total = score_name * 0.7 + score_club * 0.3
        a_profil = any("/profil/spieler/" in a.get("href", "") for a in row.find_all("a", href=True))
        candidats_trouves.append((tm_name, tm_club, score_total, a_profil))

    if not candidats_trouves:
        return "🔴 Résultats trouvés mais aucune ligne exploitable (moins de 9 colonnes)"

    candidats_trouves.sort(key=lambda x: -x[2])
    meilleur = candidats_trouves[0]
    lien_ok = "✓ lien profil trouvé" if meilleur[3] else "✗ PAS de lien profil dans la ligne"
    return f"🟡 Meilleur candidat : '{meilleur[0]}' ({meilleur[1]}) score={meilleur[2]:.0f} [{lien_ok}]"


def main():
    manquants = joueurs_sans_photo()
    print(f"{len(manquants)} joueurs sans photo — diagnostic :\n")

    for nom, club in manquants:
        resultat = diagnostiquer(nom, club)
        print(f"{nom} ({club}) → {resultat}")
        time.sleep(1.2)


if __name__ == "__main__":
    main()
