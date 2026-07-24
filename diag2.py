import pandas as pd, glob
for f in glob.glob("data/raw/*.csv"):
    d = pd.read_csv(f, nrows=1)
    print(f, "->", len(d.columns), "colonnes")
    print(sorted(d.columns.tolist()))
    print()
