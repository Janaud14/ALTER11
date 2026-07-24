-- ============================================================
-- v_alterscore — SOURCE UNIQUE DE VÉRITÉ DE LA FORMULE
-- ============================================================
-- Cette vue est le seul endroit du projet où la formule de l'ALTERSCORE
-- est définie. Tous les consommateurs (top 10 SQL, export Power BI, export
-- vitrine) lisent cette vue au lieu de recopier le calcul.
--
-- Historique : la formule a longtemps été dupliquée dans quatre fichiers.
-- Un correctif de division entière appliqué à trois d'entre eux seulement a
-- fait diverger le classement du dashboard de celui de la vitrine pendant
-- plusieurs semaines, sans jamais lever d'erreur. D'où cette vue.
--
-- Règle : ne JAMAIS recopier le contenu de cette vue ailleurs. Si un
-- consommateur a besoin d'une variante, il filtre ou trie la vue — il ne
-- réécrit pas le calcul.
--
-- Périmètre volontairement large : tous les U20 non-gardiens, sans filtre de
-- minutes. Les seuils par poste (FW 300 / MF 400 / DF 500) mettent score_brut
-- à NULL sous le seuil, mais la ligne reste présente. C'est aux consommateurs
-- de filtrer selon leur besoin :
--   - top 10 SQL      : WHERE alterscore IS NOT NULL
--   - export vitrine  : WHERE alterscore IS NOT NULL
--   - export Power BI : WHERE minutes >= 200 (garde les joueurs sans score
--                       pour les graphiques descriptifs type nuage xG)
--
-- Application :
--   sqlite3 alter11.db < sql/00_view_alterscore.sql
-- ============================================================

DROP VIEW IF EXISTS v_alterscore;

