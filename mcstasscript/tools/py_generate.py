"""Create McStasScript instruments from McStas or McXtrace files.

This module wraps the McStas and McXtrace ``*-pygen`` commands. Each command
generates a Python file with a ``make`` function; this module imports that
file and returns the instrument created by the function.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
from typing import Any, Optional, Union


PathLike = Union[str, os.PathLike]


def _import_python_file(path: Path) -> Any:
    """Import a generated Python file without adding it to ``sys.path``."""
    spec = importlib.util.spec_from_file_location(path.stem, str(path))

    if spec is None or spec.loader is None:
        raise ImportError("Could not import generated file: " + str(path))

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise ImportError(
            "Could not execute generated file: " + str(path) + ": " + str(error)
        ) from error

    return module


def _generated_file_path(input_file: Path,
                         destination: Optional[PathLike]) -> Path:
    """Resolve the output file, accepting a file or an existing directory."""
    if destination is None:
        return input_file.with_name(input_file.stem + "_generated.py")

    destination_path = Path(destination).expanduser().resolve()
    if destination_path.is_dir():
        return destination_path / (input_file.stem + "_generated.py")

    return destination_path


def _generate_instrument(filename: PathLike,
                          destination: Optional[PathLike],
                          input_path: Optional[PathLike],
                          generator: str) -> Any:
    """Generate and return an instrument using the selected pygen command.

    Parameters
    ----------
    filename : str or os.PathLike
        Path to the McStas instrument file.  The file must have an ``.instr``
        suffix and must exist.
    destination : str or os.PathLike, optional
        Path for the generated Python file.  If an existing directory is
        supplied, ``<instrument>_generated.py`` is written there.  By default
        the generated file is placed next to ``filename``.
    input_path : str or os.PathLike, optional
        Directory passed to the generated ``make`` function and consequently
        used as the returned instrument's ``input_path``.  The directory must
        already exist.

    Returns
    -------
    object
        The instrument object returned by the generated Python file's
        ``make`` function.

    Raises
    ------
    FileNotFoundError
        If the input file, output parent, or generated Python file is missing.
    NotADirectoryError
        If ``input_path`` or the output parent is not a directory.
    RuntimeError
        If the selected pygen command cannot be started or exits with an error.
    ImportError
        If the generated file cannot be imported or executed.
    AttributeError
        If the generated file does not define ``make``.
    TypeError
        If ``make`` is present but is not callable.
    """
    input_file = Path(filename).expanduser().resolve()

    if input_file.suffix.lower() != ".instr":
        raise ValueError("Input file must have an .instr suffix: " + str(input_file))
    if not input_file.exists():
        raise FileNotFoundError("Input file does not exist: " + str(input_file))
    if not input_file.is_file():
        raise IsADirectoryError("Input path is not a file: " + str(input_file))

    input_path_value = None
    if input_path is not None:
        input_directory = Path(input_path).expanduser()
        if not input_directory.exists():
            raise FileNotFoundError(
                "input_path does not exist: " + str(input_directory)
            )
        if not input_directory.is_dir():
            raise NotADirectoryError(
                "input_path is not a directory: " + str(input_directory)
            )
        input_path_value = str(input_directory)

    generated_file = _generated_file_path(input_file, destination)
    if not generated_file.parent.exists():
        raise FileNotFoundError(
            "Destination directory does not exist: " + str(generated_file.parent)
        )
    if not generated_file.parent.is_dir():
        raise NotADirectoryError(
            "Destination parent is not a directory: " + str(generated_file.parent)
        )

    command = [
        generator,
        "-o",
        str(generated_file),
        str(input_file),
    ]
    try:
        process = subprocess.run(
            command,
            cwd=str(input_file.parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except OSError as error:
        raise RuntimeError(
            "Could not run "
            + generator
            + ". Ensure it is installed and available on PATH."
        ) from error

    output = process.stdout or ""
    if process.returncode != 0:
        raise RuntimeError(
            generator
            + " failed with return code "
            + str(process.returncode)
            + "\n\nCommand:\n"
            + " ".join(command)
            + "\n\nOutput:\n"
            + output
        )

    if not generated_file.exists():
        raise FileNotFoundError(
            generator
            + " did not create the expected file: "
            + str(generated_file)
            + "\n\nCommand output:\n"
            + output
        )
    if not generated_file.is_file():
        raise IsADirectoryError(
            "Generated path is not a file: " + str(generated_file)
        )

    module = _import_python_file(generated_file)
    if not hasattr(module, "make"):
        raise AttributeError(
            str(generated_file) + " does not define a make() function"
        )

    make = module.make
    if not callable(make):
        raise TypeError(str(generated_file) + ".make exists but is not callable")

    if input_path_value is None:
        return make()
    return make(input_path=input_path_value)


def mcstas_pygen(filename: PathLike,
                 destination: Optional[PathLike] = None,
                 input_path: Optional[PathLike] = None) -> Any:
    """Generate and return a McStas instrument from a ``.instr`` file.

    This uses the ``mcstas-pygen`` executable and returns the McStas
    instrument generated by that command.

    ``destination`` selects the generated Python file, or an existing
    directory in which ``<instrument>_generated.py`` is written. ``input_path``
    is passed to the generated ``make`` function and must name an existing
    directory.
    """
    return _generate_instrument(
        filename,
        destination=destination,
        input_path=input_path,
        generator="mcstas-pygen",
    )


def mcxtrace_pygen(filename: PathLike,
                   destination: Optional[PathLike] = None,
                   input_path: Optional[PathLike] = None) -> Any:
    """Generate and return a McXtrace instrument from a ``.instr`` file.

    This uses the ``mcxtrace-pygen`` executable and returns the McXtrace
    instrument generated by that command.

    ``destination`` selects the generated Python file, or an existing
    directory in which ``<instrument>_generated.py`` is written. ``input_path``
    is passed to the generated ``make`` function and must name an existing
    directory.
    """
    return _generate_instrument(
        filename,
        destination=destination,
        input_path=input_path,
        generator="mcxtrace-pygen",
    )


__all__ = ["mcstas_pygen", "mcxtrace_pygen"]
