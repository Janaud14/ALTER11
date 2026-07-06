"""
Scrape les stats FBref de la saison 2024-2025 (5 grands championnats) pour
servir de base à la validation prédictive de l'ALTERSCORE.

Logique : on calcule l'ALTERSCORE sur les U20 de la saison 2024-2025 (avec
la formule actuelle) puis on regarde ce qu'ils sont devenus en 2025-2026
(déjà scrapé) pour voir si le score avait un vrai pouvoir prédictif.

Usage :
    python scripts/scrape_2024_2025.py

Prérequis :
    pip install soccerdata pandas
"""

from pathlib import Path

import pandas as pd
import soccerdata as sd

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT_DIR / "data" / "raw" / "players_data-2024_2025.csv"

LIGUES = [
    "ENG-Premier League",
    "ESP-La Liga",
    "FRA-Ligue 1",
    "GER-Bundesliga",
    "ITA-Serie A",
]

RENAME_MAP = {
    "player": "player_name", "team": "team_name", "league": "competition",
    "pos": "position", "age": "age",
    "Playing Time_MP": "matches_played", "Playing Time_Min": "minutes",
    "Playing Time_90s": "nineties",
    "Performance_Gls": "goals", "Performance_Ast": "assists",
    "Standard_Sh": "shots", "Standard_SoT": "shots_on_target",
    "Performance_Int": "interceptions", "Performance_TklW": "tackles_won",
    "Performance_CrdY": "yellow_cards", "Performance_CrdR": "red_cards",
    "Performance_Fls": "fouls_committed", "Performance_Fld": "fouls_drawn",
    "Performance_Crs": "crosses",
}


def flatten_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Aplatit les colonnes multi-index renvoyées par soccerdata."""
    df.columns = [
        "_".join(filter(None, col)).strip() if isinstance(col, tuple) else col
        for col in df.columns
    ]
    return df


def main():
    fbref = sd.FBref(leagues=LIGUES, seasons=["2425"])

    print("Scraping standard stats...")
    df_standard = flatten_cols(fbref.read_player_season_stats(stat_type="standard").reset_index())
    print(f"  {df_standard.shape}")

    print("Scraping misc...")
    df_misc = flatten_cols(fbref.read_player_season_stats(stat_type="misc").reset_index())
    print(f"  {df_misc.shape}")

    print("Scraping shooting...")
    df_shooting = flatten_cols(fbref.read_player_season_stats(stat_type="shooting").reset_index())
    print(f"  {df_shooting.shape}")

    keys = ["league", "season", "team", "player"]
    df_merged = df_standard.merge(
        df_misc[keys + [c for c in df_misc.columns if c not in df_standard.columns]],
        on=keys, how="left",
    ).merge(
        df_shooting[keys + [c for c in df_shooting.columns
                             if c not in df_standard.columns and c not in df_misc.columns]],
        on=keys, how="left",
    )

    cols_present = {k: v for k, v in RENAME_MAP.items() if k in df_merged.columns}
    df_merged = df_merged.rename(columns=cols_present)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_merged.to_csv(OUTPUT_PATH, index=False)
    print(f"\n✅ Sauvegardé : {OUTPUT_PATH} ({df_merged.shape[0]} lignes)")


if __name__ == "__main__":
    main()
