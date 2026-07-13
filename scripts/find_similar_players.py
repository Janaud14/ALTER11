"""
Trouve les joueurs U20 les plus similaires à un joueur donné, en se basant
sur la distance dans l'espace des 3 composantes ACP déjà calculées pour
ALTER11 (voir notebooks/01_analysis.ipynb, section 5).

Contrairement à l'ALTERSCORE (qui dit "qui est bon"), cet outil répond à
une question différente : "qui joue comme qui" — utile pour trouver une
alternative à un joueur convoité, ou un profil de remplacement.

Usage :
    python scripts/find_similar_players.py "Lamine Yamal" --n 5
    python scripts/find_similar_players.py "Marc Bernal"

Prérequis :
    pip install pandas scikit-learn
"""

import argparse
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "alter11.db"

FEATURES = ["buts_p90", "passes_p90", "tirs_p90", "tacles_p90",
            "int_p90", "fd_p90", "min_pct", "ppm"]


def load_dataset(db_path: Path) -> pd.DataFrame:
    """Charge le même dataset que l'ACP du notebook (minutes >= 200, hors GK).

    xG/xA ont été testés comme dimensions ACP (bruts, puis en écart au réel)
    et retirés dans les deux cas :
      - xg_p90/xa_p90 bruts corrèlent à 0.84 avec tirs_p90/buts_p90 (vérifié
        empiriquement) — quasi redondants, gonflaient l'axe offensif.
      - L'écart buts-xG/passes-xA est trop bruité sur le faible volume de
        tirs/passes clés d'un jeune sur une saison — l'ACP traite ce bruit
        comme un vrai trait de style, ce qui donnait des similarités moins
        cohérentes (vérifié empiriquement sur Lamine Yamal).
    xG/xA restent disponibles en base (voir scripts/scrape_understat.py) pour
    de l'affichage informatif à côté du score de similarité, pas comme
    composante du calcul de distance lui-même.
    """
    q = """
        SELECT
            p.player_name, p.age, p.position, t.team_name,
            ROUND(f.goals / NULLIF(f.nineties, 0), 2)         AS buts_p90,
            ROUND(f.assists / NULLIF(f.nineties, 0), 2)       AS passes_p90,
            ROUND(f.shots / NULLIF(f.nineties, 0), 2)         AS tirs_p90,
            ROUND(f.tackles_won / NULLIF(f.nineties, 0), 2)   AS tacles_p90,
            ROUND(f.interceptions / NULLIF(f.nineties, 0), 2) AS int_p90,
            ROUND(f.fouls_drawn / NULLIF(f.nineties, 0), 2)   AS fd_p90,
            ROUND(f.minutes * 100.0 / NULLIF(f.matches_played * 90.0, 0), 1) AS min_pct,
            ROUND(f.points_per_match, 2)                      AS ppm
        FROM fact_stats f
        JOIN dim_player p ON f.player_id = p.player_id
        JOIN dim_team t ON p.team_id = t.team_id
        WHERE f.minutes >= 200
          AND p.position != 'GK'
    """
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql(q, conn)
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    return df


def build_pca_space(df: pd.DataFrame):
    """Standardise et projette sur 3 composantes, comme dans le notebook d'analyse."""
    df_clean = df.dropna(subset=FEATURES).reset_index(drop=True)
    X = df_clean[FEATURES].values
    X_scaled = StandardScaler().fit_transform(X)
    pca = PCA(n_components=3)
    X_pca = pca.fit_transform(X_scaled)
    return df_clean, X_pca


def find_similar(player_name: str, df_clean: pd.DataFrame, X_pca: np.ndarray,
                  n: int = 5, candidats_u20_only: bool = True):
    """Retourne les n joueurs les plus proches (similarité cosinus sur l'espace ACP).

    Le joueur de référence peut être n'importe qui (U20 ou senior), mais les
    candidats retournés sont limités aux U20 par défaut — ALTER11 sert à
    repérer des jeunes, pas à recommander un international de 30 ans comme
    "alternative".
    """
    matches = df_clean.index[df_clean["player_name"].str.lower() == player_name.lower()]
    if len(matches) == 0:
        # essai de match partiel si le nom exact n'est pas trouvé
        matches = df_clean.index[
            df_clean["player_name"].str.lower().str.contains(player_name.lower())
        ]
    if len(matches) == 0:
        print(f"❌ Aucun joueur trouvé pour '{player_name}' "
              f"(minutes >= 200 requis, gardiens exclus)")
        return None

    idx = matches[0]
    ref_name = df_clean.loc[idx, "player_name"]
    if len(matches) > 1:
        print(f"⚠️ Plusieurs correspondances, on utilise : {ref_name}")

    similarities = cosine_similarity([X_pca[idx]], X_pca)[0]
    df_result = df_clean.copy()
    df_result["similarite"] = similarities
    df_result = df_result[df_result.index != idx]

    if candidats_u20_only:
        df_result = df_result[df_result["age"] <= 20]

    df_result = df_result.sort_values("similarite", ascending=False)

    return ref_name, df_result.head(n)


def load_xg_info(db_path: Path) -> pd.DataFrame:
    """xG/xA affichés à titre informatif seulement — pas utilisés dans le
    calcul de similarité (voir docstring de load_dataset pour pourquoi)."""
    q = """
        SELECT p.player_name,
               ROUND(f.xg / NULLIF(f.nineties, 0), 2) AS xg_p90,
               ROUND(f.xa / NULLIF(f.nineties, 0), 2) AS xa_p90
        FROM fact_stats f
        JOIN dim_player p ON f.player_id = p.player_id
    """
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(q, conn)


def main():
    parser = argparse.ArgumentParser(description="Trouve les joueurs U20 similaires à un joueur donné.")
    parser.add_argument("player", help="Nom du joueur de référence (ex: 'Lamine Yamal')")
    parser.add_argument("--n", type=int, default=5, help="Nombre de joueurs similaires à afficher")
    parser.add_argument("--include-seniors", action="store_true",
                         help="Inclure aussi les joueurs > 20 ans dans les résultats")
    args = parser.parse_args()

    df = load_dataset(DB_PATH)
    df_clean, X_pca = build_pca_space(df)

    result = find_similar(args.player, df_clean, X_pca, n=args.n,
                           candidats_u20_only=not args.include_seniors)
    if result is None:
        return

    ref_name, df_top = result
    df_xg = load_xg_info(DB_PATH)
    df_top = df_top.merge(df_xg, on="player_name", how="left")

    print(f"\n🔵 Joueurs les plus similaires à {ref_name} :\n")
    cols = ["player_name", "team_name", "age", "position", "similarite", "xg_p90", "xa_p90"]
    df_top_display = df_top[cols].copy()
    df_top_display["similarite"] = (df_top_display["similarite"] * 100).round(1)
    print(df_top_display.to_string(index=False))
    print("\n(xG/xA affichés à titre informatif — n'entrent pas dans le calcul de similarité)")


if __name__ == "__main__":
    main()
