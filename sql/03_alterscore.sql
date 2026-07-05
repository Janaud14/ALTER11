-- ============================================================
-- ALTERSCORE — Scoring des U20 par poste (5 grands championnats)
-- ============================================================
-- Logique :
--   1. base    : agrégation des stats par 90 minutes + coefficients
--                (bonus âge, coef de fiabilité, malus club)
--   2. scored  : calcul du score brut, formule différenciée par poste
--                (FW / MF avec split défensif-offensif / DF)
--   3. final   : score brut pondéré par la fiabilité et le coef club
-- Sortie : top 10 U20 par poste, classés par ALTERSCORE.
--
-- Seuils de minutes minimum par poste (fiabilité statistique) :
--   FW >= 300 min | MF >= 400 min | DF >= 500 min
-- ============================================================

WITH base AS (
    SELECT
        p.player_name, p.age, p.position, t.team_name, t.competition,
        f.minutes, f.nineties, f.matches_played,
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
        COALESCE(m.malus, 1.0)                                 AS coef_club,

        -- Bonus âge dégressif : plus le joueur est jeune, plus le bonus est fort
        CASE
            WHEN p.age <= 17 THEN 2.0
            WHEN p.age <= 18 THEN 1.7
            WHEN p.age <= 19 THEN 1.4
            WHEN p.age = 20  THEN 1.1
            ELSE 0.8
        END AS bonus_age,

        -- Coef de fiabilité : monte avec le volume de minutes jouées (plafond à 1.0)
        MIN(1.0, 0.5 + (f.minutes / 3000.0)) AS coef_fiab,

        -- Split milieux offensifs / défensifs : ratio activité défensive vs offensive
        CASE
            WHEN (f.tackles_won + f.interceptions) / NULLIF(f.nineties, 0)
               > (f.goals + f.assists) / NULLIF(f.nineties, 0) * 3
            THEN 'MF_DEF'
            ELSE 'MF_OFF'
        END AS mf_type

    FROM fact_stats f
    JOIN dim_player p ON f.player_id = p.player_id
    JOIN dim_team t ON p.team_id = t.team_id
    LEFT JOIN malus_clubs m ON t.team_name = m.team_name
    WHERE p.age <= 20
      AND p.position != 'GK'
),
scored AS (
    SELECT *,
        CASE position

            -- ATTAQUANT (min 300 min)
            WHEN 'FW' THEN
                CASE WHEN minutes < 300 THEN NULL ELSE
                ROUND(
                    (MIN(tirs_p90, 5.0) / 5.0 * 10 * 0.25)
                  + (MIN(buts_p90, 1.0) / 1.0 * 10 * 0.25)
                  + (MIN(passes_p90, 0.8) / 0.8 * 10 * 0.15)
                  + (MIN(min_pct, 100) / 100.0 * 10 * 0.15)
                  + (MIN(ppm, 3.0) / 3.0 * 10 * 0.05)
                  + (bonus_age * 0.15 * 10 / 2.0)
                , 1) END

            -- MILIEU (min 400 min), formule différenciée selon le profil
            WHEN 'MF' THEN
                CASE WHEN minutes < 400 THEN NULL ELSE
                ROUND(
                    CASE mf_type
                    WHEN 'MF_DEF' THEN
                        (MIN(tacles_p90, 4.0) / 4.0 * 10 * 0.25)
                      + (MIN(int_p90, 3.0) / 3.0 * 10 * 0.25)
                      + (MIN(fd_p90, 3.0) / 3.0 * 10 * 0.10)
                      + (MIN(fls_p90, 4.0) / 4.0 * 10 * 0.05)
                      + (MIN(ppm, 3.0) / 3.0 * 10 * 0.10)
                      + (MIN(min_pct, 100) / 100.0 * 10 * 0.10)
                      + (bonus_age * 0.15 * 10 / 2.0)
                    ELSE
                        (MIN(tacles_p90, 4.0) / 4.0 * 10 * 0.10)
                      + (MIN(int_p90, 3.0) / 3.0 * 10 * 0.10)
                      + (MIN(buts_p90 + passes_p90, 1.0) / 1.0 * 10 * 0.25)
                      + (MIN(tirs_p90, 3.0) / 3.0 * 10 * 0.20)
                      + (MIN(fd_p90, 3.0) / 3.0 * 10 * 0.10)
                      + (MIN(ppm, 3.0) / 3.0 * 10 * 0.05)
                      + (MIN(min_pct, 100) / 100.0 * 10 * 0.10)
                      + (bonus_age * 0.15 * 10 / 2.0)
                    END
                , 1) END

            -- DÉFENSEUR (min 500 min)
            WHEN 'DF' THEN
                CASE WHEN minutes < 500 THEN NULL ELSE
                ROUND(
                    (MIN(tacles_p90, 4.0) / 4.0 * 10 * 0.22)
                  + (MIN(int_p90, 3.0) / 3.0 * 10 * 0.20)
                  + (MIN(fd_p90, 3.0) / 3.0 * 10 * 0.08)
                  + (MIN(fls_p90, 4.0) / 4.0 * 10 * 0.05)
                  + (MIN(crs_p90, 3.0) / 3.0 * 10 * 0.10)
                  + (MIN(ppm, 3.0) / 3.0 * 10 * 0.10)
                  + (MIN(min_pct, 100) / 100.0 * 10 * 0.10)
                  + (bonus_age * 0.15 * 10 / 2.0)
                , 1) END

        END AS score_brut
    FROM base
),
final AS (
    SELECT *,
        ROUND(score_brut * coef_fiab * coef_club, 1) AS alterscore
    FROM scored
    WHERE score_brut IS NOT NULL
)

-- Top 10 par poste, classés par ALTERSCORE décroissant
SELECT rang, player_name, age, position, mf_type, team_name, competition, minutes, alterscore
FROM (
    SELECT
        ROW_NUMBER() OVER (PARTITION BY position ORDER BY alterscore DESC) AS rang,
        *
    FROM final
)
WHERE rang <= 10
ORDER BY position, rang;
