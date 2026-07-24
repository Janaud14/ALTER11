"""
Tests de cohérence de la formule ALTERSCORE.

Ces tests portent sur la FORMULE elle-même, pas sur les données : ils lisent
sql/00_view_alterscore.sql et vérifient deux invariantes qui, si elles cassent,
faussent les scores sans jamais lever d'erreur.

Origine : deux bugs trouvés à la main en juillet 2026.
  - Le barème des MF_OFF totalisait 1.05 au lieu de 1.00 (soit 5% d'avantage
    structurel pour ce profil), et ça datait des tout premiers commits.
  - Les plafonds des composantes (le X dans MIN(stat, X) / X) avaient été
    choisis a priori, sans regarder les données : 4.0 tacles/90 quand le
    maximum réel chez les U20 est 2.48. Résultat, la moitié du score des
    milieux défensifs était structurellement bridée, et ce profil perdait
    1.5 point de moyenne face aux milieux offensifs.

Usage :
    pytest tests/ -v
"""

import re
import sqlite3
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "alter11.db"
VIEW_PATH = ROOT_DIR / "sql" / "00_view_alterscore.sql"

# Le bonus âge n'est pas écrit sous la forme MIN(stat, X) / X * 10 * poids mais
# sous la forme bonus_age * 0.15 * 10 / 2.0 : son poids est donc 0.15, et la
# somme des autres composantes doit valoir 0.85 pour que le total fasse 1.00.
POIDS_BONUS_AGE = 0.15
TOTAL_ATTENDU = 1.00

# Tolérance de calibrage : un plafond ne devrait pas dépasser de plus de 30%
# la valeur maximale réellement observée. Au-delà, la composante est bridée
# (personne ne peut approcher le plafond) et perd son pouvoir discriminant.
MARGE_PLAFOND = 1.30


@pytest.fixture(scope="module")
def conn():
    if not DB_PATH.exists():
        pytest.skip(f"Base absente : {DB_PATH}")
    connexion = sqlite3.connect(DB_PATH)
    connexion.row_factory = sqlite3.Row
    yield connexion
    connexion.close()


@pytest.fixture(scope="module")
def sql_vue() -> str:
    if not VIEW_PATH.exists():
        pytest.skip(f"Vue absente : {VIEW_PATH}")
    return VIEW_PATH.read_text(encoding="utf-8")


def extraire_blocs(sql: str) -> dict[str, str]:
    """
    Découpe le CASE de scoring en quatre blocs, un par profil.

    Les délimiteurs sont les mots-clés du CASE lui-même (WHEN 'FW', WHEN 'MF',
    WHEN 'MF_DEF', ELSE, WHEN 'DF'), ce qui reste stable même si l'indentation
    ou les retours à la ligne changent.
    """
    # On ne travaille que sur le CTE scored, pas sur le CTE base qui contient
    # lui aussi des CASE (bonus_age, mf_type).
    debut = sql.find("scored AS (")
    if debut == -1:
        pytest.fail("Bloc 'scored AS (' introuvable dans la vue")
    corps = sql[debut:]

    def entre(depuis: str, jusqu_a: str) -> str:
        i = corps.find(depuis)
        if i == -1:
            pytest.fail(f"Marqueur introuvable dans la vue : {depuis!r}")
        j = corps.find(jusqu_a, i + len(depuis))
        return corps[i:j] if j != -1 else corps[i:]

    bloc_mf = entre("WHEN 'MF' THEN", "WHEN 'DF' THEN")

    # Attention : le bloc MF contient DEUX 'ELSE'. Le premier ferme le seuil de
    # minutes (CASE WHEN minutes < 400 THEN NULL ELSE ...), le second sépare
    # MF_DEF de MF_OFF. On cherche donc le ELSE situé APRÈS le marqueur MF_DEF.
    i_def = bloc_mf.find("WHEN 'MF_DEF' THEN")
    if i_def == -1:
        pytest.fail("Marqueur MF_DEF introuvable dans le bloc MF")
    i_else = bloc_mf.find("ELSE", i_def)
    if i_else == -1:
        pytest.fail("Separateur ELSE (MF_DEF / MF_OFF) introuvable")

    return {
        "FW": entre("WHEN 'FW' THEN", "WHEN 'MF' THEN"),
        "MF_DEF": bloc_mf[i_def:i_else],
        "MF_OFF": bloc_mf[i_else:],
        "DF": entre("WHEN 'DF' THEN", "END AS score_brut"),
    }


