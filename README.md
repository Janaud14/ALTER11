# ALTER11 — Talent Radar 🔵

> Data. Foot. Instinct. — Underrated Soccer Talent

## 🎯 Concept

ALTER11 est un projet data football centré sur les jeunes joueurs U20 des 5 grandes ligues européennes. L'objectif : identifier les profils sous-radar, sous-évalués, à potentiel — ceux que personne ne regarde encore.

L'**ALTERSCORE** est un indice composite sur 10 qui évalue le potentiel d'un joueur selon :

- Sa performance par poste (/90 min) — métriques différentes selon FW, MF, DF
- Pour les attaquants : buts hors penalty, qualité des occasions (npxG), volume de tirs, précision de tir
- Sa régularité (% du temps de jeu disponible)
- Un bonus jeunesse (17→18→19→20 ans)
- Un coefficient d'exposition médiatique (malus/bonus club, basé sur le niveau réel de l'équipe)
- Un coefficient de fiabilité (basé sur le volume de minutes)

## 📊 Dashboard Power BI

![Dashboard ALTER11](docs/dashboard_powerbi.png)

Top 10 ALTERSCORE filtrable par poste, et analyse de finition
(buts réels vs buts attendus hors penaltys) sur 251 joueurs U20.
Généré depuis `scripts/export_power_bi.py`.

## 🛠️ Stack technique

- **Python** — nettoyage, scraping (FBref, Transfermarkt, Understat), ACP, clustering (pandas, scikit-learn, BeautifulSoup, rembg)
- **SQLite** — base de données relationnelle (3 tables + tables de référence)
- **SQL** — requêtes analytiques, CTEs, window functions, scoring composite
- **Power BI** — dashboard interactif (slicers, KPI, nuage de points avec ligne de symétrie)
- **HTML/CSS/JS** — vitrine web interactive déployée sur GitHub Pages, données chargées dynamiquement (aucune valeur codée en dur)

## 📁 Structure du projet

```
ALTER11/
├── data/
│   ├── raw/                  # Datasets FBref bruts (2024-25, 2025-26)
│   ├── clean/                 # Données nettoyées
│   └── photos/                 # Photos joueurs (détourées, via Transfermarkt)
├── notebooks/
│   └── 01_analysis.ipynb      # Pipeline complet : nettoyage → ACP → clustering → scoring
├── sql/
│   ├── 01_schema.sql          # Création des tables
│   ├── 02_kpi_u20.sql         # Requêtes analytiques KPI
│   └── 03_alterscore.sql      # Calcul ALTERSCORE (source de vérité de la formule)
├── scripts/
│   ├── find_similar_players.py       # Scoring de similarité entre joueurs (ACP)
│   ├── scrape_2024_2025.py           # Scraping saison 2024-25 (validation)
│   ├── validate_alterscore.py        # Validation prédictive de l'ALTERSCORE
│   ├── scrape_understat.py           # Enrichit fact_stats avec xG/xA/npxG (Understat)
│   ├── generate_cards.py             # Récupère et détoure les photos joueurs (Transfermarkt)
│   ├── export_power_bi.py            # Génère alter11_power_bi.csv (dashboard Power BI)
│   └── export_vitrine_data.py        # Génère players.json depuis alter11.db (vitrine)
├── run_alterscore.py           # Exécute 03_alterscore.sql et affiche le top par poste
├── alter11.db                  # Base SQLite
├── players.json                 # Données de la vitrine, généré depuis alter11.db
└── index.html                   # Vitrine web ALTER11 (charge players.json en fetch())
```

## 📊 Modèle de données

| Table         | Description                                          |
| ------------- | ----------------------------------------------------- |
| `dim_team`    | Clubs des 5 grands championnats                       |
| `dim_player`  | ~2600 joueurs toutes ligues                           |
| `fact_stats`  | Stats saison par joueur (FBref + Understat)           |
| `malus_clubs` | Coefficients d'ajustement club (0.70 à 1.15)          |

## 🏆 Ligues couvertes

| Ligue          | Pays               |
| -------------- | ------------------ |
| Ligue 1        | 🇫🇷 France          |
| La Liga        | 🇪🇸 Espagne         |
| Serie A        | 🇮🇹 Italie          |
| Premier League | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Angleterre |
| Bundesliga     | 🇩🇪 Allemagne       |

## 🔍 Méthodologie ALTERSCORE

Le score est calculé différemment selon le poste :

- **FW** — buts hors penalty/90 (25%), npxG/90 (7%), tirs/90 (8%), précision de tir (10%),
  passes déc/90 (15%), min% (15%), PPM équipe (5%)
