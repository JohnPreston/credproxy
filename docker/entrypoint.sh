#!/usr/bin/env sh
# --------------------------------------------------------------
#  entrypoint.sh
#  • Runs init_secrets.sh to expand __FILE environment variables
#  • Then starts the CredProxy Python application
# --------------------------------------------------------------

set -eu

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# -----------------------------------------------------------------
# 1. Run init_secrets.sh to handle Docker secrets
# -----------------------------------------------------------------
echo "Initializing secrets..."
if [ -f "${SCRIPT_DIR}/init_secrets.sh" ]; then
    # Source the script to run it in the current shell environment
    . "${SCRIPT_DIR}/init_secrets.sh" -- "$@"
else
    echo "Warning: init_secrets.sh not found in ${SCRIPT_DIR}"
fi

# -----------------------------------------------------------------
# 2. Start CredProxy application directly
# -----------------------------------------------------------------
echo "Starting CredProxy..."

# Default command if none provided
if [ $# -eq 0 ]; then
    # Run credproxy directly with system Python (dependencies installed globally)
    exec python -m credproxy --config /credproxy/config.yaml
else
    # Execute whatever command was passed
    exec "$@"
fi
