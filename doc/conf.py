# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------

project = "Project-W"
copyright = "2023-2025, Julian Partanen & Markus Everling"
author = "Julian Partanen, Markus Everling"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinxcontrib.openapi",
    "sphinxcontrib.autodoc_pydantic",
    "sphinx_mdinclude",
    "sphinx.ext.autodoc",
    "sphinx_rtd_theme",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = []

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# These paths are either relative to html_static_path
# or fully qualified paths (eg. https://...)
html_css_files = [
    # this fixes the style of tables when using the readthedocs theme
    # refer to https://stackoverflow.com/questions/69359978/grid-table-does-not-word-wrap
    "css/custom.css",
]

# -- API autodoc setup -------------------------------------------------------

import json
from pathlib import Path

import project_W.dependencies as dp
from project_W.models.settings import Settings

config_dict = {
    "client_url": "http://localhost:5173/#",
    "web_server": {
        "address": "127.0.0.1",
        "no_https": True,
    },
    "postgres_connection_string": "postgresql://postgres@%2Fvar%2Frun%2Fpostgresql/postgres",
    "redis_connection": {
        "connection_string": "redis://localhost:6379/project-W",
    },
    "security": {
        "secret_key": "f26a5feb0eb502fb2b4f872026ce7b5d3986dbfef77d72d3f29050df2f8b3bdb",
    },
    "smtp_server": {
        "hostname": "example.org",
        "sender_email": "test@example.org",
    },
}
dp.config = Settings.model_validate(config_dict)
from project_W.app import app
from project_W.routers import ldap, local_account, oidc

app.include_router(oidc.router, prefix="/api")
app.include_router(ldap.router, prefix="/api")
app.include_router(local_account.router, prefix="/api")

openapi_file = Path(__file__).parent / ".sphinx-openapi.json"
openapi_file.write_text(json.dumps(app.openapi()))

import os

# -- Config file autodoc setup -----------------------------------------------
import sys

sys.path.append(os.path.abspath("."))
import runner_settings

autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_validator_members = False
autodoc_pydantic_model_show_validator_summary = False
