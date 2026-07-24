import sqlite3, pandas as pd
c = sqlite3.connect("alter11.db")
q = """SELECT mf_type, COUNT(*) AS n, ROUND(AVG(tacles_p90 + int_p90), 2) AS act_def,
       ROUND(AVG(buts_p90 + passes_p90), 2) AS impact_off, ROUND(AVG(score_brut), 2) AS score
       FROM v_alterscore WHERE position = 'MF' AND alterscore IS NOT NULL GROUP BY mf_type"""
print(pd.read_sql(q, c).to_string())
