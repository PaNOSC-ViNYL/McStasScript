"""Classical McStas-syntax sugar for McStasScript (opt-in, additive).

This subpackage adds method aliases that borrow the keyword names from
classical .instr files (COMPONENT, AT, ROTATED, WHEN, GROUP, EXTEND, ...).
Nothing here changes existing behaviour; the top-level ``mcstasscript``
package auto-enables it via :func:`enable_classical_api`.
"""
from __future__ import annotations

from . import _component_mixin, _instrument_mixin
from ._sentinels import PREVIOUS, ABSOLUTE


def enable_classical_api():
    """Idempotently install the classical-syntax methods on the standard
    instrument classes and on the Component class."""
    from mcstasscript.interface.instr import McCode_instr, McStas_instr, McXtrace_instr
    from mcstasscript.helper.mcstas_objects import Component

    _instrument_mixin.enable(
        McCode_instr,
        McStas_instr_cls=McStas_instr,
        McXtrace_instr_cls=McXtrace_instr,
    )
    # Eager install on the component base class so users can use the fluent
    # chain even if they got their component via the raw add_component call.
    _component_mixin.install_on(Component)


__all__ = ["enable_classical_api", "PREVIOUS", "ABSOLUTE"]
