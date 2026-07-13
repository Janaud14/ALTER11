"""
Génère players.json à partir des vraies données ALTER11 (alter11.db), pour
que la vitrine web (index.html) affiche l'ALTERSCORE réel au lieu de valeurs
codées en dur et déconnectées du pipeline.

Usage :
    python scripts/export_vitrine_data.py

Prérequis :
    pip install pandas
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "alter11.db"
PHOTOS_DIR = ROOT_DIR / "data" / "photos"
OUTPUT_PATH = ROOT_DIR / "players.json"

LIGUE_LABELS = {
    "FRA-Ligue 1": "Ligue 1", "ENG-Premier League": "Premier League",
    "ESP-La Liga": "La Liga", "GER-Bundesliga": "Bundesliga",
    "ITA-Serie A": "Serie A",
    # fallback si les noms en base sont déjà au format FBref d'origine
    "fr Ligue 1": "Ligue 1", "eng Premier League": "Premier League",
    "es La Liga": "La Liga", "de Bundesliga": "Bundesliga", "it Serie A": "Serie A",
}


def load_scored_players(db_path: Path) -> pd.DataFrame:
    """Reprend la logique de sql/03_alterscore.sql, mais retourne tous les
    joueurs scorés (pas seulement le top 10 par poste) pour alimenter la vitrine."""
    q = """
        WITH base AS (
            SELECT
                p.player_name, p.age, p.position, t.team_name, t.competition,
                f.minutes, f.nineties, f.matches_played,
                ROUND(f.minutes * 100.0 / NULLIF(f.matches_played * 90.0, 0), 1) AS min_pct,
                ROUND(f.goals / NULLIF(f.nineties, 0), 2)              AS buts_p90,
                ROUND(f.assists / NULLIF(f.nineties, 0), 2)            AS passes_p90,
                ROUND(f.shots / NULLIF(f.nineties, 0), 2)              AS tirs_p90,
                ROUND(f.tackles_won / NULLIF(f.nineties, 0), 2)        AS tacles_p90,
                ROUND(f.interceptions / NULLIF(f.nineties, 0), 2)      AS int_p90,
                ROUND(f.fouls_drawn / NULLIF(f.nineties, 0), 2)        AS fd_p90,
                ROUND(f.fouls_committed / NULLIF(f.nineties, 0), 2)    AS fls_p90,
                ROUND(f.crosses / NULLIF(f.nineties, 0), 2)            AS crs_p90,
                ROUND(f.points_per_match, 2)                           AS ppm,
                COALESCE(m.malus, 1.0)                                 AS coef_club,
                -- Variables Understat, protégées par COALESCE (voir sql/03_alterscore.sql
                -- pour l'explication détaillée du risque d'exclusion silencieuse)
                ROUND(COALESCE(f.np_goals, f.goals) / NULLIF(f.nineties, 0), 2) AS np_goals_p90,
                ROUND(COALESCE(f.npxg, 0) / NULLIF(f.nineties, 0), 2)           AS npxg_p90,
                ROUND(COALESCE(f.shots_on_target, 0) * 1.0 / NULLIF(f.shots, 0), 3) AS precision_tir,
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
        WHERE score_brut IS NOT NULL
        ORDER BY alterscore DESC
    """
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(q, conn)


def find_local_photo(player_name: str) -> str | None:
    """Cherche une photo locale déjà générée pour ce joueur (voir generate_cards.py)."""
    candidat = PHOTOS_DIR / f"{player_name.replace(' ', '_')}.png"
    if candidat.exists():
        return f"data/photos/{candidat.name}"
    return None


def parse_age(age_raw) -> int:
    """Gère le format FBref 'années-jours' (ex: '19-290') en plus des entiers simples."""
    s = str(age_raw)
    if "-" in s:
        s = s.split("-")[0]
    return int(float(s))


def build_players_json(df: pd.DataFrame) -> list:
    df = df.copy()
    df["buts_p90"] = df["buts_p90"].fillna(0)
    df["passes_p90"] = df["passes_p90"].fillna(0)
    df["tirs_p90"] = df["tirs_p90"].fillna(0)
    df["tacles_p90"] = df["tacles_p90"].fillna(0)
    df["int_p90"] = df["int_p90"].fillna(0)
    df["fd_p90"] = df["fd_p90"].fillna(0)
    df["fls_p90"] = df["fls_p90"].fillna(0)
    df["crs_p90"] = df["crs_p90"].fillna(0)
    df["min_pct"] = df["min_pct"].fillna(0)
    df["ppm"] = df["ppm"].fillna(0)
    df["np_goals_p90"] = df["np_goals_p90"].fillna(0)
    df["npxg_p90"] = df["npxg_p90"].fillna(0)
    df["precision_tir"] = df["precision_tir"].fillna(0.35)
    df["impact_off_p90"] = (df["buts_p90"] + df["passes_p90"]).round(2)
    df["act_def_p90"] = (df["tacles_p90"] + df["int_p90"]).round(2)

    # Groupe de comparaison pour les percentiles : par poste, et pour les
    # milieux, par profil offensif/défensif (mf_type) — comparer le "Tirs/90"
    # d'un défenseur à celui d'un attaquant n'a pas de sens.
    df["groupe_pct"] = df["position"]
    is_mf = df["position"] == "MF"
    df.loc[is_mf, "groupe_pct"] = "MF_" + df.loc[is_mf, "mf_type"].astype(str)

    pct_cols = ["buts_p90", "passes_p90", "tirs_p90", "tacles_p90",
                "int_p90", "fd_p90", "fls_p90", "crs_p90", "min_pct", "ppm",
                "impact_off_p90", "act_def_p90",
                "np_goals_p90", "npxg_p90", "precision_tir"]
    for col in pct_cols:
        df[f"pct_{col}"] = df.groupby("groupe_pct")[col].rank(pct=True).mul(100).round(0).astype(int)

    df = df.sort_values("alterscore", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1

    def stats_for_row(row) -> list:
        """4 stats affichées au dos de la carte, cohérentes avec les variables
        réellement utilisées dans la formule ALTERSCORE pour ce poste/profil."""
        if row["position"] == "FW":
            return [
                {"l": "Buts hors pen./90", "v": f"{row['np_goals_p90']:.2f}", "p": int(row["pct_np_goals_p90"])},
                {"l": "npxG/90", "v": f"{row['npxg_p90']:.2f}", "p": int(row["pct_npxg_p90"])},
                {"l": "Tirs/90", "v": f"{row['tirs_p90']:.2f}", "p": int(row["pct_tirs_p90"])},
                {"l": "Précision tir", "v": f"{row['precision_tir']*100:.0f}%", "p": int(row["pct_precision_tir"])},
                {"l": "Passes déc/90", "v": f"{row['passes_p90']:.2f}", "p": int(row["pct_passes_p90"])},
                {"l": "Min%", "v": f"{row['min_pct']:.1f}%", "p": int(row["pct_min_pct"])},
            ]
        if row["position"] == "MF":
            if row["mf_type"] == "MF_DEF":
                return [
                    {"l": "Tacles/90", "v": f"{row['tacles_p90']:.2f}", "p": int(row["pct_tacles_p90"])},
                    {"l": "Interceptions/90", "v": f"{row['int_p90']:.2f}", "p": int(row["pct_int_p90"])},
                    {"l": "Fautes subies/90", "v": f"{row['fd_p90']:.2f}", "p": int(row["pct_fd_p90"])},
                    {"l": "Fautes commises/90", "v": f"{row['fls_p90']:.2f}", "p": int(row["pct_fls_p90"])},
                    {"l": "PPM équipe", "v": f"{row['ppm']:.2f}", "p": int(row["pct_ppm"])},
                    {"l": "Min%", "v": f"{row['min_pct']:.1f}%", "p": int(row["pct_min_pct"])},
                ]
            return [
                {"l": "Impact Off/90", "v": f"{row['impact_off_p90']:.2f}", "p": int(row["pct_impact_off_p90"])},
                {"l": "Tirs/90", "v": f"{row['tirs_p90']:.2f}", "p": int(row["pct_tirs_p90"])},
                {"l": "Act. Déf/90", "v": f"{row['act_def_p90']:.2f}", "p": int(row["pct_act_def_p90"])},
                {"l": "Fautes subies/90", "v": f"{row['fd_p90']:.2f}", "p": int(row["pct_fd_p90"])},
                {"l": "PPM équipe", "v": f"{row['ppm']:.2f}", "p": int(row["pct_ppm"])},
                {"l": "Min%", "v": f"{row['min_pct']:.1f}%", "p": int(row["pct_min_pct"])},
            ]
        # DF
        return [
            {"l": "Tacles/90", "v": f"{row['tacles_p90']:.2f}", "p": int(row["pct_tacles_p90"])},
            {"l": "Interceptions/90", "v": f"{row['int_p90']:.2f}", "p": int(row["pct_int_p90"])},
            {"l": "Centres/90", "v": f"{row['crs_p90']:.2f}", "p": int(row["pct_crs_p90"])},
            {"l": "Fautes subies/90", "v": f"{row['fd_p90']:.2f}", "p": int(row["pct_fd_p90"])},
            {"l": "PPM équipe", "v": f"{row['ppm']:.2f}", "p": int(row["pct_ppm"])},
            {"l": "Min%", "v": f"{row['min_pct']:.1f}%", "p": int(row["pct_min_pct"])},
        ]

    players = []
    for _, row in df.iterrows():
        players.append({
            "name": row["player_name"],
            "age": parse_age(row["age"]),
            "pos": row["position"],
            "team": row["team_name"],
            "ligue": LIGUE_LABELS.get(row["competition"], row["competition"]),
            "score": row["alterscore"],
            "rank": int(row["rank"]),
            "photo": find_local_photo(row["player_name"]),
            "stats": stats_for_row(row),
        })
    return players


def main():
    df = load_scored_players(DB_PATH)
    print(f"Joueurs scorés : {len(df)}")

    players = build_players_json(df)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(players)} joueurs exportés vers {OUTPUT_PATH}")
    print(f"   Top 3 : {[p['name'] + ' (' + str(p['score']) + ')' for p in players[:3]]}")


if __name__ == "__main__":
    main()
