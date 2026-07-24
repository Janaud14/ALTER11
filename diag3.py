import sqlite3, pandas as pd
c = sqlite3.connect("alter11.db")
q = """SELECT tacles_p90, int_p90, fd_p90, fls_p90 FROM v_alterscore
       WHERE position = 'MF' AND mf_type = 'MF_DEF' AND alterscore IS NOT NULL"""
d = pd.read_sql(q, c)
print(d.describe(percentiles=[.5, .75, .9, .95, .99]).round(2).to_string())
