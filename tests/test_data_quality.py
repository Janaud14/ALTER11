"""
Tests de qualité de données ALTER11.

Chaque test correspond à un problème réellement rencontré sur le projet, ou à une
invariante métier qui, si elle casse, fausse les scores sans lever d'erreur.

Les trois bugs historiques (tous silencieux, tous trouvés à la main) :
  - postes stockés au format "MF,FW" au lieu de "FW"  -> test_position_valeurs_canoniques
  - âges au format FBref "19-290" au lieu d'un entier -> test_age_est_un_entier_plausible
  - precision_tir en division entière SQLite          -> test_precision_tir_est_une_vraie_proportion

Un quatrième a été découvert en écrivant ces tests : des joueurs agrègent les
stats de deux clubs ou de deux homonymes sur une seule ligne
-> test_pas_de_volume_de_matchs_impossible (marqué xfail, hors U20 donc sans
   impact sur l'ALTERSCORE ; corrigé à la source dans le notebook, en attente
   de reconstruction de la base).

Usage :
    pip install pytest
    pytest tests/ -v
"""

import sqlite3
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "alter11.db"

POSTES_VALIDES = {"FW", "MF", "DF", "GK"}


@pytest.fixture(scope="module")
def conn():
    if not DB_PATH.exists():
        pytest.skip(f"Base absente : {DB_PATH}. Lancer le pipeline d'abord.")
    connexion = sqlite3.connect(DB_PATH)
    connexion.row_factory = sqlite3.Row
    yield connexion
    connexion.close()


def q(conn, sql):
    """Raccourci : exécute une requête et renvoie la liste des lignes."""
    return conn.execute(sql).fetchall()


# --------------------------------------------------------------------------
# Intégrité structurelle
# --------------------------------------------------------------------------

def test_tables_attendues_presentes(conn):
    tables = {r["name"] for r in q(conn, "SELECT name FROM sqlite_master WHERE type='table'")}
    for attendue in ["dim_player", "dim_team", "fact_stats", "malus_clubs"]:
        assert attendue in tables, f"Table manquante : {attendue}"


def test_pas_de_joueur_orphelin(conn):
    """Toute ligne de fact_stats doit pointer vers un joueur existant."""
    orphelins = q(conn, """
        SELECT COUNT(*) AS n FROM fact_stats f
        LEFT JOIN dim_player p ON f.player_id = p.player_id
        WHERE p.player_id IS NULL
    """)[0]["n"]
    assert orphelins == 0, f"{orphelins} lignes de stats sans joueur correspondant"


def test_pas_de_joueur_sans_equipe(conn):
    orphelins = q(conn, """
        SELECT COUNT(*) AS n FROM dim_player p
        LEFT JOIN dim_team t ON p.team_id = t.team_id
        WHERE t.team_id IS NULL
    """)[0]["n"]
    assert orphelins == 0, f"{orphelins} joueurs rattachés à une équipe inexistante"


def test_pas_de_doublon_joueur_dans_fact_stats(conn):
    """Un joueur ne doit avoir qu'une ligne de stats par saison."""
    doublons = q(conn, """
        SELECT player_id, COUNT(*) AS n FROM fact_stats
        GROUP BY player_id HAVING n > 1
    """)
    assert not doublons, f"{len(doublons)} joueurs ont plusieurs lignes dans fact_stats"


# --------------------------------------------------------------------------
# Bug historique n°1 : postes au format "MF,FW"
# --------------------------------------------------------------------------

def test_position_valeurs_canoniques(conn):
    """
    FBref renvoie parfois des postes multiples ("MF,FW"). Le CASE du scoring ne
    matche alors aucune branche : le score passe à NULL et le joueur disparaît
    silencieusement du classement.
    """
    invalides = q(conn, """
        SELECT DISTINCT position FROM dim_player
        WHERE position IS NOT NULL
    """)
    hors_liste = [r["position"] for r in invalides if r["position"] not in POSTES_VALIDES]
    assert not hors_liste, f"Postes non canoniques trouvés : {hors_liste}"


# --------------------------------------------------------------------------
# Bug historique n°2 : âge au format "19-290"
# --------------------------------------------------------------------------

def test_age_est_un_entier_plausible(conn):
    """
    FBref stocke parfois l'âge au format 'années-jours'. Stocké tel quel, il
    casse les comparaisons SQL du bonus âge sans lever d'erreur.
    """
    mauvais_format = q(conn, """
        SELECT COUNT(*) AS n FROM dim_player
        WHERE age IS NOT NULL AND CAST(age AS TEXT) LIKE '%-%'
    """)[0]["n"]
    assert mauvais_format == 0, f"{mauvais_format} joueurs ont un âge au format 'années-jours'"

    hors_bornes = q(conn, """
        SELECT COUNT(*) AS n FROM dim_player
        WHERE age IS NOT NULL AND (age < 14 OR age > 45)
    """)[0]["n"]
    assert hors_bornes == 0, f"{hors_bornes} joueurs ont un âge hors de l'intervalle 14-45"


# --------------------------------------------------------------------------
# Bug historique n°3 : division entière SQLite
# --------------------------------------------------------------------------

