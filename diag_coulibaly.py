import requests
from bs4 import BeautifulSoup
h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
r = requests.get("https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query=Abdoul+Coulibaly", headers=h, timeout=30)
soup = BeautifulSoup(r.text, "lxml")
row = soup.find_all("tr", {"class": ["odd","even"]})[0]
lien = next(("https://www.transfermarkt.com"+a["href"] for a in row.find_all("a", href=True) if "/profil/spieler/" in a["href"]), None)
rp = requests.get(lien, headers=h, timeout=30)
sp = BeautifulSoup(rp.text, "lxml")
img = sp.find("img", {"class": "data-header__profile-image"})
print("src:", img.get("src") if img else "aucune")
