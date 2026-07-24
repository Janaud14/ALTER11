import sqlite3, pandas as pd
c = sqlite3.connect("alter11.db")
q = """SELECT player_name, minutes, coef_club, alterscore,
       RANK() OVER (ORDER BY alterscore DESC) AS rang
       FROM v_alterscore WHERE alterscore IS NOT NULL"""
d = pd.read_sql(q, c)
print(d[d.player_name.str.contains("Bamba")].to_string())
print("Total classes :", len(d), "| Moyenne :", round(d.alterscore.mean(), 2))
