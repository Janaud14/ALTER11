# ALTER11 — Talent Radar 🔵

> Data. Foot. Instinct. — Underrated Soccer Talent

## 🎯 Concept

ALTER11 est un projet data football centré sur les jeunes joueurs U20 des 5 grandes ligues européennes. L'objectif : identifier les profils sous-radar, sous-évalués, à potentiel — ceux que personne ne regarde encore.

L'**ALTERSCORE** est un indice composite sur 10 qui évalue le potentiel d'un joueur selon :

- Sa performance par poste (/90 min) — métriques différentes selon FW, MF, DF
- Sa régularité (% du temps de jeu disponible)
- Un bonus jeunesse (17→18→19→20 ans)
- Un coefficient d'exposition médiatique (malus grands clubs)
- Un coefficient de fiabilité (basé sur le volume de minutes)

## 🛠️ Stack technique

- **Python** — nettoyage, ACP, clustering (pandas, scikit-learn)
- **SQLite** — base de données relationnelle (3 tables + tables de référence)
- **SQL** — requêtes analytiques, CTEs, window functions, scoring composite
- **HTML/CSS/JS** — vitrine web interactive déployée sur GitHub Pages

## 📁 Structure du projet

```
ALTER11/
├── data/
│   ├── raw/                 # Dataset FBref 2025/2026
│   ├── clean/                # Données nettoyées
│   └── photos/                # Photos joueurs ALTER11
├── notebooks/
│   └── 01_analysis.ipynb    # Pipeline complet : nettoyage → ACP → clustering → scoring
├── sql/
│   ├── 01_schema.sql         # Création des tables
│   ├── 02_kpi_u20.sql        # Requêtes analytiques KPI
│   └── 03_alterscore.sql     # Calcul ALTERSCORE
├── scripts/
│   ├── find_similar_players.py   # Scoring de similarité entre joueurs (ACP + xG/xA)
│   ├── scrape_understat.py       # Enrichit fact_stats avec xG/xA (Understat)
│   ├── scrape_2024_2025.py       # Scraping saison 2024-25 (validation)
│   ├── validate_alterscore.py    # Validation prédictive de l'ALTERSCORE
│   ├── export_vitrine_data.py    # Génère players.json depuis alter11.db (vitrine)
│   └── generate_cards.py         # Récupère et détoure les photos joueurs (Transfermarkt)
├── run_alterscore.py         # Exécute 03_alterscore.sql et affiche le top par poste
├── alter11.db                # Base SQLite
├── players.json               # Données de la vitrine, généré depuis alter11.db
└── index.html                 # Vitrine web ALTER11 (charge players.json en fetch())
```

## 📊 Modèle de données

| Table         | Description                          |
| ------------- | ------------------------------------ |
| `dim_team`    | 96 clubs des 5 grands championnats   |
| `dim_player`  | 2627 joueurs toutes ligues           |
| `fact_stats`  | Stats saison 2025/2026 par joueur    |
| `malus_clubs` | Coefficients d'exposition médiatique |

## 🏆 Ligues couvertes

| Ligue          | Pays               |
| -------------- | ------------------ |
| Ligue 1        | 🇫🇷 France          |
| La Liga        | 🇪🇸 Espagne         |
| Serie A        | 🇮🇹 Italie          |
| Premier League | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Angleterre |
| Bundesliga     | 🇩🇪 Allemagne       |

## 🔵 ALTERSCORE — Top U20 par poste — Saison 2025/2026

**Attaquants**

| Joueur       | Âge | Club      | Ligue      | ALTERSCORE |
| ------------ | --- | --------- | ---------- | ---------- |
| Said El Mala | 19  | Köln      | Bundesliga | 5.8        |
| Carlos Espí  | 20  | Levante   | La Liga    | 4.7        |
| Lamine Yamal | 18  | Barcelona | La Liga    | 4.7        |

**Milieux**

| Joueur          | Âge | Club       | Ligue      | ALTERSCORE |
| --------------- | --- | ---------- | ---------- | ---------- |
| Johan Manzambi  | 20  | Freiburg   | Bundesliga | 4.6        |
| Jesus Rodríguez | 20  | Como       | Serie A    | 5.3        |
| Bazoumana Touré | 20  | Hoffenheim | Bundesliga | 5.2        |

**Défenseurs**

| Joueur           | Âge | Club          | Ligue      | ALTERSCORE |
| ---------------- | --- | ------------- | ---------- | ---------- |
| Noahkai Banks    | 19  | Augsburg      | Bundesliga | 4.2        |
| Abdoul Coulibaly | 18  | Werder Bremen | Bundesliga | 3.9        |
| Kacper Potulski  | 18  | Mainz 05      | Bundesliga | 3.8        |

## 🔍 Méthodologie ALTERSCORE

Le score est calculé différemment selon le poste :

- **FW** — tirs/90, buts/90, passes déc/90, régularité
- **MF offensif** — tirs/90, impact off/90, activité défensive/90
- **MF défensif** — tacles/90, interceptions/90, fautes subies/90
- **DF** — tacles/90, interceptions/90, centres/90, fautes subies/90

Tous les postes intègrent : bonus jeunesse + coefficient fiabilité + malus exposition club.

Le détail de la démarche complète (ACP, biplot, clustering par profil de jeu) est
documenté dans `notebooks/01_analysis.ipynb`.

## ⚠️ Limites connues

Ce projet est une V1 assumée comme telle. Les points suivants sont identifiés et
volontairement documentés plutôt que masqués :

- **Pas de validation prédictive.** L'ALTERSCORE n'a pas encore été confronté à une
  mesure de réussite future (transferts, temps de jeu en pro, sélections espoirs...).
  C'est un score de profil, pas encore un score prédictif validé.
