"""Sentinel singletons for the classical RELATIVE keywords.

Using these lets Python code read::

    .AT([0, 0, 2], RELATIVE=PREVIOUS)

which matches the classical .instr line::

    AT (0, 0, 2) RELATIVE PREVIOUS

exactly, instead of the stringly-typed ``RELATIVE="PREVIOUS"`` (where
typos are silently treated as a missing reference -> ABSOLUTE placement).
"""
from __future__ import annotations


class _Sentinel:
    _mcstas_sentinel = True

    def __init__(self, name):
        self._name = name

    def __str__(self):
        return self._name

    def __repr__(self):
        return "<mcstasscript." + self._name + ">"

    def __reduce__(self):
        # Ensure pickling re-uses the singleton.
        return (_resolve, (self._name,))


def _resolve(name):
    return _SINGLETONS[name]


PREVIOUS = _Sentinel("PREVIOUS")
ABSOLUTE = _Sentinel("ABSOLUTE")

_SINGLETONS = {
    "PREVIOUS": PREVIOUS,
    "ABSOLUTE": ABSOLUTE,
}


__all__ = ["PREVIOUS", "ABSOLUTE"]
