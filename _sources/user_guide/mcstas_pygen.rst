Converting instrument files
===========================

The ``.instr`` suffix is shared by McStas and McXtrace, so select the
appropriate conversion function explicitly. For McStas, use the
``mcstas-pygen`` command supplied with McStas:

.. code-block:: python

   import mcstasscript as ms

   instrument = ms.mcstas_pygen("my_instrument.instr")

For McXtrace, use the corresponding ``mcxtrace-pygen`` command:

.. code-block:: python

   instrument = ms.mcxtrace_pygen("my_instrument.instr")

The generated file is written next to the input file as
``my_instrument_generated.py``. Use ``destination`` to choose a generated
Python file or an existing destination directory:

.. code-block:: python

   instrument = ms.mcstas_pygen(
       "my_instrument.instr",
       destination="generated/my_instrument.py",
   )

The optional ``input_path`` is passed to the generated ``make`` function and
sets the work directory used by the returned instrument:

.. code-block:: python

   instrument = ms.mcstas_pygen(
       "my_instrument.instr",
       input_path="path/to/components",
   )

The input directory must exist, as must the parent directory of a custom
destination. The selected McStas or McXtrace installation must provide its
corresponding ``*-pygen`` executable on the system ``PATH``.

.. autofunction:: mcstasscript.mcstas_pygen

.. autofunction:: mcstasscript.mcxtrace_pygen
