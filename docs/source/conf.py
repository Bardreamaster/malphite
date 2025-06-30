# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath("."))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "malphite"
copyright = "2025, Wei Jinqi"
author = "Wei Jinqi"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "autodoc2",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx.ext.napoleon",
    "sphinx.ext.githubpages",
]

templates_path = ["_templates"]
exclude_patterns = []

# Options for autodoc2 extension
autodoc2_packages = [
    "../../src/malphite",
]
autodoc2_module_all_regexes = []

# autodoc2_render_plugin = "myst"
autodoc2_docstring_parser_regexes = [
    # this will render all docstrings as Markdown
    (r".*", "docstring_parser"),
]
## ignore all warnings from this package
# nitpick_ignore_regex = [
#     ("py:.*", r"malphite\..*"),
# ]

# myst config
## enable md docstring
myst_enable_extensions = [
    "fieldlist",
]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]

# Options for Furo theme
source_repository = "https://github.com/Bardreamaster/malphite"
source_branch = "main"
source_directory = "docs/source/"
html_theme_options = {
    "source_repository": source_repository,
    "source_branch": source_branch,
    "source_directory": source_directory,
    "top_of_page_buttons": ["view", "edit"],
}
