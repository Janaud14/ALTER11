"""
Exporte une table plate complète depuis alter11.db vers un CSV, pensée pour
Power BI (ou tout autre outil de dataviz) — plus large que juste l'ALTERSCORE :
inclut tous les U20 avec au moins 200 minutes jouées (seuil déjà utilisé
ailleurs dans le projet pour l'ACP/similarité), toutes les stats par 90, le
xG/xA, et les infos club/ligue.

Le seuil de 200 minutes est nécessaire même pour les stats "par 90" brutes,
pas seulement pour l'ALTERSCORE : sous ce seuil, diviser par un nombre de
minutes proche de zéro donne des taux par 90 complètement démesurés (ex :
1 but sur 10 minutes jouées = un taux de 9 buts/90, statistiquement absurde)
qui écrasent toute visualisation les incluant.

Usage :
    python scripts/export_power_bi.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "alter11.db"
OUTPUT_PATH = ROOT_DIR / "alter11_power_bi.csv"


def parse_age(age_raw) -> int:
    """Gère le format FBref 'années-jours' (ex: '19-290') en plus des entiers simples."""
    s = str(age_raw)
    if "-" in s:
        s = s.split("-")[0]
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def load_full_table(db_path: Path) -> pd.DataFrame:
    q = """
        WITH base AS (
            SELECT
                p.player_name, p.age AS age_raw, p.position, t.team_name,
                t.competition,
                f.minutes, f.nineties, f.matches_played,
                ROUND(f.minutes * 100.0 / NULLIF(f.matches_played * 90.0, 0), 1) AS min_pct,
                ROUND(f.goals / NULLIF(f.nineties, 0), 2)              AS buts_p90,
                ROUND(f.assists / NULLIF(f.nineties, 0), 2)            AS passes_p90,
                ROUND(f.shots / NULLIF(f.nineties, 0), 2)              AS tirs_p90,
                ROUND(COALESCE(f.shots_on_target, 0) * 1.0 / NULLIF(f.shots, 0), 3) AS precision_tir,
                ROUND(f.tackles_won / NULLIF(f.nineties, 0), 2)        AS tacles_p90,
                ROUND(f.interceptions / NULLIF(f.nineties, 0), 2)      AS int_p90,
                ROUND(f.fouls_drawn / NULLIF(f.nineties, 0), 2)        AS fd_p90,
                ROUND(f.fouls_committed / NULLIF(f.nineties, 0), 2)    AS fls_p90,
                ROUND(f.crosses / NULLIF(f.nineties, 0), 2)            AS crs_p90,
                ROUND(f.points_per_match, 2)                           AS ppm,
                ROUND(f.xg / NULLIF(f.nineties, 0), 2)                 AS xg_p90,
                ROUND(f.xa / NULLIF(f.nineties, 0), 2)                 AS xa_p90,
                ROUND(f.npxg / NULLIF(f.nineties, 0), 2)               AS npxg_p90,
                ROUND(COALESCE(f.np_goals, f.goals) / NULLIF(f.nineties, 0), 2) AS np_goals_p90,
                COALESCE(m.malus, 1.0)                                 AS coef_club,
                CASE
                    WHEN p.age <= 17 THEN 2.0 WHEN p.age <= 18 THEN 1.7
                    WHEN p.age <= 19 THEN 1.4 WHEN p.age = 20  THEN 1.1
                    ELSE 0.8
                END AS bonus_age,
                MIN(1.0, 0.5 + (f.minutes / 3000.0)) AS coef_fiab,
                CASE
                    WHEN (f.tackles_won + f.interceptions) / NULLIF(f.nineties, 0)
                       > (f.goals + f.assists) / NULLIF(f.nineties, 0) * 3
                    THEN 'MF_DEF' ELSE 'MF_OFF'
                END AS mf_type
            FROM fact_stats f
            JOIN dim_player p ON f.player_id = p.player_id
            JOIN dim_team t ON p.team_id = t.team_id
            LEFT JOIN malus_clubs m ON t.team_name = m.team_name
            WHERE p.age <= 20 AND p.position != 'GK'
              AND f.minutes >= 200
        ),
        scored AS (
            SELECT *,
                CASE position
                    WHEN 'FW' THEN CASE WHEN minutes < 300 THEN NULL ELSE ROUND(
                        (MIN(np_goals_p90, 1.0) / 1.0 * 10 * 0.25)
                      + (MIN(npxg_p90, 1.0) / 1.0 * 10 * 0.07)
                      + (MIN(tirs_p90, 5.0) / 5.0 * 10 * 0.08)
                      + (COALESCE(precision_tir, 0.35) * 10 * 0.10)
                      + (MIN(passes_p90, 0.8) / 0.8 * 10 * 0.15)
                      + (MIN(min_pct, 100) / 100.0 * 10 * 0.15)
                      + (MIN(ppm, 3.0) / 3.0 * 10 * 0.05)
                      + (bonus_age * 0.15 * 10 / 2.0), 1) END
                    WHEN 'MF' THEN CASE WHEN minutes < 400 THEN NULL ELSE ROUND(
                        CASE mf_type
                        WHEN 'MF_DEF' THEN
                            (MIN(tacles_p90, 4.0) / 4.0 * 10 * 0.25)
                          + (MIN(int_p90, 3.0) / 3.0 * 10 * 0.25)
                          + (MIN(fd_p90, 3.0) / 3.0 * 10 * 0.10)
                          + (MIN(fls_p90, 4.0) / 4.0 * 10 * 0.05)
                          + (MIN(ppm, 3.0) / 3.0 * 10 * 0.10)
                          + (MIN(min_pct, 100) / 100.0 * 10 * 0.10)
                          + (bonus_age * 0.15 * 10 / 2.0)
                        ELSE
                            (MIN(tacles_p90, 4.0) / 4.0 * 10 * 0.10)
                          + (MIN(int_p90, 3.0) / 3.0 * 10 * 0.10)
                          + (MIN(buts_p90 + passes_p90, 1.0) / 1.0 * 10 * 0.25)
                          + (MIN(tirs_p90, 3.0) / 3.0 * 10 * 0.20)
                          + (MIN(fd_p90, 3.0) / 3.0 * 10 * 0.10)
                          + (MIN(ppm, 3.0) / 3.0 * 10 * 0.05)
                          + (MIN(min_pct, 100) / 100.0 * 10 * 0.10)
                          + (bonus_age * 0.15 * 10 / 2.0)
                        END, 1) END
                    WHEN 'DF' THEN CASE WHEN minutes < 500 THEN NULL ELSE ROUND(
                        (MIN(tacles_p90, 4.0) / 4.0 * 10 * 0.22)
                      + (MIN(int_p90, 3.0) / 3.0 * 10 * 0.20)
                      + (MIN(fd_p90, 3.0) / 3.0 * 10 * 0.08)
                      + (MIN(fls_p90, 4.0) / 4.0 * 10 * 0.05)
                      + (MIN(crs_p90, 3.0) / 3.0 * 10 * 0.10)
                      + (MIN(ppm, 3.0) / 3.0 * 10 * 0.10)
                      + (MIN(min_pct, 100) / 100.0 * 10 * 0.10)
                      + (bonus_age * 0.15 * 10 / 2.0), 1) END
                END AS score_brut
            FROM base
        )
        SELECT *, ROUND(score_brut * coef_fiab * coef_club, 1) AS alterscore
        FROM scored
    """
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql(q, conn)

    df["age"] = df["age_raw"].apply(parse_age)
    df = df.drop(columns=["age_raw"])
    return df


def main():
    df = load_full_table(DB_PATH)
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"✅ {len(df)} lignes exportées vers {OUTPUT_PATH}")
    print(f"   Colonnes : {list(df.columns)}")
    print(f"   Dont {df['alterscore'].notna().sum()} avec un ALTERSCORE calculé "
          f"(seuil de minutes atteint)")


if __name__ == "__main__":
    main()
