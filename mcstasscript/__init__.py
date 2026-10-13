"""Public package interface.

The public objects are imported on first use rather than during package
initialisation.  Importing plotting and scientific Python stacks can load
native extensions and select a Matplotlib backend, neither of which is
necessary for checking the package version or importing it in a notebook.
"""

from importlib import import_module

from ._version import __version__

_LAZY_IMPORTS = {
    "McStas_instr": ("mcstasscript.interface.instr", "McStas_instr"),
    "McXtrace_instr": ("mcstasscript.interface.instr", "McXtrace_instr"),
    "load_data": ("mcstasscript.interface.functions", "load_data"),
    "load_metadata": ("mcstasscript.interface.functions", "load_metadata"),
    "load_monitor": ("mcstasscript.interface.functions", "load_monitor"),
    "name_plot_options": ("mcstasscript.interface.functions", "name_plot_options"),
    "name_search": ("mcstasscript.interface.functions", "name_search"),
    "Configurator": ("mcstasscript.interface.functions", "Configurator"),
    "make_animation": ("mcstasscript.interface.plotter", "make_animation"),
    "make_plot": ("mcstasscript.interface.plotter", "make_plot"),
    "make_sub_plot": ("mcstasscript.interface.plotter", "make_sub_plot"),
    "McStas_file": ("mcstasscript.interface.reader", "McStas_file"),
    "Cryostat": ("mcstasscript.tools.cryostat_builder", "Cryostat"),
    "has_component": ("mcstasscript.tools.instrument_checker", "has_component"),
    "has_parameter": ("mcstasscript.tools.instrument_checker", "has_parameter"),
    "all_parameters_set": ("mcstasscript.tools.instrument_checker", "all_parameters_set"),
    "mcstas_pygen": ("mcstasscript.tools.py_generate", "mcstas_pygen"),
    "mcxtrace_pygen": ("mcstasscript.tools.py_generate", "mcxtrace_pygen"),
    "Diagnostics": (
        "mcstasscript.instrument_diagnostics.beam_diagnostics",
        "BeamDiagnostics",
    ),
}
_LAZY_MODULES = {
    name: f"mcstasscript.{name}"
    for name in (
        "data",
        "helper",
        "interface",
        "instr_reader",
        "instrument_diagram",
        "instrument_diagnostics",
        "tools",
    )
}

__all__ = ["__version__", *_LAZY_IMPORTS]


def __getattr__(name):
    """Load a public object when it is first accessed."""
    if name in _LAZY_MODULES:
        module = import_module(_LAZY_MODULES[name])
        globals()[name] = module
        return module

    try:
        module_name, attribute_name = _LAZY_IMPORTS[name]
    except KeyError as error:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from error

    module = import_module(module_name)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__():
    """Include lazy public objects in interactive completion."""
    return sorted(set(globals()) | set(__all__) | set(_LAZY_MODULES))
