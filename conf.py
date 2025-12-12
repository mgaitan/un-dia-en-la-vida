# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Un día en la vida - Cenital"
copyright = "2024-2025"
author = "Tomás Aguerre"
version = "2025.12"
release = version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

extensions = [
    "myst_parser",
]

html_static_path = ["_static"]

# EPUB configuration
epub_ignore_images = True
epub_exclude_files = [
    ".doctrees",
    ".doctrees/*",
    ".doctrees/**",
    "**/.doctrees/*",
    "**/.doctrees/**",
    "_sources/**",
    "_static/**",
    "search.html",
    "searchindex.js",
    ".buildinfo",
    ".buildinfo.bak",
]
epub_show_urls = "hide"
