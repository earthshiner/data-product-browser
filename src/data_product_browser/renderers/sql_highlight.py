"""SQL syntax highlighter producing the span classes used by the cookbook HTML.

Produces:
  <span class="sql-keyword">SELECT</span>
  <span class="sql-type">VARCHAR</span>
  <span class="sql-function">COUNT</span>
  <span class="sql-string">'value'</span>
  <span class="sql-number">42</span>
  <span class="sql-comment">-- comment</span>

Vocabulary is derived from the Teradata SQL Assistant syntax file
(``teradata.syn``) plus the Teradata SQL reference: every DDL/DML/DCL verb,
object kind and attribute that appears in any snippet, the full data-type
list, and the procedural and transactional vocabulary. Types get their own
class so that ``SMALLINT``, ``DATE``, ``DECIMAL(8,2)`` etc. are visually
distinct from generic keywords.

Multi-word phrases like ``DOUBLE PRECISION`` or ``LONG VARCHAR`` are not
matched as units — each component word is classified individually, which
produces the correct colouring even when the words appear in isolation.
"""

from __future__ import annotations

import html
import re

# ---------------------------------------------------------------------------
# DATA TYPES — get their own colour. Includes character-set names (which sit
# alongside types in column declarations).
# ---------------------------------------------------------------------------
_TYPES = frozenset(
    """
    BYTEINT SMALLINT INTEGER INT BIGINT
    DECIMAL NUMERIC NUMBER FLOAT REAL DOUBLE PRECISION
    BYTE VARBYTE BLOB
    CHAR CHARACTER VARCHAR CLOB LONG
    DATE TIME TIMESTAMP PERIOD INTERVAL
    JSON XML DATASET ST_GEOMETRY MBR MBB BOOLEAN ARRAY
    TIMEZONE UNICODE LATIN GRAPHIC VARGRAPHIC KANJISJIS KANJI1
    """.split()
)

# ---------------------------------------------------------------------------
# KEYWORDS — DDL, DML, DCL, procedural, transactional, session, locking,
# table/object attributes. Drawn directly from teradata.syn (every snippet
# title verb + every reserved word appearing in any sample).
# ---------------------------------------------------------------------------
_KEYWORDS = frozenset(
    """
    SELECT FROM WHERE INTO VALUES INSERT UPDATE DELETE MERGE TRUNCATE
    JOIN LEFT RIGHT INNER OUTER FULL CROSS LATERAL ON USING MATCHED
    AND OR NOT IN IS NULL TRUE FALSE EXISTS BETWEEN LIKE LIKE_REGEX
    ANY SOME ALL DISTINCT TOP SAMPLE QUALIFY UNION INTERSECT MINUS
    EXCEPT WITH RECURSIVE CYCLE AS
    GROUP BY ORDER HAVING LIMIT OFFSET ASC DESC
    CASE WHEN THEN ELSE END IF
    OVER PARTITION ROWS RANGE PRECEDING FOLLOWING CURRENT ROW
    UNBOUNDED COLLECT STATISTICS DEMOGRAPHICS QUALIFY
    CAST COALESCE NULLIF GREATEST LEAST DEFAULT
    CREATE ALTER DROP REPLACE RENAME MODIFY COMMENT COMPILE
    INITIATE RESTART RELEASE LOCK CHECKPOINT FLUSH
    TABLE VIEW INDEX MACRO PROCEDURE FUNCTION TRIGGER TYPE
    DATABASE USER ROLE PROFILE CONSTRAINT SCHEMA SERVER ZONE MAP
    METHOD ORDERING TRANSFORM AUTHORIZATION CAST GLOP
    HASH JOIN REPLICATION GROUP RULESET ERROR FOREIGN MAPPING
    AVRO CSV PARQUET ORC TEXT JSON_TABLE
    PRIMARY UNIQUE FOREIGN KEY REFERENCES CHECK
    FALLBACK JOURNAL BEFORE AFTER DUAL NO FREESPACE PERM SPOOL
    TEMPORARY ACCOUNT COLLATION PASSWORD MAP COLOCATE
    INLINE LENGTH TITLE FORMAT CHARACTER SET CASESPECIFIC
    RETURNING RETURNS RETURN PARAMETER STYLE LANGUAGE EXTERNAL NAME
    SECURITY INVOKER DEFINER TRUSTED DETERMINISTIC SPECIFIC
    CONTAINS READS MODIFIES SQL SELF RESULT
    BEGIN END DECLARE ELSEIF WHILE FOR LOOP LEAVE ITERATE
    CALL EXEC EXECUTE
    HANDLER CONDITION CONTINUE EXIT SQLEXCEPTION SQLWARNING SQLSTATE
    CURSOR OPEN CLOSE FETCH NEXT PRIOR
    COMMIT ROLLBACK WORK BT ET ABORT
    LOCKING ACCESS EXCLUSIVE SHARE SHARED READ WRITE NOWAIT MODE
    GRANT REVOKE GIVE OPTION ADMIN BUT MONITOR PROXY CONNECT THROUGH
    LOGON LOGOFF ROOT PERMANENT
    SESSION CHARACTERISTICS ISOLATION LEVEL TRANSACTION UNCOMMITTED
    REPEATABLE SERIALIZABLE QUERY_BAND CALENDAR DATEFORM TRACE
    SUBSCRIBER TRANSACTIONTIME VALIDTIME TEMPORAL
    SHOW HELP EXPLAIN STATISTICS
    LOADING CONCURRENT ISOLATED OVERRIDE MULTIPLE BATCH BUFFERED
    LOGGING DENIALS EACH BAND PASS
    RESTRICT CASCADE ENABLED DISABLED FINAL CONSTRUCTOR INSTANCE
    IMPORT EXPORT SOURCE TARGET REFERENCING OLD NEW
    SKEW
    """.split()
)

