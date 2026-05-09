# ALTER11 — Talent Radar 🔵

> Identifier les joueurs "alter" — différents, sous-cotés, à potentiel — dans les 5 grands championnats européens.

## 🎯 Concept

ALTER11 est un projet data football centré sur les jeunes joueurs U20 des 5 grandes ligues européennes.

L'**ALTERSCORE** est un indice composite qui évalue le potentiel d'un joueur selon :
- Sa régularité (% du temps de jeu disponible)
- Son impact offensif (/90 min)
- Son activité défensive (/90 min)
- Un bonus jeunesse (plus le joueur est jeune, plus le score est valorisé)

## 🛠️ Stack technique

- **Python** — nettoyage et préparation des données (pandas)
- **SQLite** — base de données relationnelle (3 tables)
- **SQL** — requêtes analytiques et calcul des KPI
- **HTML/CSS/JS** — vitrine web interactive

## 📁 Structure du projet
ALTER11/
├── data/
│   ├── raw/               # Dataset FBref 2025/2026
│   ├── clean/             # Données nettoyées
│   └── photos/            # Photos joueurs ALTER11
├── notebooks/
│   └── 01_cleaning.ipynb  # Nettoyage + insertion SQLite
├── sql/
│   ├── 01_schema.sql      # Création des tables
│   └── 02_kpi_u23.sql     # Requêtes analytiques
└── alter11.db             # Base SQLite

## 📊 Modèle de données

| Table | Description |
|-------|-------------|
| `dim_team` | Clubs des 5 grands championnats |
| `dim_player` | ~2500 joueurs toutes ligues |
| `fact_stats` | Stats saison 2025/2026 par joueur |

## 🏆 Ligues couvertes

| Ligue | Pays |
|-------|------|
| Ligue 1 | 🇫🇷 France |
| La Liga | 🇪🇸 Espagne |
| Serie A | 🇮🇹 Italie |
| Premier League | 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Angleterre |
| Bundesliga | 🇩🇪 Allemagne |

## 🔵 ALTERSCORE Top U20 — Saison 2025/2026

| Joueur | Âge | Poste | Club | ALTERSCORE |
|--------|-----|-------|------|------------|
| Endrick | 19 | FW | Lyon | 28.6 |
| Senny Mayulu | 19 | MF | PSG | 27.4 |
| Ayyoub Bouaddi | 18 | MF | Lille | 26.8 |
| Warren Zaïre-Emery | 20 | DF | PSG | 26.1 |
| Prosper Peter | 18 | FW | Angers | 25.3 |
| Désiré Doué | 20 | FW | PSG | 24.9 |

## 🚀 Lancer le projet

```bash
# Cloner le repo
git clone https://github.com/Janaud14/ALTER11.git
cd ALTER11

# Installer les dépendances
pip install pandas jupyter ipykernel

# Lancer le notebook de nettoyage
jupyter notebook notebooks/01_cleaning.ipynb
```

## 📡 Source des données

- [FBref](https://fbref.com) — statistiques saison 2025/2026
- Ligues : Ligue 1, La Liga, Serie A, Premier League, Bundesliga

---

*ALTER11 — Data Football · Scouting · Analyse de potentiel*