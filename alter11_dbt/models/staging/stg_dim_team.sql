SELECT team_id, team_name, competition
FROM {{ source('alter11', 'dim_team') }}