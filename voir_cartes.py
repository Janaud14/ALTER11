with open("index.html", encoding="utf-8") as f:
    txt = f.read()
i = txt.find("card")
# cherche la fonction qui rend les cartes
for mot in ["function render", "innerHTML", "grid.innerHTML", ".map(", "createElement"]:
    j = txt.find(mot)
    if j != -1:
        print(f"--- autour de '{mot}' (position {j}) ---")
        print(txt[j:j+400])
        print()
