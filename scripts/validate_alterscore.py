"""
Validation prédictive de l'ALTERSCORE.

Principe : calculer l'ALTERSCORE des U20 sur la saison 2024-2025 (formule
actuelle, SANS malus club — voir note de méthodologie ci-dessous), puis
regarder si ce score corrèle avec leur évolution de temps de jeu la saison
suivante (2025-2026, déjà en base).

Note de méthodologie : le malus club (coefficient d'exposition médiatique)
n'est pas appliqué ici car il demanderait de ressaisir les points par équipe
de la saison 2024-2025. Le score utilisé est donc : formule par poste +
bonus âge + coefficient de fiabilité, sans correction club. C'est une
simplification assumée de cette validation, pas du score de production.

Limite structurelle à garder en tête : biais de survie. Seuls les joueurs
encore présents dans les 5 grands championnats en 2025-2026 peuvent être
suivis — ceux relégués en D2, transférés hors des 5 ligues, ou avec une
carrière arrêtée, sortent de l'échantillon.

Usage :
    python scripts/validate_alterscore.py
    (après avoir lancé scrape_2024_2025.py)

Prérequis :
    pip install pandas numpy scipy matplotlib rapidfuzz
"""

from pathlib import Path
import sqlite3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from rapidfuzz import fuzz
from scipy import stats

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_2425 = ROOT_DIR / "data" / "raw" / "players_data-2024_2025.csv"
DB_PATH = ROOT_DIR / "alter11.db"

FEATURES_FW = {"tirs_p90": (5.0, 0.25), "buts_p90": (1.0, 0.25),
               "passes_p90": (0.8, 0.15), "min_pct": (100, 0.15), "ppm": (3.0, 0.05)}


