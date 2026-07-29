import glob
for f in glob.glob("scripts/*.py") + glob.glob("*.py"):
    try:
        txt = open(f, encoding="utf-8").read()
    except:
        continue
    if "to_sql" in txt or "dim_player" in txt or "INSERT INTO" in txt:
        print(f)
