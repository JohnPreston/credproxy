#!/usr/bin/env sh
# --------------------------------------------------------------
#  entrypoint‑helper.sh
#  • Replaces any <VAR>__FILE env var with the file content
#  • Keeps all interior newlines, strips only trailing ones
#  • Finally execs the command given to the container
# --------------------------------------------------------------

set -eu

# -----------------------------------------------------------------
# 1. Expand <VAR>__FILE → <VAR>
# -----------------------------------------------------------------
for env_var in $(env | awk -F= '$1 ~ /__FILE$/ {print $1}'); do
    file_path="${!env_var}"

    # Bail out if the var is empty or the file is not readable
    if [ -z "$file_path" ] || [ ! -r "$file_path" ]; then
        echo "${env_var} is set but does not point to a readable file" >&2
        continue
    fi

    # Read the file in its raw form
    raw_value="$(cat "$file_path")"

    # Strip only trailing newlines
    cleaned_value="$(printf '%s' "$raw_value" | sed 's/\n*$//')"

    # Export under the base name
    base_var="${env_var%__FILE}"
    export "${base_var}=${cleaned_value}"

    # Optional: remove the *__FILE variable to avoid leakage
    unset "$env_var"

    echo "Expanded ${env_var} → ${base_var}"
done
