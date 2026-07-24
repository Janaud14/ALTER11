import sqlite3, pandas as pd
c = sqlite3.connect("alter11.db")
q = """SELECT player_name, age, position, team_name, minutes, coef_club, alterscore
       FROM v_alterscore WHERE alterscore IS NOT NULL
       ORDER BY alterscore DESC LIMIT 15"""
print(pd.read_sql(q, c).to_string())
