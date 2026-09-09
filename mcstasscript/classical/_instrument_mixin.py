"""Classical-syntax methods on the instrument object.

Every method here is a pure delegation to existing McStasScript methods on
``mcstasscript.interface.instr.McCode_instr``; nothing is renamed or
overridden.
"""
from __future__ import annotations

from . import _component_mixin


# Matches add_component's / copy_component's placement kwargs verbatim.
_PLACEMENT_KEYS = {
    "AT", "AT_RELATIVE", "ROTATED", "ROTATED_RELATIVE",
    "RELATIVE", "WHEN", "GROUP", "SPLIT", "EXTEND", "JUMP",
    "before", "after", "comment",
    "c_code_before", "c_code_after",
}


def _looks_like_sentinel(obj):
    return getattr(obj, "_mcstas_sentinel", False)


def _normalise_refs(placement):
    for key in ("RELATIVE", "AT_RELATIVE", "ROTATED_RELATIVE"):
        if key in placement and placement[key] is not None \
                and not isinstance(placement[key], str) \
                and _looks_like_sentinel(placement[key]):
            placement[key] = str(placement[key])


def _COMPONENT(self, name, component_name=None, **kwargs):
    """Classical-syntax alias for :meth:`McCode_instr.add_component`.

    Non-placement kwargs are forwarded to the returned component's
    ``set_parameters`` so a COMPONENT call can carry its constructor
    parameters on the same line, mirroring::

        COMPONENT name = Type(p1=v1, p2=v2) AT (...) ROTATED (...) ...

    Placement kwargs (AT, ROTATED, RELATIVE, WHEN, GROUP, SPLIT, EXTEND,
    JUMP, comment, c_code_before, c_code_after, before, after) are passed
    straight through to ``add_component``.
    """
    placement = {k: kwargs.pop(k) for k in list(kwargs) if k in _PLACEMENT_KEYS}
    _normalise_refs(placement)
    comp = self.add_component(name, component_name, **placement)
    _component_mixin.install_on(type(comp))
    if kwargs:
        comp.set_parameters(**kwargs)
    return comp


_INSTALLED_ON: set = set()


def install_on(instr_cls):
    if instr_cls in _INSTALLED_ON:
        return
    _INSTALLED_ON.add(instr_cls)
    instr_cls.COMPONENT = _COMPONENT


def enable(McCode_instr_cls, McStas_instr_cls=None, McXtrace_instr_cls=None):
    install_on(McCode_instr_cls)
    if McStas_instr_cls is not None and McStas_instr_cls is not McCode_instr_cls:
        install_on(McStas_instr_cls)
    if McXtrace_instr_cls is not None and McXtrace_instr_cls is not McCode_instr_cls:
        install_on(McXtrace_instr_cls)
