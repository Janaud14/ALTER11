-- ============================================================
-- ALTERSCORE — Top 10 U20 par poste (5 grands championnats)
-- ============================================================
-- La formule n'est PAS définie ici : elle vit dans la vue v_alterscore
-- (sql/00_view_alterscore.sql), qui est la source unique de vérité du projet.
-- Ce fichier ne fait que consommer cette vue pour l'affichage.
--
-- Prérequis : la vue doit exister.
--   sqlite3 alter11.db < sql/00_view_alterscore.sql
--
-- Seuils de minutes par poste (FW 300 / MF 400 / DF 500) : appliqués dans la
-- vue, qui met alterscore à NULL sous le seuil.
-- ============================================================

SELECT rang, player_name, age, position, mf_type,
       team_name, competition, minutes, alterscore
FROM (
    SELECT
        ROW_NUMBER() OVER (PARTITION BY position ORDER BY alterscore DESC) AS rang,
        *
    FROM v_alterscore
    WHERE alterscore IS NOT NULL
)
WHERE rang <= 10
ORDER BY position, rang;
