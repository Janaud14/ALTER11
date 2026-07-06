"""
Génère les cartes joueurs ALTER11 (design noir/bleu électrique).

Pipeline par joueur :
  1. Recherche sur Transfermarkt (nom + club) pour récupérer l'URL de la photo
  2. Détourage local avec rembg (pas de clé API, tout tourne en local)
  3. Composition de la carte : fond ALTER11, photo détourée, dégradé, textes

Usage :
    python scripts/generate_cards.py

Prérequis :
    pip install requests beautifulsoup4 rapidfuzz rembg pillow
"""

import os
import time
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from rapidfuzz import fuzz
from rembg import remove as rembg_remove

# ── Chemins relatifs à la racine du projet ────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
PHOTOS_DIR = ROOT_DIR / "data" / "photos"
CLUSTERS_CSV = ROOT_DIR / "clusters_u20.csv"  # source des joueurs à traiter

PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Dimensions de la carte
CARD_W, CARD_H = 400, 520
PHOTO_SIZE = (180, 220)
PHOTO_Y = 120


def get_tm_photo_url(player_name: str, team_name: str, headers: dict = HEADERS):
    """Cherche un joueur sur Transfermarkt et retourne l'URL de sa photo.

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
        best_img, best_score = None, 0

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
                img = row.find("img")
                if img:
                    best_img = img.get("data-src") or img.get("src")

        return best_img, best_score

    except requests.RequestException:
        return None, 0


def generer_carte(player_name: str, team_name: str, age: int,
                   position: str, alterscore: float, img_url: str | None):
    """Génère et sauvegarde une carte joueur ALTER11. Retourne le chemin du fichier."""
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

    # Détourage local (rembg, pas de clé API)
    img_detoure = Image.open(BytesIO(rembg_remove(r_photo.content))).convert("RGBA")
    img_detoure.thumbnail(PHOTO_SIZE)

    # Fond ALTER11 : noir + grille bleu électrique
    fond = Image.new("RGBA", (CARD_W, CARD_H), (5, 5, 10, 255))
    draw = ImageDraw.Draw(fond)
    for x in range(0, CARD_W, 20):
        draw.line([(x, 0), (x, CARD_H)], fill=(0, 102, 255, 12), width=1)
    for y in range(0, CARD_H, 20):
        draw.line([(0, y), (CARD_W, y)], fill=(0, 102, 255, 12), width=1)

    # Photo joueur centrée
    x = (CARD_W - img_detoure.width) // 2
    fond.paste(img_detoure, (x, PHOTO_Y), img_detoure)

    # Dégradé vers le bandeau d'infos
    fondu = Image.new("RGBA", (CARD_W, 200), (0, 0, 0, 0))
    draw_f = ImageDraw.Draw(fondu)
    for i in range(200):
        alpha = int((i / 200) ** 0.6 * 255)
        draw_f.rectangle([(0, i), (CARD_W, i + 1)], fill=(5, 5, 10, alpha))
    fond.paste(fondu, (0, 340), fondu)

    # Ligne séparatrice bleu électrique
    draw = ImageDraw.Draw(fond)
    draw.rectangle([(0, 420), (CARD_W, 422)], fill=(0, 102, 255, 220))

    # Textes (fallback police par défaut si Arial absent, ex. hors Windows)
    try:
        font_nom = ImageFont.truetype("arial.ttf", 22)
        font_info = ImageFont.truetype("arial.ttf", 16)
        font_score = ImageFont.truetype("arialbd.ttf", 28)
    except OSError:
        font_nom = font_info = font_score = ImageFont.load_default()

    draw.text((20, 428), player_name.upper(), fill=(240, 240, 240, 255), font=font_nom)
    draw.text((20, 458), f"{team_name}  •  {position}  •  {age} ans",
              fill=(160, 160, 160, 255), font=font_info)
    draw.text((320, 428), str(alterscore), fill=(0, 102, 255, 255), font=font_score)
    draw.text((320, 462), "ALTER", fill=(120, 120, 120, 255), font=font_info)

    fond.save(chemin)
    print(f"✅ {player_name}")
    return chemin


def main():
    df = pd.read_csv(CLUSTERS_CSV)
    resultats = []

    for _, row in df.iterrows():
        img_url, score = get_tm_photo_url(row["player_name"], row["team_name"])
        chemin = generer_carte(
            row["player_name"], row["team_name"],
            row["age"], row.get("position_detail", row.get("position", "")),
            row.get("alterscore", "—"),
            img_url,
        )
        resultats.append({"player_name": row["player_name"], "chemin": chemin})
        time.sleep(1.5)  # politesse envers Transfermarkt

    ok = sum(1 for r in resultats if r["chemin"])
    print(f"\n✅ {ok} cartes générées")
    print(f"❌ {len(resultats) - ok} échecs")


if __name__ == "__main__":
    main()
