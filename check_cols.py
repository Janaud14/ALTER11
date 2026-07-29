import sqlite3
c = sqlite3.connect("alter11.db")
cols = [r[1] for r in c.execute("PRAGMA table_info(dim_player)")]
print("Colonnes dim_player :", cols)