def poids_du_bloc(bloc: str) -> list[float]:
    """
    Extrait les poids d'un bloc : les nombres qui suivent '* 10 * '.

    On cible ce motif précis plutôt que tous les décimaux du bloc, pour ne pas
    ramasser les plafonds ni les diviseurs.
    """
    return [float(p) for p in re.findall(r"\*\s*10\s*\*\s*(0\.\d+)", bloc)]


def plafonds_du_bloc(bloc: str) -> list[tuple[str, float, float]]:
    """
    Extrait les triplets (variable, plafond, diviseur) des MIN(stat, X) / Y.

    Le diviseur est ramené séparément pour pouvoir vérifier qu'il est bien
    égal au plafond : MIN(tacles_p90, 2.2) / 4.0 ne lève aucune erreur SQL
    mais donne un résultat faux.
    """
    motif = r"MIN\(\s*([a-z_0-9\s\+]+?)\s*,\s*([\d.]+)\s*\)\s*/\s*([\d.]+)"
    return [
        (var.strip(), float(plafond), float(diviseur))
        for var, plafond, diviseur in re.findall(motif, bloc)
    ]


# --------------------------------------------------------------------------
# Barème : chaque profil doit être noté sur la même échelle
# --------------------------------------------------------------------------

@pytest.mark.parametrize("profil", ["FW", "MF_DEF", "MF_OFF", "DF"])
def test_bareme_total_egal_a_un(sql_vue, profil):
    """
    Un profil dont les poids totalisent 1.05 est noté sur 10.5 pendant que les
    autres sont notés sur 10 : il gagne 5% sans aucune raison métier. C'est
    exactement ce qui est arrivé aux MF_OFF, et personne ne l'a vu pendant des
    mois parce qu'aucun joueur réel n'atteignait le plafond partout.
    """
    blocs = extraire_blocs(sql_vue)
    poids = poids_du_bloc(blocs[profil])

    assert poids, f"Aucun poids extrait du bloc {profil} - la vue a peut-etre ete reformatee"

    total = round(sum(poids) + POIDS_BONUS_AGE, 4)
    assert total == pytest.approx(TOTAL_ATTENDU, abs=0.001), (
        f"{profil} : les poids totalisent {total} au lieu de {TOTAL_ATTENDU} "
        f"(composantes {sum(poids):.2f} + bonus age {POIDS_BONUS_AGE}). "
        f"Detail : {poids}"
    )


@pytest.mark.parametrize("profil", ["FW", "MF_DEF", "MF_OFF", "DF"])
def test_plafond_et_diviseur_identiques(sql_vue, profil):
    """
    Dans MIN(stat, X) / Y, X et Y doivent etre egaux : c'est ce qui ramene la
    composante a une proportion entre 0 et 1. Un ecart passe inapercu de SQL
    et fausse silencieusement le poids reel de la composante.
    """
    blocs = extraire_blocs(sql_vue)
    incoherents = [
        (var, plafond, diviseur)
        for var, plafond, diviseur in plafonds_du_bloc(blocs[profil])
        if plafond != diviseur
    ]

    assert not incoherents, (
        f"{profil} : plafond et diviseur different sur "
        + ", ".join(f"{v} (MIN(..., {p}) / {d})" for v, p, d in incoherents)
    )


# --------------------------------------------------------------------------
# Calibrage : les plafonds doivent rester atteignables
# --------------------------------------------------------------------------

FILTRES_PROFIL = {
    "FW": "position = 'FW'",
    "MF_DEF": "position = 'MF' AND mf_type = 'MF_DEF'",
    "MF_OFF": "position = 'MF' AND mf_type = 'MF_OFF'",
    "DF": "position = 'DF'",
}

# Variables dont le plafond est une borne metier absolue, pas une calibration
# empirique : min_pct est un pourcentage, ppm est borne par 3 points par match.
PLAFONDS_ABSOLUS = {"min_pct", "ppm"}


