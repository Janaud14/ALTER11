import requests
h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
base = "https://img.a.transfermarkt.technology/portrait/{}/1190411-1744375833.jpg?lm=1"
for taille in ["header", "big", "large", "medium", "originalimage", "original"]:
    url = base.format(taille)
    try:
        r = requests.get(url, headers=h, timeout=10)
        ko = len(r.content) // 1024
        print(f"{taille:15} -> {r.status_code}  {ko} Ko")
    except Exception as e:
        print(f"{taille:15} -> erreur {e}")
