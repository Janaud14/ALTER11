-- Staging : nettoyage de la table brute fact_stats.
-- Role : caster proprement, exposer des colonnes fiables aux couches suivantes.

SELECT
    player_id,
    minutes,
    nineties,
    matches_played,
    goals,
    assists,
    shots,
    shots_on_target,
    tackles_won,
    interceptions,
    fouls_committed,
    fouls_drawn,
    crosses,
    points_per_match,
    xg,
    xa,
    npxg,
    np_goals
FROM {{ source('alter11', 'fact_stats') }}