def per90(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule les variables par 90 minutes nécessaires au scoring."""
    df = df.copy()
    df["min_pct"] = (df["minutes"] * 100 / (df["matches_played"] * 90)).round(1)
    for src, dst in [("goals", "buts_p90"), ("assists", "passes_p90"),
                     ("shots", "tirs_p90"), ("tackles_won", "tacles_p90"),
                     ("interceptions", "int_p90"), ("fouls_drawn", "fd_p90"),
                     ("fouls_committed", "fls_p90"), ("crosses", "crs_p90")]:
        if src in df.columns:
            df[dst] = (df[src] / df["nineties"].replace(0, np.nan)).round(2)
    return df


def bonus_age(age: float) -> float:
    if age <= 17:
        return 2.0
    if age <= 18:
        return 1.7
    if age <= 19:
        return 1.4
    if age == 20:
        return 1.1
    return 0.8


def coef_fiab(minutes: float) -> float:
    return min(1.0, 0.5 + minutes / 3000.0)


def score_fw(row) -> float:
    return round(
        min(row["tirs_p90"], 5.0) / 5.0 * 10 * 0.25
        + min(row["buts_p90"], 1.0) / 1.0 * 10 * 0.25
        + min(row["passes_p90"], 0.8) / 0.8 * 10 * 0.15
        + min(row["min_pct"], 100) / 100 * 10 * 0.15
        + min(row.get("ppm", 0) or 0, 3.0) / 3.0 * 10 * 0.05
        + bonus_age(row["age"]) * 0.15 * 10 / 2.0, 1)


def score_df(row) -> float:
    return round(
        min(row["tacles_p90"], 4.0) / 4.0 * 10 * 0.22
        + min(row["int_p90"], 3.0) / 3.0 * 10 * 0.20
        + min(row["fd_p90"], 3.0) / 3.0 * 10 * 0.08
        + min(row["fls_p90"], 4.0) / 4.0 * 10 * 0.05
        + min(row.get("crs_p90", 0) or 0, 3.0) / 3.0 * 10 * 0.10
        + min(row.get("ppm", 0) or 0, 3.0) / 3.0 * 10 * 0.10
        + min(row["min_pct"], 100) / 100 * 10 * 0.10
        + bonus_age(row["age"]) * 0.15 * 10 / 2.0, 1)


def score_mf(row) -> float:
    defensif = (row["tacles_p90"] + row["int_p90"]) > (row["buts_p90"] + row["passes_p90"]) * 3
    if defensif:
        return round(
            min(row["tacles_p90"], 4.0) / 4.0 * 10 * 0.25
            + min(row["int_p90"], 3.0) / 3.0 * 10 * 0.25
            + min(row["fd_p90"], 3.0) / 3.0 * 10 * 0.10
            + min(row["fls_p90"], 4.0) / 4.0 * 10 * 0.05
            + min(row.get("ppm", 0) or 0, 3.0) / 3.0 * 10 * 0.10
            + min(row["min_pct"], 100) / 100 * 10 * 0.10
            + bonus_age(row["age"]) * 0.15 * 10 / 2.0, 1)
    return round(
        min(row["tacles_p90"], 4.0) / 4.0 * 10 * 0.10
        + min(row["int_p90"], 3.0) / 3.0 * 10 * 0.10
        + min(row["buts_p90"] + row["passes_p90"], 1.0) / 1.0 * 10 * 0.25
        + min(row["tirs_p90"], 3.0) / 3.0 * 10 * 0.20
        + min(row["fd_p90"], 3.0) / 3.0 * 10 * 0.10
        + min(row.get("ppm", 0) or 0, 3.0) / 3.0 * 10 * 0.05
        + min(row["min_pct"], 100) / 100 * 10 * 0.10
        + bonus_age(row["age"]) * 0.15 * 10 / 2.0, 1)


def compute_score_brut(df: pd.DataFrame) -> pd.DataFrame:
    """Applique la formule par poste (sans malus club, voir note en tête)."""
    df = df.copy()
    scores = []
    for _, row in df.iterrows():
        pos = row["position"]
        min_req = {"FW": 300, "MF": 400, "DF": 500}.get(pos, 400)
        if row["minutes"] < min_req:
            scores.append(None)
            continue
        if pos == "FW":
            scores.append(score_fw(row))
        elif pos == "MF":
            scores.append(score_mf(row))
        elif pos == "DF":
            scores.append(score_df(row))
        else:
            scores.append(None)
    df["score_brut"] = scores
    df["alterscore_sans_malus"] = (df["score_brut"] * df["minutes"].apply(coef_fiab)).round(1)
    return df


def match_player(name: str, candidates: list[str], min_score: int = 85):
    """Trouve le meilleur match d'un nom de joueur dans une liste de candidats."""
    best, best_score = None, 0
    for c in candidates:
        s = fuzz.ratio(name.lower(), c.lower())
        if s > best_score:
            best, best_score = c, s
    return (best, best_score) if best_score >= min_score else (None, best_score)


def load_2526_from_db(db_path: Path) -> pd.DataFrame:
    """Charge les stats 2025-26 déjà nettoyées depuis alter11.db (fact_stats + dim_player)."""
    q = """
        SELECT p.player_name, f.minutes, f.matches_played
        FROM fact_stats f
        JOIN dim_player p ON f.player_id = p.player_id
    """
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql(q, conn)


def main():
    df_2425 = pd.read_csv(DATA_2425)
    df_2526 = load_2526_from_db(DB_PATH)

    df_2425 = per90(df_2425)
    df_2425["age"] = pd.to_numeric(df_2425["age"], errors="coerce")
    u20_2425 = df_2425[(df_2425["age"] <= 20) & (df_2425["position"] != "GK")].copy()
    u20_2425 = compute_score_brut(u20_2425).dropna(subset=["alterscore_sans_malus"])

    print(f"U20 scorés en 2024-2025 : {len(u20_2425)}")

    # min_pct de la saison suivante, pour ceux qu'on retrouve
    df_2526["min_pct_2526"] = (
        df_2526["minutes"] * 100 / (df_2526["matches_played"] * 90)
    ).round(1)
    noms_2526 = df_2526["player_name"].dropna().unique().tolist()

    resultats = []
    for _, row in u20_2425.iterrows():
        match, score = match_player(row["player_name"], noms_2526)
        if match:
            min_pct_2526 = df_2526.loc[
                df_2526["player_name"] == match, "min_pct_2526"
            ].mean()
            resultats.append({
                "player_name": row["player_name"],
                "alterscore_2425": row["alterscore_sans_malus"],
                "min_pct_2425": row["min_pct"],
                "min_pct_2526": min_pct_2526,
                "delta_min_pct": min_pct_2526 - row["min_pct"],
            })

    df_val = pd.DataFrame(resultats).dropna(subset=["delta_min_pct"])

    attrition = 1 - len(df_val) / len(u20_2425)
    print(f"Retrouvés en 2025-2026 : {len(df_val)}/{len(u20_2425)} "
          f"(attrition {attrition:.0%} — biais de survie à garder en tête)")

    if len(df_val) < 15:
        print("⚠️ Échantillon trop petit pour une corrélation fiable. "
              "Résultats à interpréter avec une prudence extrême.")

    corr, p_value = stats.spearmanr(df_val["alterscore_2425"], df_val["delta_min_pct"])
    print(f"\nCorrélation de Spearman GLOBALE (ALTERSCORE 2024-25 vs Δ% temps de jeu) : "
          f"{corr:.3f} (p={p_value:.3f})")

    # Segmentation par poste : un vrai signal peut être noyé si FW/MF/DF
    # réagissent différemment (ex : un DF au niveau peut rester sur le banc
    # pour des raisons hors performance, ce qui bruite le pool global).
    u20_2425_pos = (
        u20_2425.drop_duplicates(subset="player_name")
        .set_index("player_name")["position"]
    )
    df_val["position"] = df_val["player_name"].map(u20_2425_pos)

    print("\nCorrélations par poste :")
    corr_par_poste = {}
    for pos in ["FW", "MF", "DF"]:
        sous = df_val[df_val["position"] == pos]
        if len(sous) < 10:
            print(f"  {pos} : échantillon trop petit ({len(sous)}), corrélation non calculée")
            continue
        c, p = stats.spearmanr(sous["alterscore_2425"], sous["delta_min_pct"])
        corr_par_poste[pos] = (c, p, len(sous))
        print(f"  {pos} (n={len(sous)}) : r={c:.3f}, p={p:.3f}")


    fig, ax = plt.subplots(figsize=(9, 6))
    couleurs_poste = {"FW": "#d73027", "MF": "#fee090", "DF": "#4575b4"}
    for pos, couleur in couleurs_poste.items():
        sous = df_val[df_val["position"] == pos]
        ax.scatter(sous["alterscore_2425"], sous["delta_min_pct"],
                   alpha=0.75, s=60, c=couleur, label=pos, edgecolors="black", linewidths=0.3)
    ax.legend(title="Poste")
    z = np.polyfit(df_val["alterscore_2425"], df_val["delta_min_pct"], 1)
    x_line = np.linspace(df_val["alterscore_2425"].min(), df_val["alterscore_2425"].max(), 100)
    ax.plot(x_line, np.poly1d(z)(x_line), color="crimson", lw=2, ls="--")
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_xlabel("ALTERSCORE 2024-2025 (sans malus club)")
    ax.set_ylabel("Δ % temps de jeu (2025-26 vs 2024-25)")
    ax.set_title(f"Validation prédictive ALTERSCORE — Spearman r={corr:.2f}, p={p_value:.3f}")
    plt.tight_layout()
    plt.savefig(ROOT_DIR / "validation_predictive.png", dpi=150)
    plt.show()

    df_val.to_csv(ROOT_DIR / "validation_predictive.csv", index=False)
    print(f"\nDétail sauvegardé : validation_predictive.csv")


if __name__ == "__main__":
    main()
