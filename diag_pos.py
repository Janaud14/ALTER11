import sqlite3, pandas as pd
c = sqlite3.connect("alter11.db")
q = """SELECT player_name, position, position_detail
       FROM dim_player
       WHERE player_name IN ('Nathan Mbala','Can Uzun','Lamine Yamal',
                             'Jesus Rodríguez','Lennart Karl','Assane Diao')"""
print(pd.read_sql(q, c).to_string())
print()
# distribution des positions detaillees pour les MF
q2 = """SELECT position_detail, COUNT(*) AS n
        FROM dim_player WHERE position = 'MF'
        GROUP BY position_detail ORDER BY n DESC"""
print(pd.read_sql(q2, c).to_string())
