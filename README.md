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
├── run_alterscore.py         # Exécute 03_alterscore.sql et affiche le top par poste
├── alter11.db                # Base SQLite
└── index.html                 # Vitrine web ALTER11
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
- **8 variables seulement.** Le profil d'un joueur est réduit à 8 métriques par 90 minutes.
  C'est volontairement simple pour rester interprétable, mais ça laisse de côté beaucoup
  de dimensions du jeu (positionnement, passes progressives, duels aériens, etc.).
- **Malus club approximatif.** Le coefficient d'exposition médiatique est basé sur le
  nombre de points par match de l'équipe, avec des bornes (0.70–1.15) choisies à la main.

L'objectif de cette V1 est de poser une méthode explicite et discutable, pas de livrer
un score définitif.

## 🚀 Lancer le projet

```bash
git clone https://github.com/Janaud14/ALTER11.git
cd ALTER11
pip install pandas jupyter ipykernel scikit-learn matplotlib beautifulsoup4 rapidfuzz

# Pipeline complet (nettoyage, ACP, clustering, scoring) :
jupyter notebook notebooks/01_analysis.ipynb

# Ou juste le scoring final, si la base est déjà construite :
python run_alterscore.py
```

## 🌐 Vitrine web

**[janaud14.github.io/ALTER11](https://janaud14.github.io/ALTER11)**

## 📡 Source des données

- [FBref](https://fbref.com) — statistiques saison 2025/2026
- [Transfermarkt](https://transfermarkt.com) — position détaillée et valeur marchande
- Ligues : Ligue 1, La Liga, Serie A, Premier League, Bundesliga

---

*ALTER11 — Data. Foot. Instinct.*
