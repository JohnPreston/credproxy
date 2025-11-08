#  SPDX-License-Identifier: MPL-2.0
#  Copyright 2025-present John Mille <john@ews-network.net>

"""CredProxy - AWS credentials proxy provider."""

from __future__ import annotations


__version__ = "0.1.0"
__author__ = "John Preston <john@ews-network.net>"
__license__ = "MPL-2.0"

# Build information (populated at Docker build time)
__git_commit__ = "development"
__build_date__ = "unknown"

# Try to import build-time information if available
try:
    from credproxy._build_info import (
        __version__ as _build_version,
        __build_date__ as _build_date,
        __git_commit__ as _git_commit,
    )

    __git_commit__ = _git_commit
    __build_date__ = _build_date
    # Use build version if different from source
    if _build_version and _build_version != "0.1.0":
        __version__ = _build_version
except ImportError:
    # _build_info.py only exists in Docker builds
    pass


__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "__git_commit__",
    "__build_date__",
]
