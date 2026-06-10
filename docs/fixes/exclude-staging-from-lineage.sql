/* ---------------------------------------------------------------------------
 * Exclude staging objects from data_lineage
 *
 * Symptom: Trust engine raises CALLCENTRE-SEM-011 ("Lineage metadata exposes
 * BUS_V access endpoints") for rows whose source_database/target_database is
 * a staging area (CallCentre_STG_STD_T.*). Staging should not be part of the
 * agent-facing lineage surface at all.
 *
 * Fix: Soft-delete (is_active = 0) every data_lineage row that references a
 * staging database on either side. Idempotent; safe to re-run.
 *
 * Preview before applying — confirm the affected rows look right.
 * ------------------------------------------------------------------------ */

/* --- A. Preview ----------------------------------------------------- */
SELECT lineage_id
     , source_database, source_table
     , target_database, target_table
FROM   CallCentre_SEM_STD_V.data_lineage
WHERE  is_active = 1
  AND  ( source_database LIKE '%\_STG\_STD\_T' ESCAPE '\'
      OR target_database LIKE '%\_STG\_STD\_T' ESCAPE '\' )
ORDER BY lineage_id;

/* --- B. Soft-delete staging-touching rows --------------------------- */
UPDATE CallCentre_SEM_STD_T.data_lineage
SET    is_active = 0
WHERE  is_active = 1
  AND  ( source_database LIKE '%\_STG\_STD\_T' ESCAPE '\'
      OR target_database LIKE '%\_STG\_STD\_T' ESCAPE '\' );

/* --- C. Verify ------------------------------------------------------ */
SELECT COUNT(*) AS active_staging_rows_remaining
FROM   CallCentre_SEM_STD_V.data_lineage
WHERE  is_active = 1
  AND  ( source_database LIKE '%\_STG\_STD\_T' ESCAPE '\'
      OR target_database LIKE '%\_STG\_STD\_T' ESCAPE '\' );
