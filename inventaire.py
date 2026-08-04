import sqlite3, pandas as pd
c = sqlite3.connect("alter11.db")

# Toutes les colonnes de fact_stats
cols = [r[1] for r in c.execute("PRAGMA table_info(fact_stats)")]
print("=== COLONNES fact_stats ===")
print(cols)
print()

# Lesquelles sont deja dans la vue (donc deja exploitees)
vue_cols = [r[1] for r in c.execute("PRAGMA table_info(v_alterscore)")]
print("=== COLONNES v_alterscore (deja exploitees) ===")
print(vue_cols)
print()

# Un joueur exemple pour voir le remplissage reel
print("=== Said El Mala : valeurs brutes fact_stats ===")
df = pd.read_sql("""
    SELECT f.* FROM fact_stats f
    JOIN dim_player p ON f.player_id = p.player_id
    WHERE p.player_name = 'Said El Mala'
""", c)
print(df.T.to_string())
