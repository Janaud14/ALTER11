SELECT team_name, malus, points_per_match
FROM {{ source('alter11', 'malus_clubs') }}