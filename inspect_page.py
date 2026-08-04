import sqlite3, pandas as pd, json
c = sqlite3.connect("alter11.db")

# Composantes du score
print("=== DECOMPOSITION SCORE (Said El Mala) ===")
q = "SELECT player_name, score_brut, bonus_age, coef_fiab, coef_club, alterscore FROM v_alterscore WHERE player_name = 'Said El Mala'"
print(pd.read_sql(q, c).T.to_string())

# Structure du players.json
print()
print("=== STRUCTURE players.json (1er joueur) ===")
p = json.load(open("players.json", encoding="utf-8"))
import pprint
pprint.pprint(p[0])
