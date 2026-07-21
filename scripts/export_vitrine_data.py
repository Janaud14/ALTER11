"""
Génère players.json à partir des vraies données ALTER11 (alter11.db), pour
que la vitrine web (index.html) affiche l'ALTERSCORE réel au lieu de valeurs
codées en dur et déconnectées du pipeline.

La formule de l'ALTERSCORE n'est PAS recopiée ici : ce script lit la vue
v_alterscore (sql/00_view_alterscore.sql), qui est la source unique de vérité
du projet. Ce fichier ne fait que mettre en forme pour la vitrine (percentiles
par groupe de comparaison, stats affichées au dos des cartes, photos locales).

Prérequis :
    pip install pandas
    sqlite3 alter11.db < sql/00_view_alterscore.sql

Usage :
    python scripts/export_vitrine_data.py
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "alter11.db"
VIEW_PATH = ROOT_DIR / "sql" / "00_view_alterscore.sql"
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


def load_scored_players(db_path: Path) -> pd.DataFrame:
    """
    Tous les joueurs effectivement scorés (pas seulement le top 10 par poste).
    Contrairement à l'export Power BI, on exclut ici les joueurs sans
    ALTERSCORE : une carte de vitrine sans score n'aurait rien à afficher.
    """
    q = """
        SELECT *
        FROM v_alterscore
        WHERE alterscore IS NOT NULL
        ORDER BY alterscore DESC
    """
    with sqlite3.connect(db_path) as conn:
        verifier_vue(conn)
        return pd.read_sql(q, conn)


def find_local_photo(player_name: str) -> str | None:
    """Cherche une photo locale déjà générée pour ce joueur (voir generate_cards.py)."""
    candidat = PHOTOS_DIR / f"{player_name.replace(' ', '_')}.png"
    if candidat.exists():
        return f"data/photos/{candidat.name}"
    return None


def build_players_json(df: pd.DataFrame) -> list:
    df = df.copy()

    colonnes_a_zero = [
        "buts_p90", "passes_p90", "tirs_p90", "tacles_p90", "int_p90",
        "fd_p90", "fls_p90", "crs_p90", "min_pct", "ppm",
        "np_goals_p90", "npxg_p90",
    ]
    for col in colonnes_a_zero:
        df[col] = df[col].fillna(0)

    # Même valeur de repli que dans la formule FW de la vue, pour rester cohérent
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
        df[f"pct_{col}"] = (
            df.groupby("groupe_pct")[col].rank(pct=True).mul(100).round(0).astype(int)
        )

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
            # L'âge est déjà normalisé en entier par la vue (CAST), plus besoin
            # de gérer le format FBref "années-jours" ici.
            "age": int(row["age"]),
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
    print(f"Joueurs scores : {len(df)}")

    players = build_players_json(df)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)

    print(f"OK - {len(players)} joueurs exportes vers {OUTPUT_PATH}")
    print(f"     Top 3 : {[p['name'] + ' (' + str(p['score']) + ')' for p in players[:3]]}")


if __name__ == "__main__":
    main()
