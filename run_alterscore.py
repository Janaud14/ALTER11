"""
Exécute la requête ALTERSCORE (sql/03_alterscore.sql) et affiche
le top 10 U20 par poste pour les 5 grands championnats européens.

Usage : python run_alterscore.py
(à lancer depuis la racine du projet ALTER11)
"""

import sqlite3
from pathlib import Path

import pandas as pd

# Chemins relatifs à la racine du projet — plus de chemin en dur
ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = ROOT_DIR / "alter11.db"
SQL_PATH = ROOT_DIR / "sql" / "03_alterscore.sql"


def load_query(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_alterscore(db_path: Path, sql_path: Path) -> pd.DataFrame:
    query = load_query(sql_path)
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(query, conn)


if __name__ == "__main__":
    top = run_alterscore(DB_PATH, SQL_PATH)

    print("🔵 ALTERSCORE — Top 10 par poste — U20 — 5 ligues\n")
    for pos in ["FW", "MF", "DF"]:
        print(f"\n{'═' * 60}")
        print(f"  {pos}")
        print("═" * 60)
        print(top[top["position"] == pos].to_string(index=False))
