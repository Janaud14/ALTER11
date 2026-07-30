import json, requests
from bs4 import BeautifulSoup
from pathlib import Path
h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
players = json.load(open("players.json", encoding="utf-8"))
photos = Path("data/photos")
manquants = [p for p in players if not (photos / f"{p['name'].replace(' ','_')}.png").exists()]
print(f"{len(manquants)} manquants :\n")
for p in manquants:
    q = p["name"].replace(" ", "+")
    try:
        r = requests.get(f"https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={q}", headers=h, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")
        tables = soup.find_all("table", {"class": "items"})
        n = len(tables[0].find_all("tr", {"class": ["odd","even"]})) if tables else 0
        premier = ""
        if n:
            tds = tables[0].find_all("tr", {"class": ["odd","even"]})[0].find_all("td")
            if len(tds) >= 4:
                premier = f" | 1er: {tds[2].get_text(strip=True)} ({tds[3].get_text(strip=True)})"
        print(f"{p['name']:28} [{p['team']}] -> {n} resultats{premier}")
    except Exception as e:
        print(f"{p['name']:28} -> erreur {e}")