- **Clustering non stabilisé.** Le K-Means est lancé avec une seed fixe (`random_state=42`)
  pour la reproductibilité, mais les clusters ne sont pas garantis stables si on relance
  avec d'autres seeds ou si le dataset évolue. Pas de test de robustesse (bootstrap,
  comparaison multi-seeds) à ce stade.
- **Pondérations choisies à la main.** Les poids de l'ALTERSCORE (ex : 25% tirs, 25% buts
  pour un attaquant) sont fixés par jugement métier, pas appris ou optimisés sur une
  cible externe.
- **8 variables dans l'ALTERSCORE, 10 dans le scoring de similarité.** Le score lui-même
  reste basé sur 8 métriques par 90 minutes, volontairement simple pour rester
  interprétable. Le scoring de similarité (`scripts/find_similar_players.py`), lui,
  intègre aussi le xG et le xA (voir point suivant) — mais ça reste un profil de jeu
  limité, sans dribbles ni duels aériens (voir ci-dessous).
- **Dribbles et duels aériens indisponibles — limite externe, pas un choix.** J'ai
  identifié un cas concret où le scoring de similarité confondait deux profils différents
  (un dribbleur créatif et un pivot physique, tous deux avec un taux de fautes subies
  similaire). La solution évidente — ajouter les dribbles réussis et les duels aériens
  gagnés — est bloquée : **FBref a perdu l'accès à ses données avancées fournies par Opta
  le 20 janvier 2026**, suite à une rupture de contrat avec Stats Perform
  ([source](https://www.sports-reference.com/blog/2026/01/fbref-stathead-data-update/)).
  J'ai vérifié les alternatives (Sofascore, WhoScored via `soccerdata`, dataset Kaggle) :
  aucune n'expose ces variables au niveau saison via les outils gratuits actuels.
- **xG/xA ajoutés à la similarité, pas encore à l'ALTERSCORE.** Contrairement à Opta,
  Understat calcule son propre modèle xG (indépendant, non affecté par la coupure), donc
  toujours accessible (`scripts/scrape_understat.py`). Je l'ai intégré au scoring de
  similarité, mais **pas** à l'ALTERSCORE lui-même : un xG élevé ne prouve pas qu'un
  joueur est meilleur (ça dépend beaucoup du système collectif de l'équipe), et
  comparer buts réels vs xG sur un petit échantillon de tirs (souvent <20 sur une
  saison pour un jeune) est trop bruité pour en tirer une vraie conclusion de
  précocité. Question ouverte, pas tranchée.
- **Malus club approximatif.** Le coefficient d'exposition médiatique est calculé par
  interpolation linéaire du PPM (points par match) de l'équipe entre le pire et le meilleur
  club des 5 championnats — 0.70 pour le club en tête, 1.15 pour le dernier. Les bornes
  elles-mêmes restent choisies à la main, pas optimisées.
- **Validation prédictive testée, résultat non significatif.** J'ai recalculé l'ALTERSCORE
  (sans malus club) sur les U20 de la saison 2024-2025, puis regardé s'il prédisait un gain
  de temps de jeu en 2025-2026. Résultat : aucune corrélation significative, ni globalement
  (r=-0.10, p=0.29) ni par poste (FW, MF, DF testés séparément). Deux limites à cette
  validation elle-même : biais de survie (18% des joueurs ont quitté les 5 championnats et
  sortent de l'échantillon), et échantillon réduit par poste (13 attaquants seulement). Le
  scoring de similarité entre joueurs (voir `scripts/find_similar_players.py`), en revanche,
  fonctionne comme prévu.

L'objectif de cette V1 est de poser une méthode explicite et discutable, pas de livrer
un score définitif.

## 🚀 Lancer le projet

```bash
git clone https://github.com/Janaud14/ALTER11.git
cd ALTER11
pip install pandas jupyter ipykernel scikit-learn matplotlib beautifulsoup4 rapidfuzz scipy soccerdata

# Pipeline complet (nettoyage, ACP, clustering, scoring) :
jupyter notebook notebooks/01_analysis.ipynb

# Ou juste le scoring final, si la base est déjà construite :
python run_alterscore.py

# Enrichir la base avec xG/xA (Understat), utilisé par le scoring de similarité :
python scripts/scrape_understat.py

# Trouver des joueurs similaires à un profil donné :
python scripts/find_similar_players.py "Lamine Yamal"

# Validation prédictive de l'ALTERSCORE (2024-25 vs 2025-26) :
python scripts/scrape_2024_2025.py
python scripts/validate_alterscore.py
```

## 🌐 Vitrine web

**[janaud14.github.io/ALTER11](https://janaud14.github.io/ALTER11)**

`index.html` ne contient aucune donnée codée en dur — il charge `players.json`
au démarrage, qui est généré à partir de la vraie base (mêmes calculs que
`sql/03_alterscore.sql`), pour tous les U20 éligibles. Pour régénérer la
vitrine après une mise à jour des stats ou des photos :

```bash
python scripts/export_vitrine_data.py   # génère players.json depuis alter11.db
python scripts/generate_cards.py        # récupère les photos manquantes (Transfermarkt)
python scripts/export_vitrine_data.py   # relance pour prendre en compte les nouvelles photos
```

Les photos sont récupérées sur Transfermarkt (photo de profil, pas la
vignette de recherche) puis détourées en local avec `rembg`
(modèle `u2net_human_seg`, spécialisé silhouettes humaines) — aucune clé API
n'est nécessaire.

## 📡 Source des données

- [FBref](https://fbref.com) — statistiques saison 2025/2026
- [Transfermarkt](https://transfermarkt.com) — position détaillée et valeur marchande
- Ligues : Ligue 1, La Liga, Serie A, Premier League, Bundesliga

---

*ALTER11 — Data. Foot. Instinct.*
