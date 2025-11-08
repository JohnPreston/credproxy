# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path


# Add project root to path to import credproxy
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import credproxy


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "CredProxy"
copyright = "2025-present, John MILLE"
author = "John MILLE"
version = credproxy.__version__
release = credproxy.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",  # Auto-generate API docs from docstrings
    "sphinx.ext.autosummary",  # Generate summary tables
    "sphinx.ext.intersphinx",  # Cross-reference to Python docs
    "sphinx.ext.viewcode",  # Highlight source code
    "sphinx.ext.napoleon",  # Support Google/NumPy style docstrings
    "sphinx_json_schema",  # Generate docs from JSON schema
    "myst_parser",  # Markdown support during transition
    "sphinx_sitemap",  # Generate sitemap.xml for SEO
    "sphinx-jsonschema",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# The suffix(es) of source filenames.
source_suffix = {
    ".rst": None,
    ".md": "myst_parser",
}

# The master toctree document.
master_doc = "index"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"

# Sitemap configuration
html_baseurl = "https://docs.credproxy.compose-x.io/"
html_theme_options = {
    # Light theme colors
    "light_css_variables": {
        "color-brand-primary": "#007acc",
        "color-brand-content": "#ffffff",
        "color-background-primary": "#ffffff",
        "color-background-secondary": "#f5f5f5",
        "color-foreground-primary": "#000000",
        "color-foreground-secondary": "#333333",
        "color-highlighted-background": "#fff3cd",
    },
    # Dark theme colors
    "dark_css_variables": {
        "color-brand-primary": "#58a6ff",
        "color-brand-content": "#ffffff",
        "color-background-primary": "#1a1a1a",
        "color-background-secondary": "#242424",
        "color-foreground-primary": "#ffffff",
        "color-foreground-secondary": "#e0e0e0",
        "color-highlighted-background": "#3d3d1a",
    },
    # Navigation settings
    "navigation_with_keys": True,
    "sidebar_hide_name": False,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# -- Autodoc configuration -------------------------------------------------

# Mock external dependencies for builds
autodoc_mock_imports = ["boto3", "botocore", "flask", "prometheus_client", "watchdog"]

# Default options for autodoc directives
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

# -- Intersphinx configuration -----------------------------------------------

# Intersphinx mapping for Python docs
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "boto3": ("https://boto3.amazonaws.com/v1/documentation/api/latest/", None),
}

# -- Napoleon configuration -------------------------------------------------

# Enable Google and NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# -- API documentation configuration -------------------------------------------

# Path configuration for importing credproxy
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Auto-document all modules
apidoc_modules = [
    {
        "path": "credproxy",
        "destination": "api/",
        "exclude_patterns": ["**/test*"],
        "automodule_options": {
            "members",
            "show-inheritance",
            "undoc-members",
            "special-members",
        },
    }
]

# -- Nitpicky mode for validation -------------------------------------------

nitpicky = True
nitpick_ignore = [
    ("py:class", "boto3.session.Session"),
    ("py:class", "botocore.credentials.Credentials"),
    ("py:class", "flask.Flask"),
    ("py:class", "watchdog.events.FileSystemEventHandler"),
    ("py:class", "watchdog.events.FileSystemEvent"),
]
