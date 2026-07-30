import requests
from bs4 import BeautifulSoup
h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
r = requests.get("https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query=Endrick", headers=h, timeout=10)
soup = BeautifulSoup(r.text, "lxml")
row = soup.find_all("tr", {"class": ["odd","even"]})[0]
lien = None
for a in row.find_all("a", href=True):
    if "/profil/spieler/" in a["href"]:
        lien = "https://www.transfermarkt.com" + a["href"]
        break
print("Fiche:", lien)
rp = requests.get(lien, headers=h, timeout=10)
sp = BeautifulSoup(rp.text, "lxml")
img = sp.find("img", {"class": "data-header__profile-image"})
print("img trouvee:", img is not None)
if img:
    print("src:", img.get("src"))
    print("data-src:", img.get("data-src"))
