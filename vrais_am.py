import sqlite3, pandas as pd
c = sqlite3.connect("alter11.db")
q = """SELECT v.player_name, v.age, v.team_name, v.minutes,
              v.passes_p90, v.buts_p90, v.tirs_p90, v.alterscore
       FROM v_alterscore v
       JOIN dim_player p ON v.player_id = p.player_id
       WHERE p.position_detail = 'AM' AND v.alterscore IS NOT NULL
       ORDER BY v.alterscore DESC"""
print(pd.read_sql(q, c).to_string())
