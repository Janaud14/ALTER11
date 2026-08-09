-- Staging : dimension joueur nettoyee.
-- Cast de l'age (stocke en TEXT, parfois au format FBref "19-290").

SELECT
    player_id,
    player_name,
    position,
    nation,
    birth_year,
    CAST(SPLIT_PART(CAST(age AS TEXT), '-', 1) AS INTEGER) AS age,
    team_id,
    position_detail,
    market_value
FROM {{ source('alter11', 'dim_player') }}