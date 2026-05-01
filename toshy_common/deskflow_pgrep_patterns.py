"""Pgrep regex patterns for Deskflow process detection.

toshy_common/deskflow_pgrep_patterns.py

Patterns used with `pgrep -f` to match the full command line of the
unified `deskflow-core` binary (introduced in Deskflow v1.24.0).

The (^|/) prefix handles both bare command names and full paths.
Word boundaries (\\b) prevent partial matches against unrelated arguments.

Kept in a dedicated module to avoid regex corruption during artifact editing.
"""

# Match: deskflow-core server [options]
deskflow_core_server_rgx = r'(^|/)deskflow-core\b.*\bserver\b'

# Match: deskflow-core client [options]
deskflow_core_client_rgx = r'(^|/)deskflow-core\b.*\bclient\b'

# End of file #
