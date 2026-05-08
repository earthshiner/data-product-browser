"""SQL syntax highlighter producing the same span classes as the existing cookbook HTML.

Produces:
  <span class="sql-keyword">SELECT</span>
  <span class="sql-function">COUNT</span>
  <span class="sql-string">'value'</span>
  <span class="sql-number">42</span>
  <span class="sql-comment">-- comment</span>

These classes are defined in the cookbook template CSS and match the style of
the existing hand-crafted MortgagePlatform_Cookbook.html exactly.
"""

from __future__ import annotations

import html
import re

_KEYWORDS = frozenset(
    """
    SELECT FROM WHERE JOIN LEFT RIGHT INNER OUTER FULL ON AND OR NOT IN
    EXISTS BETWEEN LIKE IS NULL TRUE FALSE GROUP BY ORDER HAVING LIMIT
    OFFSET INSERT INTO VALUES UPDATE SET DELETE CREATE TABLE VIEW INDEX
    DROP ALTER WITH AS CASE WHEN THEN ELSE END UNION ALL DISTINCT TOP
    SAMPLE QUALIFY CAST COALESCE NULLIF PARTITION OVER ROWS RANGE
    PRECEDING FOLLOWING CURRENT ROW COLLECT STATISTICS PRIMARY UNIQUE
    CONSTRAINT DEFAULT REFERENCES FOREIGN KEY CHECK SHOW HELP LOCKING
    ACCESS FOR EACH REPLACE MERGE USING MATCHED RECURSIVE CYCLE
    """.split()
)

_FUNCTIONS = frozenset(
    """
    COUNT SUM AVG MIN MAX RANK ROW_NUMBER DENSE_RANK LAG LEAD FIRST_VALUE
    LAST_VALUE NVL ZEROIFNULL NULLIFZERO TRIM UPPER LOWER SUBSTR LENGTH
    TO_DATE TO_TIMESTAMP CURRENT_DATE CURRENT_TIMESTAMP DATE TIMESTAMP
    INTERVAL YEAR MONTH DAY HOUR MINUTE SECOND FORMAT CAST TYPE TYPEOF
    OREPLACE OTRANSLATE CHARACTERS BYTES POSITION STRPOS CONTAINS LIKE_REGEX
    TD_NORMALIZE_OVERLAP TD_SYSFNLIB REGR_SLOPE CORR STDDEV VAR_SAMP
    """.split()
)

_TOKEN_RE = re.compile(
    r"(--[^\n]*"            # line comment
    r"|'(?:''|[^'])*'"      # single-quoted string
    r"|\d+(?:\.\d+)?"       # number
    r"|[A-Za-z_]\w*"        # identifier or keyword
    r"|[^\w\s]"             # punctuation
    r"|\s+"                 # whitespace
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
            elif tok.upper() in _KEYWORDS:
                result.append(f'<span class="sql-keyword">{html.escape(tok)}</span>')
            elif tok.upper() in _FUNCTIONS:
                result.append(f'<span class="sql-function">{html.escape(tok)}</span>')
            else:
                result.append(html.escape(tok))

    return "".join(result)
