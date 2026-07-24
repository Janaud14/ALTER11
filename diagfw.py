import sqlite3, pandas as pd
c = sqlite3.connect("alter11.db")
q = """SELECT np_goals_p90, npxg_p90, tirs_p90, passes_p90, precision_tir, ppm
       FROM v_alterscore WHERE position = 'FW' AND alterscore IS NOT NULL"""
print(pd.read_sql(q, c).describe(percentiles=[.5, .95]).round(2).to_string())
