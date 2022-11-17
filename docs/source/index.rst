Welcome to McStasScript's documentation!
========================================

**McStasScript** is a Python API for `McStas <https://mcstas.org>`_, which allows the user to get help, build their instrument, perform simulations and plot the resulting data.
This site serves as the documentation for the package and contains conceptual explanations of how the package is meant to be used, tutorials and a reference for all internal functions/methods.

Documentation
=============

.. toctree::
   :caption: Getting started
   :maxdepth: 2
   
   getting_started/overview
   getting_started/installation
   getting_started/version_history
   getting_started/quick_start
   
.. toctree::
   :caption: User guide
   :maxdepth: 2
   
   user_guide/instrument_object
   user_guide/component_object
   user_guide/parameters_and_variables
   user_guide/data
   user_guide/plotting
   user_guide/functions
   user_guide/widgets
   user_guide/instrument_reader

.. toctree::
   :caption: McStasScript Tutorial
   :maxdepth: 1
   
   tutorial/McStasScript_tutorial_1_the_basics
   tutorial/McStasScript_tutorial_2_SPLIT.ipynb
   tutorial/McStasScript_tutorial_3_EXTEND_and_WHEN.ipynb
   tutorial/McStasScript_tutorial_4_JUMP.ipynb
   tutorial/McStasScript_tutorial_5_MCPL_bridges.ipynb
   tutorial/McStasScript_tutorial_6_Diagnostics.ipynb
   
.. toctree::
   :caption: McStas Union Tutorial
   :maxdepth: 1
   
   tutorial/Union_tutorial_1_processes_and_materials.ipynb
   tutorial/Union_tutorial_2_geometry.ipynb
   tutorial/Union_tutorial_3_loggers.ipynb
   tutorial/Union_tutorial_4_conditionals.ipynb
   tutorial/Union_tutorial_5_masks.ipynb
   tutorial/Union_tutorial_6_Exit_and_number_of_activations.ipynb
   tutorial/Union_tutorial_7_Tagging_history.ipynb
   
.. autosummary::
   :toctree: _autosummary
   :template: custom-module-template.rst
   :caption: Reference
   :recursive:
   
   mcstasscript
   
.. autosummary::
   :toctree: _autosummary
   :template: custom-module-template.rst
   :caption: Reference (libpyvinyl)
   :recursive:
   
   libpyvinyl

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
