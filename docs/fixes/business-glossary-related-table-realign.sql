/* ---------------------------------------------------------------------------
 * Realign Business_Glossary.related_table to deployed database names.
 *
 * Symptom: The browser's Glossary tab is empty for every entity because the
 * curated rows reference *logical* module names (CallCentre_Domain.Call_*),
 * but the deployed databases are physical (CallCentre_DOM_STD_T.*). SQL
 * needs exact matches, so the join from entity_metadata -> related_table
 * never matches.
 *
 * Fix: Rewrite the database prefix on related_table to the actual deployed
 * database. Run against your CallCentre product. Mirror the same pattern
 * for any other product with the same drift.
 *
 * Safe to run multiple times — only updates rows that still hold the legacy
 * "<Product>_<Module>." prefix. Always SELECT to preview before UPDATE.
 *
 * Tip: Wrap each UPDATE in a transaction and verify the row count matches
 * the SELECT count before committing.
 * ------------------------------------------------------------------------ */

DATABASE CallCentre_MEM_STD_T;

/* --- 0. Preview rows that will change --------------------------------- */
SELECT
    related_table
  , COUNT(*) AS rows_affected
FROM CallCentre_MEM_STD_T.Business_Glossary
WHERE related_table LIKE 'CallCentre\_Domain.%'      ESCAPE '\'
   OR related_table LIKE 'CallCentre\_Memory.%'      ESCAPE '\'
   OR related_table LIKE 'CallCentre\_Semantic.%'    ESCAPE '\'
   OR related_table LIKE 'CallCentre\_Search.%'      ESCAPE '\'
   OR related_table LIKE 'CallCentre\_Observability.%' ESCAPE '\'
   OR related_table LIKE 'CallCentre\_Prediction.%'  ESCAPE '\'
GROUP BY related_table
ORDER BY related_table;

/* --- 1. Realign Domain prefix ----------------------------------------- */
UPDATE CallCentre_MEM_STD_T.Business_Glossary
SET    related_table =
         'CallCentre_DOM_STD_T.' ||
         SUBSTRING(related_table FROM POSITION('.' IN related_table) + 1)
WHERE  related_table LIKE 'CallCentre\_Domain.%' ESCAPE '\';

/* --- 2. Realign Prediction prefix ------------------------------------- */
UPDATE CallCentre_MEM_STD_T.Business_Glossary
SET    related_table =
         'CallCentre_PRE_STD_T.' ||
         SUBSTRING(related_table FROM POSITION('.' IN related_table) + 1)
WHERE  related_table LIKE 'CallCentre\_Prediction.%' ESCAPE '\';

/* --- 3. Realign Semantic prefix --------------------------------------- */
UPDATE CallCentre_MEM_STD_T.Business_Glossary
SET    related_table =
         'CallCentre_SEM_STD_T.' ||
         SUBSTRING(related_table FROM POSITION('.' IN related_table) + 1)
WHERE  related_table LIKE 'CallCentre\_Semantic.%' ESCAPE '\';

/* --- 4. Realign Memory prefix ----------------------------------------- */
UPDATE CallCentre_MEM_STD_T.Business_Glossary
SET    related_table =
         'CallCentre_MEM_STD_T.' ||
         SUBSTRING(related_table FROM POSITION('.' IN related_table) + 1)
WHERE  related_table LIKE 'CallCentre\_Memory.%' ESCAPE '\';

/* --- 5. Realign Search prefix ----------------------------------------- */
UPDATE CallCentre_MEM_STD_T.Business_Glossary
SET    related_table =
         'CallCentre_SCH_STD_T.' ||
         SUBSTRING(related_table FROM POSITION('.' IN related_table) + 1)
WHERE  related_table LIKE 'CallCentre\_Search.%' ESCAPE '\';

/* --- 6. Realign Observability prefix ---------------------------------- */
UPDATE CallCentre_MEM_STD_T.Business_Glossary
SET    related_table =
         'CallCentre_OBS_STD_T.' ||
         SUBSTRING(related_table FROM POSITION('.' IN related_table) + 1)
