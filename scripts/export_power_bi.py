"""
Exporte une table plate complète depuis alter11.db vers un CSV, pensée pour
Power BI (ou tout autre outil de dataviz).

La formule de l'ALTERSCORE n'est PAS recopiée ici : ce script lit la vue
v_alterscore (sql/00_view_alterscore.sql), qui est la source unique de vérité
du projet. Ce fichier ne fait que filtrer et écrire le CSV.

Le seuil de 200 minutes est nécessaire même pour les stats "par 90" brutes,
pas seulement pour l'ALTERSCORE : sous ce seuil, diviser par un nombre de
minutes proche de zéro donne des taux par 90 complètement démesurés (ex :
1 but sur 10 minutes jouées = un taux de 9 buts/90, statistiquement absurde)
qui écrasent toute visualisation les incluant.

Contrairement à l'export vitrine, on garde ici les joueurs SANS ALTERSCORE
(entre 200 minutes et le seuil de leur poste) : ils restent pertinents pour
les visualisations descriptives, comme le nuage de points xG.

Prérequis : la vue doit exister.
    sqlite3 alter11.db < sql/00_view_alterscore.sql

Usage :
    python scripts/export_power_bi.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "alter11.db"
VIEW_PATH = ROOT_DIR / "sql" / "00_view_alterscore.sql"
OUTPUT_PATH = ROOT_DIR / "alter11_power_bi.csv"

MINUTES_MIN = 200


def verifier_vue(conn) -> None:
    """
    Échoue explicitement si la vue est absente, plutôt que de laisser remonter
    un 'no such table: v_alterscore' peu parlant.
    """
    existe = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'view' AND name = 'v_alterscore'"
    ).fetchone()

    if not existe:
        raise RuntimeError(
            "La vue v_alterscore est absente de la base.\n"
            f"La créer avec :  sqlite3 alter11.db < {VIEW_PATH.relative_to(ROOT_DIR)}"
        )


def load_full_table(db_path: Path) -> pd.DataFrame:
    q = """
        SELECT *
        FROM v_alterscore
        WHERE minutes >= ?
        ORDER BY alterscore DESC
    """
    with sqlite3.connect(db_path) as conn:
        verifier_vue(conn)
        return pd.read_sql(q, conn, params=(MINUTES_MIN,))


def main():
    df = load_full_table(DB_PATH)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print(f"OK - {len(df)} lignes exportees vers {OUTPUT_PATH}")
    print(f"     Colonnes : {list(df.columns)}")
    print(f"     Dont {df['alterscore'].notna().sum()} avec un ALTERSCORE calcule "
          f"(seuil de minutes par poste atteint)")


if __name__ == "__main__":
    main()
