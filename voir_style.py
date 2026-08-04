with open("index.html", encoding="utf-8") as f:
    lignes = f.readlines()
# Affiche jusqu'a la fin de la premiere balise <style> ou 120 lignes
for i, l in enumerate(lignes[:120]):
    print(f"{i+1:3} {l}", end="")
