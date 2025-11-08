#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

"""Alternative entry point for python -m credproxy execution.

This module provides an alternative way to run CredProxy using Python's module
execution syntax. While the primary entry point is the 'credproxy' command
defined in pyproject.toml, this module enables:

- Development workflows: python -m credproxy
- Testing scenarios: Module-based execution
- Python ecosystem compliance: Standard package entry point

Usage:
    python -m credproxy --config config.yaml

This is equivalent to:
    credproxy --config config.yaml

The primary production usage should use the 'credproxy' command, but this
alternative entry point is maintained for development convenience and Python
packaging best practices.
"""

import sys

from credproxy.cli import main


if __name__ == "__main__":
    sys.exit(main())
