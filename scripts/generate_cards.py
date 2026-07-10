"""
Récupère et détoure les photos joueurs ALTER11 depuis Transfermarkt.

Pipeline par joueur :
  1. Recherche sur Transfermarkt (nom + club) pour récupérer l'URL de la
     photo en haute résolution (fiche profil, pas la vignette de recherche)
  2. Détourage local avec rembg (pas de clé API, tout tourne en local)
  3. Sauvegarde de la photo seule (fond transparent) — la mise en forme
     (grille, score, nom) est gérée par le CSS/HTML de la vitrine (index.html),
     pas ici, pour éviter une carte-dans-la-carte.

Usage :
    python scripts/generate_cards.py

Prérequis :
    pip install requests beautifulsoup4 rapidfuzz rembg pillow pandas
"""

import time
from io import BytesIO
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from PIL import Image
from rapidfuzz import fuzz
from rembg import remove as rembg_remove, new_session

# ── Chemins relatifs à la racine du projet ────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
PHOTOS_DIR = ROOT_DIR / "data" / "photos"

PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

# Modèle spécialisé silhouettes humaines (plus précis que le modèle par
# défaut "u2net" sur les cheveux/contours pour des portraits).
# Session créée une seule fois et réutilisée (sinon rembg la recharge à
# chaque appel, très lent). Le modèle se télécharge automatiquement au
# premier lancement (~176 Mo).
REMBG_SESSION = new_session("u2net_human_seg")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def get_tm_photo_url(player_name: str, team_name: str, headers: dict = HEADERS):
    """Cherche un joueur sur Transfermarkt et retourne l'URL de sa photo en
    haute résolution (récupérée sur sa fiche profil, pas la vignette de
    recherche qui est trop petite et donne des cartes floues/déformées).

    Le matching combine similarité de nom (70%) et similarité de club (30%)
    pour limiter les faux positifs (homonymes dans d'autres championnats).
    """
    query = player_name.replace(" ", "+")
    url = f"https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={query}"

    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")
        tables = soup.find_all("table", {"class": "items"})
        if not tables:
            return None, None

        rows = tables[0].find_all("tr", {"class": ["odd", "even"]})
        best_link, best_score = None, 0

        for row in rows:
            tds = row.find_all("td")
            if len(tds) < 9:
                continue
            tm_name = tds[2].get_text(strip=True)
            tm_club = tds[3].get_text(strip=True)

            score_name = fuzz.token_sort_ratio(player_name.lower(), tm_name.lower())
            score_club = fuzz.partial_ratio(team_name.lower(), tm_club.lower())
            score_total = score_name * 0.7 + score_club * 0.3

            if score_total > best_score:
                best_score = score_total
                lien_profil = None
                for a in row.find_all("a", href=True):
                    if "/profil/spieler/" in a["href"]:
                        lien_profil = a["href"]
                        break
                if lien_profil:
                    best_link = "https://www.transfermarkt.com" + lien_profil

        if not best_link:
            return None, best_score

        # Deuxième requête : la fiche joueur, pour la vraie photo (pas la vignette)
        time.sleep(1.0)
        r_profil = requests.get(best_link, headers=headers, timeout=10)
        soup_profil = BeautifulSoup(r_profil.text, "lxml")
        img_profil = soup_profil.find("img", {"class": "data-header__profile-image"})

        if img_profil:
            photo_url = img_profil.get("src") or img_profil.get("data-src")
            # L'URL Transfermarkt encode la taille dans le chemin
            # (small/medium/header) — on force la plus grande disponible.
            if photo_url and "/small/" in photo_url:
                photo_url = photo_url.replace("/small/", "/header/")
            return photo_url, best_score

        return None, best_score

    except requests.RequestException:
        return None, 0


def generer_carte(player_name: str, team_name: str, age: int,
                   position: str, alterscore: float, img_url: str | None):
    """Télécharge, détoure et sauvegarde la photo du joueur.

    Ne génère QUE la photo (détourée, fond transparent) — pas de carte
    complète avec nom/score/grille : ça, c'est déjà géré par le CSS/HTML
    de la vitrine (index.html). Générer une carte complète ici créait un
    effet de carte-dans-la-carte avec une photo minuscule au milieu.
    """
    chemin = PHOTOS_DIR / f"{player_name.replace(' ', '_')}.png"
    if chemin.exists():
        print(f"⏭️  {player_name} — déjà générée")
        return chemin

    if not img_url:
        print(f"❌ {player_name} — pas d'URL photo trouvée")
        return None

    try:
        r_photo = requests.get(img_url, headers=HEADERS, timeout=10)
        r_photo.raise_for_status()
    except requests.RequestException:
        print(f"❌ {player_name} — téléchargement photo échoué")
        return None

    # Détourage local (rembg, pas de clé API), fond transparent conservé.
    # alpha_matting affine les bords (mèches de cheveux notamment) — sans ça,
    # rembg a tendance à "manger" les cheveux fins en les traitant comme du fond.
    img_bytes = rembg_remove(
        r_photo.content,
        session=REMBG_SESSION,
        alpha_matting=True,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=10,
    )
    img_detoure = Image.open(BytesIO(img_bytes)).convert("RGBA")

    # Recadre sur la zone réellement visible (bounding box du canal alpha),
    # avec une marge de respiration autour (sinon le recadrage colle pile au
    # visage façon photo d'identité).
    bbox = img_detoure.getbbox()
    if bbox:
        left, top, right, bottom = bbox
        marge_x = int((right - left) * 0.28)
        marge_y = int((bottom - top) * 0.22)
        left = max(0, left - marge_x)
        top = max(0, top - marge_y)
        right = min(img_detoure.width, right + marge_x)
        bottom = min(img_detoure.height, bottom + marge_y)
        img_detoure = img_detoure.crop((left, top, right, bottom))

    # Redimensionne en gardant une bonne résolution (pas de miniature 180px)
    # — c'est la vitrine (CSS object-fit: cover) qui adapte l'affichage.
    img_detoure.thumbnail((600, 700))

    img_detoure.save(chemin)
    print(f"✅ {player_name}")
    return chemin


def main():
    players_json_path = ROOT_DIR / "players.json"
    if not players_json_path.exists():
        print("❌ players.json introuvable. Lance d'abord :")
        print("   python scripts/export_vitrine_data.py")
        return

    import json
    with open(players_json_path, encoding="utf-8") as f:
        players = json.load(f)

    resultats = []
    for p in players:
        img_url, score = get_tm_photo_url(p["name"], p["team"])
        chemin = generer_carte(
            p["name"], p["team"], p["age"], p["pos"], p["score"], img_url,
        )
        resultats.append({"player_name": p["name"], "chemin": chemin})
        time.sleep(1.5)  # politesse envers Transfermarkt

    ok = sum(1 for r in resultats if r["chemin"])
    print(f"\n✅ {ok} cartes générées")
    print(f"❌ {len(resultats) - ok} échecs")
    print("\n⚠️  N'oublie pas de relancer 'python scripts/export_vitrine_data.py'")
    print("   pour que players.json prenne en compte les nouvelles photos.")


if __name__ == "__main__":
    main()
