-- Intermediate : assemble les tables staging et calcule les metriques.
-- Postgres : cast ::numeric avant ROUND, et np_goals stocke en text -> cast securise.

WITH joueurs AS (
    SELECT
        p.player_id,
        p.player_name,
        p.position,
        p.age,
        t.team_name,
        t.competition,
        f.minutes,
        f.nineties,
        f.matches_played,

        ROUND((f.minutes * 100.0 / NULLIF(f.matches_played * 90.0, 0))::numeric, 1) AS min_pct,
        ROUND((f.goals / NULLIF(f.nineties, 0))::numeric, 2)              AS buts_p90,
        ROUND((f.assists / NULLIF(f.nineties, 0))::numeric, 2)            AS passes_p90,
        ROUND((f.shots / NULLIF(f.nineties, 0))::numeric, 2)              AS tirs_p90,
        ROUND((f.tackles_won / NULLIF(f.nineties, 0))::numeric, 2)        AS tacles_p90,
        ROUND((f.interceptions / NULLIF(f.nineties, 0))::numeric, 2)      AS int_p90,
        ROUND((f.fouls_drawn / NULLIF(f.nineties, 0))::numeric, 2)        AS fd_p90,
        ROUND((f.fouls_committed / NULLIF(f.nineties, 0))::numeric, 2)    AS fls_p90,
        ROUND((f.crosses / NULLIF(f.nineties, 0))::numeric, 2)            AS crs_p90,
        ROUND(f.points_per_match::numeric, 2)                             AS ppm,
        ROUND((f.xg / NULLIF(f.nineties, 0))::numeric, 2)                 AS xg_p90,
        ROUND((f.xa / NULLIF(f.nineties, 0))::numeric, 2)                 AS xa_p90,

        COALESCE(m.malus, 1.0)                                            AS coef_club,

        ROUND((COALESCE(NULLIF(f.np_goals, '')::numeric, f.goals) / NULLIF(f.nineties, 0))::numeric, 2) AS np_goals_p90,
        ROUND((COALESCE(NULLIF(f.npxg::text, '')::numeric, 0) / NULLIF(f.nineties, 0))::numeric, 2)      AS npxg_p90,
        ROUND((COALESCE(f.shots_on_target, 0) * 1.0 / NULLIF(f.shots, 0))::numeric, 3) AS precision_tir,

        CASE
            WHEN p.age <= 17 THEN 2.0
            WHEN p.age <= 18 THEN 1.7
            WHEN p.age <= 19 THEN 1.4
            WHEN p.age =  20 THEN 1.1
            ELSE 0.8
        END AS bonus_age,

        LEAST(1.0, 0.5 + (f.minutes /
            CASE
                WHEN p.age <= 17 THEN 1200.0
                WHEN p.age <= 18 THEN 1800.0
                WHEN p.age <= 19 THEN 2400.0
                ELSE 3000.0
            END)) AS coef_fiab,

        CASE WHEN p.position = 'MF' THEN
            CASE
                WHEN (f.tackles_won + f.interceptions) / NULLIF(f.nineties, 0)
                   > (f.goals + f.assists) / NULLIF(f.nineties, 0) * 3
                THEN 'MF_DEF'
                ELSE 'MF_OFF'
            END
        ELSE NULL END AS mf_type

    FROM {{ ref('stg_fact_stats') }} f
    JOIN {{ ref('stg_dim_player') }} p ON f.player_id = p.player_id
    JOIN {{ ref('stg_dim_team') }} t   ON p.team_id = t.team_id
    LEFT JOIN {{ ref('stg_malus_clubs') }} m ON t.team_name = m.team_name
    WHERE p.age <= 20
      AND p.position != 'GK'
)

SELECT * FROM joueurs