- **MF offensif** — impact offensif/90, tirs/90, activité défensive/90, fautes subies/90,
  PPM équipe, min%
- **MF défensif** — tacles/90, interceptions/90, fautes subies/90, PPM équipe, min%
- **DF** — tacles/90, interceptions/90, centres/90, fautes subies/90, PPM équipe, min%

Tous les postes intègrent un bonus jeunesse dégressif et un coefficient de fiabilité basé
sur le volume de minutes jouées.

**Sur le choix np_goals + npxG plutôt que les buts bruts** : les penalties sont exclus pour
ne pas avantager un tireur attitré sur des situations qu'il ne crée pas lui-même. Le npxG
est ajouté en poids faible (7%, pas 25%) en complément du résultat réel — il corrèle à 0.83
avec les buts hors penalty (vérifié empiriquement), donc un poids égal aurait été redondant ;
un poids faible ajoute un signal de qualité sans dupliquer l'information.

Le détail complet de la démarche (ACP, biplot, clustering par profil de jeu) est documenté
dans `notebooks/01_analysis.ipynb`.

## 🎯 Scoring de similarité

`scripts/find_similar_players.py` trouve les joueurs au profil de jeu le plus proche d'un
joueur donné, via une distance dans l'espace ACP (8 variables, mêmes que l'ALTERSCORE hors
club/âge). Le xG/xA (Understat) est affiché à titre informatif à côté des résultats mais
**n'entre pas** dans le calcul de similarité — testé et écarté à deux reprises : d'abord en
valeur brute (corrélation 0.84 avec les stats déjà utilisées, redondant), puis en écart
buts-xG (trop bruité sur le faible volume de tirs d'un jeune sur une saison, ce qui donnait
des similarités moins cohérentes à l'usage).

```bash
python scripts/find_similar_players.py "Lamine Yamal"
```

## ⚠️ Limites connues

Ce projet est une V1 assumée comme telle. Les points suivants sont identifiés et
volontairement documentés plutôt que masqués :

- **Pas de validation prédictive convaincante — et le premier résultat était un piège.**
  J'ai recalculé l'ALTERSCORE (sans malus club) sur les U20 de 2024-2025, puis regardé
  s'il prédisait leur évolution de temps de jeu en 2025-2026. Premier résultat :
  corrélation *négative* et significative (Spearman r=-0.32, p<0.001, n=117) — les joueurs
  les mieux notés voyaient leur temps de jeu baisser. En creusant, c'est un artefact de
  régression vers la moyenne : la variable cible (Δ% temps de jeu) est fortement
  anti-corrélée au temps de jeu initial (r=-0.50), qui entre lui-même dans la formule du
  score via `min_pct`. Testé sur une cible non biaisée (% de temps de jeu absolu en
  2025-2026) : **r=-0.001, p=0.99** — aucune corrélation, ni positive ni négative.
  Conclusion assumée : l'ALTERSCORE décrit une performance passée, il ne prédit pas le
  temps de jeu futur — qui dépend largement de facteurs hors données (mercato, choix du
  coach, blessures). Limites de la validation elle-même : biais de survie (18% d'attrition)
  et échantillon réduit par poste (13 attaquants). Voir `scripts/validate_alterscore.py`.
- **Clustering non stabilisé.** Le K-Means est lancé avec une seed fixe pour la
  reproductibilité, mais les clusters ne sont pas garantis stables si on relance avec
  d'autres seeds. Pas de test de robustesse (multi-seeds, bootstrap) à ce stade.
- **Pondérations choisies à la main.** Les poids de l'ALTERSCORE sont fixés par jugement
  métier, pas appris ou optimisés sur une cible externe.
- **Variables limitées, et ce n'est pas (que) un choix.** FBref a perdu l'accès à ses
  données avancées fournies par Opta le 20 janvier 2026, suite à une rupture de contrat
  avec Stats Perform
  ([source](https://www.sports-reference.com/blog/2026/01/fbref-stathead-data-update/)).
  Les dribbles réussis et les duels aériens (qui auraient permis de mieux distinguer un
  profil dribbleur créatif d'un profil pivot physique — cas concret identifié sur le
  scoring de similarité) ne sont donc plus disponibles publiquement. Alternatives
  vérifiées et écartées : Sofascore et WhoScored via `soccerdata` ne donnent pas accès à
  ces stats au niveau saison via les outils gratuits actuels ; un dataset Kaggle annoncé
  plus complet s'est avéré être une version antérieure à la coupure.
- **xG/xA disponibles via Understat**, une source indépendante d'Opta donc non affectée
  par la coupure (`scripts/scrape_understat.py`). Le matching des noms entre les deux
  sources a nécessité plusieurs passes (normalisation des accents, score combiné
  nom+club, puis vérification manuelle ligne par ligne) pour atteindre 100% de couverture
  sur les joueurs à minutes suffisantes — un cas concret où le fuzzy matching seul créait
  des faux positifs (ex : deux joueurs différents nommés "Rayan" tous deux matchés sur un
  candidat "Rayan" générique via `partial_ratio`).
- **Malus club recalibré en cours de route.** La formule initiale ne descendait jamais
  sous 1.0 pour les clubs faibles (ils étaient "un peu moins pénalisés" plutôt que
  vraiment boostés), malgré une plage annoncée de 0.70 à 1.15. Corrigée en interpolation
  linéaire entre le meilleur et le pire club des 5 championnats, sur leur PPM réel — la
  plage complète est maintenant vraiment utilisée.
- **Trois bugs de données silencieux trouvés et corrigés en cours de projet**, qui
  faussaient les scores sans jamais générer d'erreur visible : ~22% des joueurs avaient un
  poste stocké au format `"MF,FW"` au lieu de `"FW"` (le score devenait `NULL` et le
  joueur disparaissait silencieusement du classement) ; ~20% avaient un âge stocké au
  format FBref `"19-290"` (années-jours) plutôt qu'un entier simple, ce qui pouvait fausser
  les comparaisons SQL du bonus âge. Les deux ont été détectés en creusant une incohérence
  précise (Lamine Yamal absent du classement malgré des stats qui auraient dû le classer
  très haut) plutôt que par un audit systématique — signe qu'un audit de qualité de
  données plus large serait utile avant d'aller plus loin. Enfin, la précision de tir était
  calculée en division entière SQLite (`shots_on_target / shots` sur deux INTEGER),
  renvoyant 0 pour 97% des joueurs et 1 pour les rares ayant cadré tous leurs tirs — ce qui
  annulait silencieusement une composante de 10% du score des attaquants. Cause racine : la
  formule était dupliquée dans trois fichiers et un seul n'avait pas la correction.

## 🚀 Lancer le projet

```bash
git clone https://github.com/Janaud14/ALTER11.git
cd ALTER11
pip install pandas jupyter ipykernel scikit-learn matplotlib beautifulsoup4 rapidfuzz scipy soccerdata rembg pillow

# Pipeline complet (nettoyage, ACP, clustering, scoring) :
jupyter notebook notebooks/01_analysis.ipynb

# Ou juste le scoring final, si la base est déjà construite :
python run_alterscore.py

# Enrichir la base avec xG/xA (Understat), utilisé par le scoring de similarité :
python scripts/scrape_understat.py

# Trouver des joueurs similaires à un profil donné :
python scripts/find_similar_players.py "Lamine Yamal"

# Exporter le CSV du dashboard Power BI :
python scripts/export_power_bi.py

# Validation prédictive de l'ALTERSCORE (2024-25 vs 2025-26) :
python scripts/scrape_2024_2025.py
python scripts/validate_alterscore.py
```

## 🌐 Vitrine web

**[janaud14.github.io/ALTER11](https://janaud14.github.io/ALTER11)**

`index.html` ne contient aucune donnée codée en dur — il charge `players.json` au
démarrage, généré à partir de la vraie base (mêmes calculs que `sql/03_alterscore.sql`),
pour tous les U20 éligibles. Chaque carte affiche 6 statistiques spécifiques au poste du
joueur, avec un glossaire en info-bulle et un bouton "Comment ça marche" qui explique la
méthodologie en langage clair — pensé pour qu'un visiteur non-initié comprenne les scores
sans avoir à lire ce README.

Pour régénérer la vitrine après une mise à jour des stats ou des photos :

```bash
python scripts/export_vitrine_data.py   # génère players.json depuis alter11.db
python scripts/generate_cards.py        # récupère les photos manquantes (Transfermarkt)
python scripts/export_vitrine_data.py   # relance pour prendre en compte les nouvelles photos
```

Les photos sont récupérées sur Transfermarkt (photo de profil haute résolution, pas la
vignette de recherche) puis détourées en local avec `rembg` (modèle `u2net_human_seg`,
spécialisé silhouettes humaines, avec alpha matting pour préserver les mèches de cheveux)
— aucune clé API nécessaire.

## 📡 Source des données

- [FBref](https://fbref.com) — statistiques saison, standard/tirs/temps de jeu/discipline
- [Transfermarkt](https://transfermarkt.com) — position détaillée, valeur marchande, photos
- [Understat](https://understat.com) — xG, xA, npxG (modèle indépendant d'Opta)

---

*ALTER11 — Data. Foot. Instinct.*
