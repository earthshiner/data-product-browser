/* ---------------------------------------------------------------------------
 * CallCentre_SEM_STD_T.view_column_type
 *
 * Curated overrides for view-column data types. DBC.ColumnsV returns blanks
 * for view columns (types resolve at query time), so the column_catalogue
 * view LEFT JOINs this table to surface friendly types for *_BUS_V columns.
 *
 * One row per (database_name, view_name, column_name). Seed via the
 * companion view-column-type-seed.sql which is generated from a live
 * introspection dump.
 * ------------------------------------------------------------------------ */

CREATE MULTISET TABLE CallCentre_SEM_STD_T.view_column_type
( database_name  VARCHAR(128)   NOT NULL
, view_name      VARCHAR(128)   NOT NULL
, column_name    VARCHAR(128)   NOT NULL
, data_type      VARCHAR(64)    NOT NULL
, is_active      BYTEINT        NOT NULL DEFAULT 1
, source_note    VARCHAR(256)
)
PRIMARY INDEX (database_name, view_name, column_name);

COLLECT STATISTICS COLUMN (database_name, view_name, column_name)
       ON CallCentre_SEM_STD_T.view_column_type;

/* Locking view to enforce the no-direct-table-read standard */
REPLACE VIEW CallCentre_SEM_STD_V.view_column_type
AS
LOCKING ROW FOR ACCESS
SELECT  database_name
      , view_name
      , column_name
      , data_type
      , is_active
      , source_note
FROM    CallCentre_SEM_STD_T.view_column_type;