CREATE VIEW v_alterscore AS
WITH base AS (
    SELECT
        p.player_id,
        p.player_name,
        p.position,
        t.team_name,
        t.competition,

        -- L'âge est stocké en TEXT et peut arriver au format FBref
        -- "années-jours" ("19-290"). CAST tronque au premier entier lisible,
        -- ce qui donne bien 19. Normalisé ici une fois pour toutes plutôt que
        -- dans chaque script consommateur.
        CAST(p.age AS INTEGER) AS age,

        f.minutes,
        f.nineties,
        f.matches_played,

        ROUND(f.minutes * 100.0 / NULLIF(f.matches_played * 90.0, 0), 1) AS min_pct,
        ROUND(f.goals / NULLIF(f.nineties, 0), 2)              AS buts_p90,
        ROUND(f.assists / NULLIF(f.nineties, 0), 2)            AS passes_p90,
        ROUND(f.shots / NULLIF(f.nineties, 0), 2)              AS tirs_p90,
        ROUND(f.tackles_won / NULLIF(f.nineties, 0), 2)        AS tacles_p90,
        ROUND(f.interceptions / NULLIF(f.nineties, 0), 2)      AS int_p90,
        ROUND(f.fouls_drawn / NULLIF(f.nineties, 0), 2)        AS fd_p90,
        ROUND(f.fouls_committed / NULLIF(f.nineties, 0), 2)    AS fls_p90,
        ROUND(f.crosses / NULLIF(f.nineties, 0), 2)            AS crs_p90,
        ROUND(f.points_per_match, 2)                           AS ppm,

        -- xG/xA Understat, conservés bruts pour les visualisations
        ROUND(f.xg / NULLIF(f.nineties, 0), 2)                 AS xg_p90,
        ROUND(f.xa / NULLIF(f.nineties, 0), 2)                 AS xa_p90,

        COALESCE(m.malus, 1.0)                                 AS coef_club,

        -- Variables Understat (np_goals, npxg). COALESCE à une valeur de repli
        -- plutôt que NULL : sinon toute la formule FW deviendrait NULL pour un
        -- joueur non matché et il disparaîtrait silencieusement du classement.
        ROUND(COALESCE(f.np_goals, f.goals) / NULLIF(f.nineties, 0), 2) AS np_goals_p90,
        ROUND(COALESCE(f.npxg, 0) / NULLIF(f.nineties, 0), 2)           AS npxg_p90,

        -- Précision de tir. Le * 1.0 est OBLIGATOIRE : shots_on_target et
        -- shots sont deux INTEGER, et SQLite ferait une division entière
        -- renvoyant 0 dès que le numérateur est plus petit que le dénominateur.
        -- C'est exactement le bug qui a motivé cette vue.
        ROUND(COALESCE(f.shots_on_target, 0) * 1.0 / NULLIF(f.shots, 0), 3) AS precision_tir,

        -- Bonus âge dégressif : plus le joueur est jeune, plus le bonus est fort
        CASE
            WHEN CAST(p.age AS INTEGER) <= 17 THEN 2.0
            WHEN CAST(p.age AS INTEGER) <= 18 THEN 1.7
            WHEN CAST(p.age AS INTEGER) <= 19 THEN 1.4
            WHEN CAST(p.age AS INTEGER) =  20 THEN 1.1
            ELSE 0.8
        END AS bonus_age,

        -- Coef de fiabilité : monte avec le volume de minutes (plafond à 1.0).
		-- Le seuil de pleine confiance descend avec l'âge (600 min à 17 ans,
		-- 1500 à 20+) pour ne pas pénaliser les très jeunes, qui jouent peu par
		-- construction — c'est précisément la cible du projet.
        MIN(1.0, 0.5 + (f.minutes /
		CASE
			WHEN CAST(p.age AS INTEGER) <= 17 THEN 1200.0
			WHEN CAST(p.age AS INTEGER) <= 18 THEN 1800.0
			WHEN CAST(p.age AS INTEGER) <= 19 THEN 2400.0
			ELSE 3000.0
		END)) AS coef_fiab,

        -- Split milieux offensifs / défensifs : ratio activité défensive vs offensive
        CASE
            WHEN (f.tackles_won + f.interceptions) / NULLIF(f.nineties, 0)
               > (f.goals + f.assists) / NULLIF(f.nineties, 0) * 3
            THEN 'MF_DEF'
            ELSE 'MF_OFF'
        END AS mf_type

    FROM fact_stats f
    JOIN dim_player p ON f.player_id = p.player_id
    JOIN dim_team t   ON p.team_id = t.team_id
    LEFT JOIN malus_clubs m ON t.team_name = m.team_name
    WHERE CAST(p.age AS INTEGER) <= 20
      AND p.position != 'GK'
),
scored AS (
    SELECT *,
        CASE position

            -- ATTAQUANT (min 300 min)
            -- Cluster tir/finition (50% au total, redécoupé en 4) :
            --   np_goals 25% (sans biais penalty)
            --   npxg 7% (poids faible car corrélé à 0.83 avec np_goals)
            --   tirs 8% (volume, réduit car la précision prend le relais)
            --   précision de tir 10%
            WHEN 'FW' THEN
                CASE WHEN minutes < 300 THEN NULL ELSE
                ROUND(
                    (MIN(np_goals_p90, 0.6) / 0.6 * 10 * 0.25)
                  + (MIN(npxg_p90, 0.7) / 0.7 * 10 * 0.07)
                  + (MIN(tirs_p90, 4.0) / 4.0 * 10 * 0.08)
                  + (COALESCE(precision_tir, 0.35) * 10 * 0.10)
                  + (MIN(passes_p90, 0.3) / 0.3 * 10 * 0.15)
                  + (MIN(min_pct, 100) / 100.0 * 10 * 0.15)
                  + (MIN(ppm, 3.0) / 3.0 * 10 * 0.05)
                  + (bonus_age * 0.15 * 10 / 2.0)
                , 1) END

            -- MILIEU (min 400 min), formule différenciée selon le profil
			-- Plafonds calibres sur le p95 des U20 2025-2026 (max reel : 2.48 tacles/90,
			-- 2.13 interceptions/90). Les valeurs precedentes (4.0 et 3.0) etaient
			-- inatteignables et bridaient structurellement les MF_DEF.
            WHEN 'MF' THEN
                CASE WHEN minutes < 400 THEN NULL ELSE
                ROUND(
                    CASE mf_type
                    WHEN 'MF_DEF' THEN
                        (MIN(tacles_p90, 2.2) / 2.2 * 10 * 0.25)
                      + (MIN(int_p90, 1.7) / 1.7 * 10 * 0.25)
                      + (MIN(fd_p90, 3.0) / 3.0 * 10 * 0.10)
                      + (MIN(fls_p90, 2.3) / 2.3 * 10 * 0.05)
                      + (MIN(ppm, 3.0) / 3.0 * 10 * 0.10)
                      + (MIN(min_pct, 100) / 100.0 * 10 * 0.10)
                      + (bonus_age * 0.15 * 10 / 2.0)
                    ELSE
						(MIN(buts_p90 + passes_p90, 1.0) / 1.0 * 10 * 0.25)
                      + (MIN(tirs_p90, 3.0) / 3.0 * 10 * 0.20)
                      + (MIN(fd_p90, 2.5) / 2.5 * 10 * 0.10)
                      + (MIN(ppm, 3.0) / 3.0 * 10 * 0.05)
                      + (MIN(min_pct, 100) / 100.0 * 10 * 0.10)
                      + (bonus_age * 0.15 * 10 / 2.0)
                    END
                , 1) END

            -- DÉFENSEUR (min 500 min)
            WHEN 'DF' THEN
                CASE WHEN minutes < 500 THEN NULL ELSE
                ROUND(
                    (MIN(tacles_p90, 2.3) / 2.3 * 10 * 0.22)
                  + (MIN(int_p90, 1.8) / 1.8 * 10 * 0.20)
                  + (MIN(fd_p90, 1.3) / 1.3 * 10 * 0.08)
                  + (MIN(fls_p90, 2.0) / 2.0 * 10 * 0.05)
                  + (MIN(crs_p90, 3.0) / 3.0 * 10 * 0.10)
                  + (MIN(ppm, 3.0) / 3.0 * 10 * 0.10)
                  + (MIN(min_pct, 100) / 100.0 * 10 * 0.10)
                  + (bonus_age * 0.15 * 10 / 2.0)
                , 1) END

        END AS score_brut
    FROM base
)
SELECT *,
    ROUND(score_brut * coef_fiab * (coef_club + (1 - coef_club) * MIN(0.5, minutes / 3060.0) * 0.5), 1) AS alterscore
FROM scored;
