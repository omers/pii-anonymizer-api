# Prevent pytest from collecting files outside of the configured testpaths.
# The scripts/ directory contains standalone diagnostic utilities, not test suites.
collect_ignore_glob = ["scripts/*"]
