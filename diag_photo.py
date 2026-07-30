import requests
from bs4 import BeautifulSoup
h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
# Jesus Rodriguez, une des photos ratees
r = requests.get("https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query=Jesus+Rodriguez", headers=h, timeout=10)
soup = BeautifulSoup(r.text, "lxml")
for row in soup.find_all("tr", {"class": ["odd","even"]})[:3]:
    for a in row.find_all("a", href=True):
        if "/profil/spieler/" in a["href"]:
            rp = requests.get("https://www.transfermarkt.com"+a["href"], headers=h, timeout=10)
            sp = BeautifulSoup(rp.text, "lxml")
            img = sp.find("img", {"class": "data-header__profile-image"})
            if img:
                print("URL photo:", img.get("src"))
            break
    break