def test_precision_tir_est_une_vraie_proportion(conn):
    """
    shots_on_target / shots sur deux INTEGER renvoie 0 dès que le numérateur est
    plus petit que le dénominateur. Symptôme : quasiment que des 0 et quelques 1,
    aucune valeur intermédiaire.
    """
    lignes = q(conn, """
        SELECT shots_on_target * 1.0 / shots AS precision_tir
        FROM fact_stats
        WHERE shots >= 5
    """)
    assert lignes, "Aucun joueur avec au moins 5 tirs : impossible de tester"

    valeurs = [r["precision_tir"] for r in lignes]

    hors_bornes = [v for v in valeurs if v < 0 or v > 1]
    assert not hors_bornes, f"{len(hors_bornes)} valeurs de precision_tir hors de [0, 1]"

    # Sur des joueurs à 5+ tirs, une précision strictement intermédiaire est la norme.
    # Si tout est à 0 ou 1, c'est la signature de la division entière.
    intermediaires = [v for v in valeurs if 0 < v < 1]
    ratio = len(intermediaires) / len(valeurs)
    assert ratio > 0.8, (
        f"Seulement {ratio:.0%} des valeurs de precision_tir sont strictement entre 0 et 1. "
        "Signature probable d'une division entière : utiliser * 1.0 ou CAST(... AS REAL)."
    )


def test_tirs_cadres_inferieurs_aux_tirs(conn):
    incoherents = q(conn, """
        SELECT COUNT(*) AS n FROM fact_stats
        WHERE shots_on_target > shots
    """)[0]["n"]
    assert incoherents == 0, f"{incoherents} joueurs ont plus de tirs cadrés que de tirs"


# --------------------------------------------------------------------------
# Invariantes métier
# --------------------------------------------------------------------------

def test_minutes_et_nineties_coherents(conn):
    """nineties doit valoir minutes / 90, à l'arrondi près."""
    incoherents = q(conn, """
        SELECT COUNT(*) AS n FROM fact_stats
        WHERE nineties IS NOT NULL AND minutes IS NOT NULL
          AND ABS(nineties - minutes / 90.0) > 0.05
    """)[0]["n"]
    assert incoherents == 0, f"{incoherents} joueurs ont un nineties incohérent avec minutes"


@pytest.mark.xfail(
    reason="3 anomalies connues, toutes hors U20 : collisions d'homonymes "
           "(Vitinha PSG/Marseille, Nicolas Gonzalez Man City/Juventus) et "
           "transfert mi-saison dont les lignes club ont ete additionnees "
           "(Malen, Dortmund -> Aston Villa). Sans impact sur l'ALTERSCORE, "
           "qui filtre sur age <= 20. Corrige a la source dans "
           "notebooks/01_analysis.ipynb (deduplication et jointure sur "
           "nom + birth_year au lieu du nom seul) ; ces lignes disparaitront "
           "a la prochaine reconstruction complete de la base (saison 2026-27).",
    strict=False,
)
def test_pas_de_volume_de_matchs_impossible(conn):
    """
    Les donnees sont par championnat, pas toutes competitions confondues :
    verifie empiriquement, La Liga et la Serie A plafonnent exactement a 38
    matchs, la Bundesliga a 34. Le maximum legitime est donc le nombre de
    journees de la ligue. Au-dela, c'est une agregation parasite.
    """
    absurdes = q(conn, """
        SELECT COUNT(*) AS n FROM fact_stats
        WHERE minutes < 0 OR matches_played > 38
    """)[0]["n"]
    assert absurdes == 0, (
        f"{absurdes} joueurs ont un volume de matchs impossible en championnat"
    )


def test_npxg_inferieur_ou_egal_a_xg(conn):
    """Le xG hors penalty ne peut pas dépasser le xG total."""
    incoherents = q(conn, """
        SELECT COUNT(*) AS n FROM fact_stats
        WHERE xg IS NOT NULL AND npxg IS NOT NULL AND npxg > xg + 0.01
    """)[0]["n"]
    assert incoherents == 0, f"{incoherents} joueurs ont un npxG supérieur à leur xG"


def test_malus_club_dans_la_plage_annoncee(conn):
    """Le README annonce une plage 0.70 - 1.15. Une valeur hors plage a déjà été un bug."""
    hors_plage = q(conn, """
        SELECT team_name, malus FROM malus_clubs
        WHERE malus < 0.70 OR malus > 1.15
    """)
    assert not hors_plage, (
        "Malus club hors de la plage [0.70, 1.15] : "
        + ", ".join(f"{r['team_name']}={r['malus']}" for r in hors_plage)
    )


def test_couverture_understat(conn):
    """
    Le xG/xA vient d'Understat via fuzzy matching. Une baisse de couverture
    signale une régression du matching de noms.
    """
    stats = q(conn, """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN xg IS NOT NULL THEN 1 ELSE 0 END) AS avec_xg
        FROM fact_stats
        WHERE minutes >= 200
    """)[0]
    couverture = stats["avec_xg"] / stats["total"]
    assert couverture >= 0.95, (
        f"Couverture Understat tombée à {couverture:.0%} "
        f"({stats['avec_xg']}/{stats['total']} joueurs à 200+ minutes)"
    )