# ---------------------------------------------------------------------------
# FUNCTIONS — built-in scalar, aggregate, window, math, string, date and
# Teradata-specific functions. Recognised when followed by '(' or used as a
# bare identifier (so CURRENT_DATE, CURRENT_TIMESTAMP etc. colour without
# requiring parentheses).
# ---------------------------------------------------------------------------
_FUNCTIONS = frozenset(
    """
    COUNT SUM AVG MIN MAX MEDIAN VARIANCE STDDEV STDDEV_POP STDDEV_SAMP
    VAR_POP VAR_SAMP COVAR_POP COVAR_SAMP CORR REGR_SLOPE REGR_INTERCEPT
    PERCENTILE_CONT PERCENTILE_DISC PERCENT_RANK CUME_DIST
    RANK ROW_NUMBER DENSE_RANK NTILE LAG LEAD FIRST_VALUE LAST_VALUE
    NVL NVL2 ZEROIFNULL NULLIFZERO COALESCE NULLIF GREATEST LEAST
    TRIM LTRIM RTRIM LPAD RPAD UPPER LOWER INITCAP REVERSE
    SUBSTR SUBSTRING LENGTH CHARACTERS CHARACTER_LENGTH OCTET_LENGTH
    BYTES POSITION STRPOS INDEX CONTAINS CONCAT ASCII CHR
    OREPLACE OTRANSLATE
    REGEXP_REPLACE REGEXP_SUBSTR REGEXP_INSTR REGEXP_SIMILAR LIKE_REGEX
    TO_DATE TO_TIMESTAMP TO_CHAR TO_NUMBER
    CURRENT_DATE CURRENT_TIMESTAMP CURRENT_TIME CURRENT_USER CURRENT_ROLE
    CURRENT_SCHEMA USER DATABASE SESSION
    EXTRACT ADD_MONTHS MONTHS_BETWEEN LAST_DAY NEXT_DAY
    TD_DAY_OF_WEEK TD_DAY_OF_MONTH TD_DAY_OF_YEAR TD_WEEK_OF_YEAR
    TD_MONTH_OF_QUARTER TD_QUARTER_OF_YEAR TD_MONTH_BEGIN TD_MONTH_END
    TD_YEAR_BEGIN TD_YEAR_END TD_WEEK_BEGIN TD_WEEK_END
    TD_NORMALIZE_OVERLAP TD_NORMALIZE_MEET TD_SYSFNLIB
    ABS MOD ROUND CEIL CEILING FLOOR EXP LN LOG SQRT POWER SIGN
    RANDOM TRUNC PI
    HASHROW HASHBUCKET HASHAMP HASHBAKAMP MD5
    COMPRESS DECOMPRESS ENCRYPT DECRYPT
    CAST TYPE TYPEOF
    JSONEXTRACT JSONEXTRACTVALUE JSON_KEYS JSON_TABLE
    GROUPING ROW_COUNT
    """.split()
)

_TOKEN_RE = re.compile(
    r"(--[^\n]*"  # line comment
    r"|'(?:''|[^'])*'"  # single-quoted string
    r"|\d+(?:\.\d+)?"  # number
    r"|[A-Za-z_]\w*"  # identifier or keyword
    r"|[^\w\s]"  # punctuation
    r"|\s+"  # whitespace
    r")"
)


def highlight_sql(sql: str) -> str:
    """Return HTML with syntax-highlight spans applied to Teradata SQL."""
    result: list[str] = []
    in_comment_block = False

    for line in sql.splitlines(keepends=True):
        stripped = line.lstrip()

        if stripped.startswith("--"):
            result.append(f'<span class="sql-comment">{html.escape(line)}</span>')
            continue

        for tok in _TOKEN_RE.findall(line):
            if not tok:
                continue
            if tok.startswith("--"):
                result.append(f'<span class="sql-comment">{html.escape(tok)}</span>')
            elif tok.startswith("'"):
                result.append(f'<span class="sql-string">{html.escape(tok)}</span>')
            elif re.fullmatch(r"\d+(?:\.\d+)?", tok):
                result.append(f'<span class="sql-number">{html.escape(tok)}</span>')
            elif tok.upper() in _TYPES:
                result.append(f'<span class="sql-type">{html.escape(tok)}</span>')
            elif tok.upper() in _KEYWORDS:
                result.append(f'<span class="sql-keyword">{html.escape(tok)}</span>')
            elif tok.upper() in _FUNCTIONS:
                result.append(f'<span class="sql-function">{html.escape(tok)}</span>')
            else:
                result.append(html.escape(tok))

    return "".join(result)
