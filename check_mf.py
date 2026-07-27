import sqlite3, pandas as pd
c = sqlite3.connect("alter11.db")
q = "SELECT position, mf_type, COUNT(*) AS n FROM v_alterscore GROUP BY position, mf_type ORDER BY position"
print(pd.read_sql(q, c).to_string())
