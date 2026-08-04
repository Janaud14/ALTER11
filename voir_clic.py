with open("index.html", encoding="utf-8") as f:
    lignes = f.readlines()
for i, l in enumerate(lignes):
    if "querySelectorAll" in l:
        for j in range(max(0,i-3), min(len(lignes), i+14)):
            print(f"{j+1:3} {lignes[j]}", end="")
