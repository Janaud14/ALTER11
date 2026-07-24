import sqlite3, pandas as pd
c = sqlite3.connect("alter11.db")
q = "SELECT player_name, fd_p90, fls_p90, tacles_p90, int_p90, tirs_p90 FROM v_alterscore WHERE player_name LIKE '%Bamba%'"
print(pd.read_sql(q, c).to_string())
