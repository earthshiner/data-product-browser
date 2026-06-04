"""Local web server that serves an interactive Data Product Browser.

The server reads AI-Native Data Product metadata live from Teradata (via the
same ``collect()`` engine used by the CLI) and serves a browsable single-page
UI. It depends on no AI client — all rendering is deterministic from metadata.
"""
