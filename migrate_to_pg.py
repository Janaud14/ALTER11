"""
Migration des donnees ALTER11 : SQLite -> PostgreSQL.

Copie les tables de base (celles qui contiennent les donnees brutes) depuis
alter11.db vers le PostgreSQL tournant dans Docker. Ne copie PAS la vue
v_alterscore : une vue se recree par-dessus les tables, elle ne se migre pas.
On la recreera ensuite (adaptee a la syntaxe Postgres), ou mieux, dbt la
remplacera.

Prerequis :
    pip install pandas sqlalchemy "psycopg[binary]"
    docker compose up -d   (Postgres doit tourner sur le port 5433)

Usage :
    python migrate_to_pg.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

ROOT_DIR = Path(__file__).resolve().parent
SQLITE_PATH = ROOT_DIR / "alter11.db"

# psycopg v3 via SQLAlchemy : le driver s'appelle "psycopg" (pas psycopg2)
PG_URL = "postgresql+psycopg://alter11:alter11@127.0.0.1:5433/alter11"

# Les tables de base a migrer, dans l'ordre (les dimensions avant les faits,
# meme si ici on ne pose pas encore de cles etrangeres).
TABLES = ["dim_team", "dim_player", "malus_clubs", "fact_stats"]


def main():
    if not SQLITE_PATH.exists():
        raise SystemExit(f"Base SQLite introuvable : {SQLITE_PATH}")

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    pg_engine = create_engine(PG_URL)

    # Verifie que la cible repond avant de commencer
    with pg_engine.connect() as c:
        version = c.execute(text("SELECT version()")).scalar()
        print(f"Cible PostgreSQL : {version[:40]}")
        print()

    for table in TABLES:
        # Lecture depuis SQLite
        try:
            df = pd.read_sql(f"SELECT * FROM {table}", sqlite_conn)
        except Exception as e:
            print(f"  [SKIP] {table} : absente de SQLite ({e})")
            continue

        # Ecriture dans Postgres (remplace la table si elle existe deja,
        # pour que le script soit rejouable sans erreur)
        df.to_sql(table, pg_engine, if_exists="replace", index=False)
        print(f"  [OK]   {table:15} -> {len(df):5} lignes, {len(df.columns)} colonnes")

    sqlite_conn.close()

    # Controle final : recompte cote Postgres pour confirmer que tout est arrive
    print()
    print("Verification cote PostgreSQL :")
    with pg_engine.connect() as c:
        for table in TABLES:
            try:
                n = c.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"  {table:15} : {n} lignes")
            except Exception:
                print(f"  {table:15} : absente")

    print()
    print("Migration terminee.")


if __name__ == "__main__":
    main()
