import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

for nom in ["Desire Doue", "Lewis Miley", "Pau Navarro"]:
    q = nom.replace(" ", "+")
    r = requests.get(f"https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query={q}", headers=h, timeout=10)
    soup = BeautifulSoup(r.text, "lxml")
    tables = soup.find_all("table", {"class": "items"})
    print(f"=== {nom} ===")
    if not tables:
        print("  aucune table de resultats")
        continue
    rows = tables[0].find_all("tr", {"class": ["odd","even"]})
    print(f"  {len(rows)} resultats")
    for row in rows[:3]:
        tds = row.find_all("td")
        if len(tds) >= 4:
            print(f"    nom='{tds[2].get_text(strip=True)}' club='{tds[3].get_text(strip=True)}'")
