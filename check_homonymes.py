import sqlite3, pandas as pd
c = sqlite3.connect("alter11.db")
q = """SELECT player_name, birth_year, COUNT(*) AS n
       FROM dim_player
       WHERE player_name IN ('Vitinha', 'Nicolás González')
       GROUP BY player_name, birth_year"""
print(pd.read_sql(q, c).to_string())
