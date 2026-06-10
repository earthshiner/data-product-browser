/* ---------------------------------------------------------------------------
 * column_metadata gap report + INSERT scaffold
 *
 * Symptom: Entity panel shows "No column metadata" for tables like
 * Call_Score_H, Call_Score_Cnt_H, Call_Summary_H. Diagnostic shows zero
 * near-miss rows under any other prefix.
 *
 * Diagnosis: column_metadata is a *curated* table — rows must be authored,
 * one per (database, table, column). This script confirms which deployed
 * tables in the product's standard databases have zero rows in
 * column_metadata, then emits ready-to-edit INSERT scaffolds pulled from
 * DBC so the operator only has to fill in business_description and any
 * PII / sensitivity / classification flags.
 *
 * Run order:
 *   1. Section A — coverage matrix (read-only).
 *   2. Section B — generate scaffolds for the gap tables, copy/paste into
 *      a worksheet, edit, then run the INSERTs.
 *
 * Edit DB_LIST below to suit the product you're curating.
 * ------------------------------------------------------------------------ */

/* --- A. Coverage matrix ---------------------------------------------- */
/* One row per deployed table; gap_rows = (deployed columns) - (curated rows). */
WITH deployed AS
(
    SELECT  TRIM(DatabaseName) AS database_name
          , TRIM(TableName)    AS table_name
          , COUNT(*)           AS deployed_cols
    FROM    DBC.ColumnsV
    WHERE   DatabaseName IN ('CallCentre_DOM_STD_T', 'CallCentre_PRE_STD_T',
                             'CallCentre_SEM_STD_T', 'CallCentre_MEM_STD_T',
                             'CallCentre_SCH_STD_T', 'CallCentre_OBS_STD_T')
    GROUP BY TRIM(DatabaseName), TRIM(TableName)
)
, curated AS
(
    SELECT  TRIM(database_name) AS database_name
          , TRIM(table_name)    AS table_name
          , COUNT(*)            AS curated_rows
    FROM    CallCentre_SEM_STD_T.column_metadata
    WHERE   is_active = 1
    GROUP BY TRIM(database_name), TRIM(table_name)
)
SELECT  d.database_name
      , d.table_name
      , d.deployed_cols
      , COALESCE(c.curated_rows, 0)                    AS curated_rows
      , d.deployed_cols - COALESCE(c.curated_rows, 0)  AS gap_rows
      , CASE
          WHEN COALESCE(c.curated_rows, 0) = 0                THEN 'NO COVERAGE'
          WHEN COALESCE(c.curated_rows, 0) < d.deployed_cols  THEN 'PARTIAL'
          ELSE                                                     'COMPLETE'
        END                                            AS coverage_status
FROM    deployed d
LEFT JOIN curated c
       ON c.database_name = d.database_name
      AND c.table_name    = d.table_name
ORDER BY coverage_status, d.database_name, d.table_name;


/* --- B. Scaffold INSERTs for the NO-COVERAGE tables ------------------ */
/* Emits one INSERT per missing column. business_description is left as a
 * placeholder — replace with a real description before running. Adjust
 * is_pii / is_sensitive / is_required after review.                    */

SELECT
    'INSERT INTO CallCentre_SEM_STD_T.column_metadata ('
 || 'database_name, table_name, column_name, business_description, '
 || 'data_type, data_classification, is_pii, is_sensitive, is_required, '
 || 'is_active) VALUES ('
 || '''' || TRIM(c.DatabaseName) || ''', '
 || '''' || TRIM(c.TableName)    || ''', '
 || '''' || TRIM(c.ColumnName)   || ''', '
 || '''TODO: business description for ' || TRIM(c.ColumnName) || ''', '
 || '''' || TRIM(c.ColumnType)   || ''', '
 || '''GENERAL'', '
 || '0, 0, 1, 1);'                                              AS insert_stmt
FROM   DBC.ColumnsV c
WHERE  c.DatabaseName IN ('CallCentre_DOM_STD_T', 'CallCentre_PRE_STD_T',
                          'CallCentre_SEM_STD_T', 'CallCentre_MEM_STD_T',
                          'CallCentre_SCH_STD_T', 'CallCentre_OBS_STD_T')
  AND  NOT EXISTS (
           SELECT 1
           FROM   CallCentre_SEM_STD_T.column_metadata m
           WHERE  TRIM(m.database_name) = TRIM(c.DatabaseName)
             AND  TRIM(m.table_name)    = TRIM(c.TableName)
       )
ORDER BY c.DatabaseName, c.TableName, c.ColumnId;


/* --- C. Quick verify after editing + running the INSERTs ------------- */
/* Should drop to zero rows once every deployed table has curated metadata. */
SELECT  d.database_name, d.table_name, d.deployed_cols
FROM    (
            SELECT TRIM(DatabaseName) AS database_name
                 , TRIM(TableName)    AS table_name
                 , COUNT(*)           AS deployed_cols
            FROM   DBC.ColumnsV
            WHERE  DatabaseName IN ('CallCentre_DOM_STD_T', 'CallCentre_PRE_STD_T',
                                    'CallCentre_SEM_STD_T', 'CallCentre_MEM_STD_T',
                                    'CallCentre_SCH_STD_T', 'CallCentre_OBS_STD_T')
            GROUP BY TRIM(DatabaseName), TRIM(TableName)
        ) d
WHERE   NOT EXISTS (
            SELECT 1
            FROM   CallCentre_SEM_STD_T.column_metadata m
            WHERE  TRIM(m.database_name) = d.database_name
              AND  TRIM(m.table_name)    = d.table_name
              AND  m.is_active           = 1
        )
ORDER BY d.database_name, d.table_name;