WHERE  related_table LIKE 'CallCentre\_Observability.%' ESCAPE '\';

/* --- 7. Same pattern for Design_Decision.affects_table ---------------- */
/* affects_table follows the same logical-prefix drift; mirror the fix.   */
UPDATE CallCentre_MEM_STD_T.Design_Decision
SET    affects_table =
         'CallCentre_DOM_STD_T.' ||
         SUBSTRING(affects_table FROM POSITION('.' IN affects_table) + 1)
WHERE  affects_table LIKE 'CallCentre\_Domain.%' ESCAPE '\';

UPDATE CallCentre_MEM_STD_T.Design_Decision
SET    affects_table =
         'CallCentre_PRE_STD_T.' ||
         SUBSTRING(affects_table FROM POSITION('.' IN affects_table) + 1)
WHERE  affects_table LIKE 'CallCentre\_Prediction.%' ESCAPE '\';

UPDATE CallCentre_MEM_STD_T.Design_Decision
SET    affects_table =
         'CallCentre_SEM_STD_T.' ||
         SUBSTRING(affects_table FROM POSITION('.' IN affects_table) + 1)
WHERE  affects_table LIKE 'CallCentre\_Semantic.%' ESCAPE '\';

UPDATE CallCentre_MEM_STD_T.Design_Decision
SET    affects_table =
         'CallCentre_MEM_STD_T.' ||
         SUBSTRING(affects_table FROM POSITION('.' IN affects_table) + 1)
WHERE  affects_table LIKE 'CallCentre\_Memory.%' ESCAPE '\';

UPDATE CallCentre_MEM_STD_T.Design_Decision
SET    affects_table =
         'CallCentre_SCH_STD_T.' ||
         SUBSTRING(affects_table FROM POSITION('.' IN affects_table) + 1)
WHERE  affects_table LIKE 'CallCentre\_Search.%' ESCAPE '\';

UPDATE CallCentre_MEM_STD_T.Design_Decision
SET    affects_table =
         'CallCentre_OBS_STD_T.' ||
         SUBSTRING(affects_table FROM POSITION('.' IN affects_table) + 1)
WHERE  affects_table LIKE 'CallCentre\_Observability.%' ESCAPE '\';

/* --- 8. Verify: any leftover legacy prefixes? ------------------------- */
SELECT 'Business_Glossary' AS tbl, related_table AS bad_value, COUNT(*) AS n
FROM   CallCentre_MEM_STD_T.Business_Glossary
WHERE  related_table LIKE 'CallCentre\_Domain.%'      ESCAPE '\'
   OR  related_table LIKE 'CallCentre\_Prediction.%'  ESCAPE '\'
   OR  related_table LIKE 'CallCentre\_Semantic.%'    ESCAPE '\'
   OR  related_table LIKE 'CallCentre\_Memory.%'      ESCAPE '\'
   OR  related_table LIKE 'CallCentre\_Search.%'      ESCAPE '\'
   OR  related_table LIKE 'CallCentre\_Observability.%' ESCAPE '\'
GROUP BY related_table
UNION ALL
SELECT 'Design_Decision', affects_table, COUNT(*)
FROM   CallCentre_MEM_STD_T.Design_Decision
WHERE  affects_table LIKE 'CallCentre\_Domain.%'      ESCAPE '\'
   OR  affects_table LIKE 'CallCentre\_Prediction.%'  ESCAPE '\'
   OR  affects_table LIKE 'CallCentre\_Semantic.%'    ESCAPE '\'
   OR  affects_table LIKE 'CallCentre\_Memory.%'      ESCAPE '\'
   OR  affects_table LIKE 'CallCentre\_Search.%'      ESCAPE '\'
   OR  affects_table LIKE 'CallCentre\_Observability.%' ESCAPE '\'
GROUP BY affects_table;
