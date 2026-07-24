import sqlite3, pandas as pd
c = sqlite3.connect("alter11.db")
for grp, cond in [("DF", "position = 'DF'"), ("MF_OFF", "position = 'MF' AND mf_type = 'MF_OFF'")]:
    q = f"""SELECT tacles_p90, int_p90, crs_p90, fd_p90, fls_p90, tirs_p90
            FROM v_alterscore WHERE {cond} AND alterscore IS NOT NULL"""
    print("===", grp, "===")
    print(pd.read_sql(q, c).describe(percentiles=[.5, .95]).round(2).to_string())
    print()
