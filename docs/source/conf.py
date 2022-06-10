# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../../mcstasscript'))
sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('/Users/madsbertelsen/PaNOSC/libpyvinyl/github/libpyvinyl'))

print(sys.path)

# -- Project information -----------------------------------------------------

project = 'McStasScript'
copyright = '2022, Mads Bertelsen'
author = 'Mads Bertelsen'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.autosummary',
              'sphinx.ext.napoleon',
              #'nbsphinx',
              'myst_nb',
              ]

autosummary_generate = True

# Add any paths that contain templates here, relative to this directory.
#templates_path = ['source/_templates']
templates_path = ['_templates']

master_doc = 'index'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

execution_timeout = 200


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_book_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
    #"logo_only": True,
    "repository_url": "https://github.com/PaNOSC-ViNYL/McStasScript",
    "repository_branch": "master",
    "path_to_docs": "docs",
    "use_repository_button": True,
    "use_issues_button": True,
    "use_edit_page_button": True,
    "show_toc_level": 2,  # Show subheadings in secondary sidebar
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
#man_pages = [(master_doc, 'McStasScript', u'McStasScript Documentation', 'Mads Bertelsen', 1)]
