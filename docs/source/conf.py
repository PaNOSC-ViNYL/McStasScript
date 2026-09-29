# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import os
import sys
sys.path.insert(0, os.path.abspath('../../mcstasscript'))
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------------

project = 'McStasScript'
copyright = '2022, Mads Bertelsen'
author = 'Mads Bertelsen'


# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'myst_nb',
]

autosummary_generate = True

# Don't auto-generate docs for tests or internal libpyvinyl
autodoc_exclude_patterns = [
    '*tests*',
    '*integration_tests*',
]

templates_path = ['_templates']

master_doc = 'index'

exclude_patterns = []

# myst_nb: don't execute notebooks during build (they're pre-rendered .ipynb)
nb_execution_mode = 'off'


# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_book_theme'

html_theme_options = {
    "repository_url": "https://github.com/PaNOSC-ViNYL/McStasScript",
    "repository_branch": "master",
    "path_to_docs": "docs",
    "use_repository_button": True,
    "use_issues_button": True,
    "use_edit_page_button": True,
    "show_toc_level": 2,
}

html_static_path = ['_static']