@pytest.mark.parametrize("profil", ["FW", "MF_DEF", "MF_OFF", "DF"])
def test_plafonds_atteignables(sql_vue, conn, profil):
    """
    Un plafond tres au-dessus du maximum observe bride la composante : le
    meilleur joueur du groupe n'en obtient qu'une fraction, et l'ecart entre
    un excellent et un moyen se trouve comprime.

    Cas historique : MIN(tacles_p90, 4.0) alors que le maximum reel chez les
    U20 des 5 championnats est 2.48. Le meilleur recuperateur du lot plafonnait
    a 62% d'une composante pesant 25% de son score.

    Ce test se recalibre tout seul d'une saison a l'autre, puisqu'il compare
    au maximum effectivement present en base.
    """
    blocs = extraire_blocs(sql_vue)
    filtre = FILTRES_PROFIL[profil]

    trop_hauts = []
    for var, plafond, _ in plafonds_du_bloc(blocs[profil]):
        if var in PLAFONDS_ABSOLUS:
            continue

        # La variable peut etre une expression (buts_p90 + passes_p90)
        ligne = conn.execute(
            f"SELECT MAX({var}) AS maxi FROM v_alterscore "
            f"WHERE {filtre} AND alterscore IS NOT NULL"
        ).fetchone()

        maxi = ligne["maxi"]
        if maxi is None or maxi == 0:
            continue

        if plafond > maxi * MARGE_PLAFOND:
            trop_hauts.append((var, plafond, round(maxi, 2)))

    assert not trop_hauts, (
        f"{profil} : plafonds inatteignables (max observe x{MARGE_PLAFOND}) sur "
        + ", ".join(
            f"{v} (plafond {p}, max reel {m})" for v, p, m in trop_hauts
        )
        + ". Recalibrer sur le p95 du groupe."
    )


# --------------------------------------------------------------------------
# Borne de sortie
# --------------------------------------------------------------------------

def test_score_brut_dans_les_bornes(conn):
    """
    Filet de securite en sortie : quels que soient les poids et les plafonds,
    un score brut doit rester dans [0, 10].
    """
    hors_bornes = conn.execute("""
        SELECT COUNT(*) AS n FROM v_alterscore
        WHERE score_brut IS NOT NULL AND (score_brut < 0 OR score_brut > 10)
    """).fetchone()["n"]

    assert hors_bornes == 0, f"{hors_bornes} joueurs ont un score_brut hors de [0, 10]"


def test_alterscore_dans_la_bande_des_coefficients(conn):
    """
    L'ALTERSCORE vaut score_brut x coef_fiab x coef_club_ajuste.

    coef_fiab est plafonne a 1.0, mais coef_club NE L'EST PAS : la table
    malus_clubs va de 0.70 a 1.15, c'est un malus pour les clubs surexposes ET
    un bonus pour les clubs modestes. Un joueur d'un petit club peut donc
    legitimement finir au-dessus de son score brut.

    La borne haute est donc score_brut x 1.15, et non score_brut. Au-dela, un
    coefficient est mal borne.
    """
    hors_bande = conn.execute("""
        SELECT COUNT(*) AS n FROM v_alterscore
        WHERE alterscore IS NOT NULL
          AND (alterscore > score_brut * 1.15 + 0.05 OR alterscore < 0)
    """).fetchone()["n"]

    assert hors_bande == 0, (
        f"{hors_bande} joueurs ont un ALTERSCORE hors de la bande "
        "[0, score_brut x 1.15] : un coefficient depasse ses bornes"
    )


def test_ajustement_club_ne_change_pas_le_sens_du_coefficient(conn):
    """
    L'ajustement du malus club par le temps de jeu rapproche le coefficient de
    1.0 proportionnellement aux minutes jouees. Effet de bord a surveiller :
    pour un club dont le coefficient est SUPERIEUR a 1.0 (petit club, donc
    bonus), le terme (1 - coef_club) est negatif, et l'ajustement rogne le
    bonus au lieu de reduire un malus.

    C'est coherent (le coefficient converge vers le neutre quand l'echantillon
    grandit) mais ce n'etait pas l'intention initiale. Ce test verifie au moins
    qu'un coefficient ne bascule jamais de l'autre cote de 1.0 : un club bonifie
    ne doit pas devenir penalise, ni l'inverse.
    """
    bascules = conn.execute("""
        SELECT COUNT(*) AS n FROM (
            SELECT coef_club,
                   coef_club + (1 - coef_club) * MIN(0.5, minutes / 3060.0) * 0.5 AS ajuste
            FROM v_alterscore
            WHERE alterscore IS NOT NULL
        )
        WHERE (coef_club > 1.0 AND ajuste < 1.0)
           OR (coef_club < 1.0 AND ajuste > 1.0)
    """).fetchone()["n"]

    assert bascules == 0, (
        f"{bascules} joueurs voient leur coefficient club basculer de l'autre "
        "cote de 1.0 apres ajustement par le temps de jeu"
    )
