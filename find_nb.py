import json
nb = json.load(open("notebooks/01_analysis.ipynb", encoding="utf-8"))
for i, cell in enumerate(nb["cells"]):
    src = "".join(cell.get("source", []))
    if "to_sql" in src or "dim_player" in src or "drop_duplicates" in src:
        print(f"=== Cellule {i} ===")
        print(src[:800])
        print()
