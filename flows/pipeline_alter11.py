"""
Orchestration du pipeline ALTER11 avec Prefect.

Le pipeline enchaîne scraping, enrichissement, création de la vue de scoring,
contrôles qualité et exports.

Les tests de qualité de données sont une étape BLOQUANTE : si la base est
corrompue, le flow s'arrête au lieu de propager des scores faux jusqu'à la
vitrine et au dashboard. C'est la raison d'être de cette orchestration —
les quatre bugs silencieux du projet ont tous été trouvés à la main, après
coup, alors qu'ils étaient déjà publiés.

Dépendances du DAG :

    scrape_saison
        |
        v
    enrichir_understat
        |
        v
    creer_vue  (source unique de la formule ALTERSCORE)
        |
        v
    controles_qualite  (BLOQUANT)
        |
        +---------------------------> exporter_power_bi
        |
        +--> recuperer_photos --> exporter_vitrine

Usage :
    pip install prefect pytest
    python flows/pipeline_alter11.py                 # exécution complète
    python flows/pipeline_alter11.py --skip-scraping # repart de la base existante

Pour l'interface web (facultatif, dans un autre terminal) :
    prefect server start
    # puis ouvrir http://127.0.0.1:4200
"""

import argparse
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from prefect import flow, task, get_run_logger

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "alter11.db"
VIEW_PATH = ROOT_DIR / "sql" / "00_view_alterscore.sql"
PYTHON = sys.executable


def lancer(commande: list[str], nom: str) -> str:
    """
    Exécute une commande et lève une exception si elle échoue.

    Prefect ne détecte un échec que si une exception remonte : un subprocess
    qui sort en code 1 sans lever passerait pour un succès.
    """
    logger = get_run_logger()
    logger.info("Lancement : %s", " ".join(commande))

    # Windows lance les subprocess en cp1252, qui ne gère pas les caractères
    # non-ASCII des print() des scripts. On force UTF-8 côté enfant.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    resultat = subprocess.run(
        commande,
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    if resultat.stdout:
        logger.info(resultat.stdout.strip())
    if resultat.stderr:
        logger.warning(resultat.stderr.strip())

    if resultat.returncode != 0:
        raise RuntimeError(f"{nom} a echoue (code {resultat.returncode})")

    return resultat.stdout


# --------------------------------------------------------------------------
# Étapes du pipeline
# --------------------------------------------------------------------------

@task(retries=2, retry_delay_seconds=60, task_run_name="Scraping saison FBref")
def scrape_saison() -> str:
    """
    Scraping FBref. 2 retries avec une minute d'attente : le site coupe
    régulièrement sur du rate limiting, et un échec réseau ne doit pas
    faire tomber tout le pipeline.
    """
    return lancer([PYTHON, "scripts/scrape_2024_2025.py"], "Scraping FBref")


@task(retries=2, retry_delay_seconds=60, task_run_name="Enrichissement xG-xA (Understat)")
def enrichir_understat() -> str:
    return lancer([PYTHON, "scripts/scrape_understat.py"], "Scraping Understat")


@task(task_run_name="Creation de la vue v_alterscore")
def creer_vue() -> str:
    """
    La vue v_alterscore porte toute la formule ALTERSCORE : c'est la source
    unique de vérité du projet, consommée par le top 10 SQL, l'export Power BI
    et l'export vitrine.

    Elle est recréée à chaque run. C'est idempotent (DROP VIEW IF EXISTS) et
    ça garantit que la base reflète toujours la version du fichier SQL
    versionné dans git, jamais une version figée en base lors d'un run passé.
    """
    logger = get_run_logger()

    if not DB_PATH.exists():
        raise RuntimeError(f"Base absente : {DB_PATH}")

    sql = VIEW_PATH.read_text(encoding="utf-8")
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(sql)

    logger.info("Vue v_alterscore recreee depuis %s", VIEW_PATH.name)
    return "ok"


@task(task_run_name="Controles qualite (pytest)")
def controles_qualite() -> str:
    """
    Étape bloquante. Si un test échoue, tout l'aval est annulé : pas de
    vitrine régénérée, pas de CSV Power BI exporté. Mieux vaut un pipeline
    rouge que des scores faux publiés en silence.
    """
    logger = get_run_logger()
    sortie = lancer([PYTHON, "-m", "pytest", "tests/", "-v", "--tb=short"], "Tests qualite")
    logger.info("Controles qualite passes - la base est saine, on peut exporter.")
    return sortie


@task(retries=1, retry_delay_seconds=30, task_run_name="Photos joueurs (Transfermarkt)")
def recuperer_photos() -> str:
    return lancer([PYTHON, "scripts/generate_cards.py"], "Recuperation photos")


@task(task_run_name="Export vitrine (players.json)")
def exporter_vitrine() -> str:
    return lancer([PYTHON, "scripts/export_vitrine_data.py"], "Export vitrine")


@task(task_run_name="Export dashboard Power BI (CSV)")
def exporter_power_bi() -> str:
    return lancer([PYTHON, "scripts/export_power_bi.py"], "Export Power BI")


# --------------------------------------------------------------------------
# Flow
# --------------------------------------------------------------------------

@flow(name="Pipeline ALTER11", log_prints=True)
def pipeline_alter11(skip_scraping: bool = False):
    """
    Orchestration complète : données brutes -> base enrichie -> vue de scoring
    -> contrôles -> livrables (vitrine web + dashboard Power BI).

    Args:
        skip_scraping: repart de la base existante sans rescraper les sources.
                       Utile pour retester la chaîne aval sans attendre.
    """
    logger = get_run_logger()

    if skip_scraping:
        logger.info("Scraping ignore - on repart de alter11.db tel quel.")
        amont = []
    else:
        saison = scrape_saison()
        amont = [enrichir_understat(wait_for=[saison])]

    # La vue doit exister avant les tests : plusieurs contrôles la supposent
    # présente, et les trois exports la consomment.
    vue = creer_vue(wait_for=amont)

    # Étape bloquante : rien ne s'exporte si la base n'est pas saine.
    qualite = controles_qualite(wait_for=[vue])

    # Le CSV Power BI ne dépend pas des photos : il part en parallèle.
    exporter_power_bi(wait_for=[qualite])

    # La vitrine attend les photos, sinon players.json référence des images
    # qui n'existent pas encore (d'où le double export dans la version manuelle).
    photos = recuperer_photos(wait_for=[qualite])
    exporter_vitrine(wait_for=[photos])

    logger.info("Pipeline termine - vitrine et dashboard a jour.")


if __name__ == "__main__":
    parseur = argparse.ArgumentParser(description="Pipeline ALTER11")
    parseur.add_argument(
        "--skip-scraping",
        action="store_true",
        help="repart de la base existante sans rescraper FBref/Understat",
    )
    args = parseur.parse_args()

    pipeline_alter11(skip_scraping=args.skip_scraping)
