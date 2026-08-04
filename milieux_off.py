import sqlite3, pandas as pd
c = sqlite3.connect("alter11.db")
q = """
SELECT player_name, age, team_name, competition, minutes,
       buts_p90, passes_p90, tirs_p90, fd_p90, alterscore
FROM v_alterscore
WHERE position = 'MF' AND mf_type = 'MF_OFF' AND alterscore IS NOT NULL
ORDER BY alterscore DESC
LIMIT 12
"""
print(pd.read_sql(q, c).to_string())
