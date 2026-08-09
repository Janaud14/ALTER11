{{ config(materialized='table') }}

WITH scored AS (
    SELECT *,
        CASE position

            WHEN 'FW' THEN
                CASE WHEN minutes < 300 THEN NULL ELSE
                ROUND((
                    (LEAST(np_goals_p90, 0.6) / 0.6 * 10 * 0.25)
                  + (LEAST(npxg_p90, 0.7) / 0.7 * 10 * 0.07)
                  + (LEAST(tirs_p90, 4.0) / 4.0 * 10 * 0.08)
                  + (COALESCE(precision_tir, 0.35) * 10 * 0.10)
                  + (LEAST(passes_p90, 0.3) / 0.3 * 10 * 0.15)
                  + (LEAST(min_pct, 100) / 100.0 * 10 * 0.15)
                  + (LEAST(ppm, 3.0) / 3.0 * 10 * 0.05)
                  + (bonus_age * 0.15 * 10 / 2.0)
                )::numeric, 1) END

            WHEN 'MF' THEN
                CASE WHEN minutes < 400 THEN NULL ELSE
                ROUND((
                    CASE mf_type
                    WHEN 'MF_DEF' THEN
                        (LEAST(tacles_p90, 2.2) / 2.2 * 10 * 0.25)
                      + (LEAST(int_p90, 1.7) / 1.7 * 10 * 0.25)
                      + (LEAST(fd_p90, 3.0) / 3.0 * 10 * 0.10)
                      + (LEAST(fls_p90, 2.3) / 2.3 * 10 * 0.05)
                      + (LEAST(ppm, 3.0) / 3.0 * 10 * 0.10)
                      + (LEAST(min_pct, 100) / 100.0 * 10 * 0.10)
                      + (bonus_age * 0.15 * 10 / 2.0)
                    ELSE
                        (LEAST(buts_p90 + passes_p90, 1.0) / 1.0 * 10 * 0.35)
                      + (LEAST(tirs_p90, 3.0) / 3.0 * 10 * 0.25)
                      + (LEAST(fd_p90, 2.5) / 2.5 * 10 * 0.10)
                      + (LEAST(ppm, 3.0) / 3.0 * 10 * 0.05)
                      + (LEAST(min_pct, 100) / 100.0 * 10 * 0.10)
                      + (bonus_age * 0.15 * 10 / 2.0)
                    END
                )::numeric, 1) END

            WHEN 'DF' THEN
                CASE WHEN minutes < 500 THEN NULL ELSE
                ROUND((
                    (LEAST(tacles_p90, 2.3) / 2.3 * 10 * 0.22)
                  + (LEAST(int_p90, 1.8) / 1.8 * 10 * 0.20)
                  + (LEAST(fd_p90, 1.3) / 1.3 * 10 * 0.08)
                  + (LEAST(fls_p90, 2.0) / 2.0 * 10 * 0.05)
                  + (LEAST(crs_p90, 3.0) / 3.0 * 10 * 0.10)
                  + (LEAST(ppm, 3.0) / 3.0 * 10 * 0.10)
                  + (LEAST(min_pct, 100) / 100.0 * 10 * 0.10)
                  + (bonus_age * 0.15 * 10 / 2.0)
                )::numeric, 1) END

        END AS score_brut
    FROM {{ ref('int_player_metrics') }}
)

SELECT *,
    ROUND(
        (score_brut * coef_fiab
         * (coef_club + (1 - coef_club) * LEAST(0.5, minutes / 3060.0) * 0.5)
        )::numeric, 1
    ) AS alterscore
FROM scored