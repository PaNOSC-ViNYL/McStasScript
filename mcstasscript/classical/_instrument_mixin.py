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


import re


_TYPE_HEAD_RE = re.compile(
    r"^(?P<type>(?:unsigned\s+|signed\s+)?\w[\w\s\*]*?)\s+(?=[A-Za-z_])"
)


def _split_block(block):
    """Yield non-empty, stripped lines from a triple-quoted C block."""
    if isinstance(block, (list, tuple)):
        for line in block:
            if str(line).strip():
                yield str(line)
        return
    for raw in str(block).splitlines():
        line = raw.strip()
        if line:
            yield line


def _coerce_scalar(text):
    """Turn the RHS of a declaration back into a Python scalar when safe."""
    try:
        if "." in text or "e" in text or "E" in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def _split_top_commas(text):
    depth = 0
    last = 0
    for i, ch in enumerate(text):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            yield text[last:i]
            last = i + 1
    yield text[last:]


def _expand_compound_decl(raw):
    """Expand ``double a, b = 3, c;`` into ``[(type, name, value), ...]``.

    Returns None if the line isn't a plain scalar declaration (contains
    parens, brackets, or starts with a preprocessor directive).
    """
    if "(" in raw or "[" in raw or raw.startswith("#"):
        return None
    stripped = raw.rstrip(";").strip()
    m = _TYPE_HEAD_RE.match(stripped)
    if not m:
        return None
    vartype = m.group("type").strip()
    rest = stripped[m.end():].strip()
    items = []
    for chunk in _split_top_commas(rest):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" in chunk:
            name, _, val = chunk.partition("=")
            items.append((vartype, name.strip(), _coerce_scalar(val.strip())))
        else:
            items.append((vartype, chunk, None))
    return items or None


def _declare_block(self, block, uservars=False):
    for raw in _split_block(block):
        stmts = _expand_compound_decl(raw)
        if stmts is not None:
            for vartype, name, value in stmts:
                if uservars:
                    # McStas 3.x UserVars are not allowed to carry a value.
                    self.add_user_var(vartype, name)
                elif value is None:
                    self.add_declare_var(vartype, name)
                else:
                    self.add_declare_var(vartype, name, value=value)
        else:
            # Complex declaration (arrays, function pointers, preprocessor
            # directives, ...): pass through verbatim.
            self.append_declare(raw)


def _DECLARE(self, block):
    _declare_block(self, block, uservars=False)
    return self


def _USERVARS(self, block):
    _declare_block(self, block, uservars=True)
    return self


def _INITIALIZE(self, block):
    for line in _split_block(block):
        self.append_initialize(line)
    return self


def _FINALLY(self, block):
    for line in _split_block(block):
        self.append_finally(line)
    return self


_INSTALLED_ON: set = set()


def install_on(instr_cls):
    if instr_cls in _INSTALLED_ON:
        return
    _INSTALLED_ON.add(instr_cls)
    instr_cls.COMPONENT = _COMPONENT
    instr_cls.DECLARE = _DECLARE
    instr_cls.USERVARS = _USERVARS
    instr_cls.INITIALIZE = _INITIALIZE
    instr_cls.FINALLY = _FINALLY


def enable(McCode_instr_cls, McStas_instr_cls=None, McXtrace_instr_cls=None):
    install_on(McCode_instr_cls)
    if McStas_instr_cls is not None and McStas_instr_cls is not McCode_instr_cls:
        install_on(McStas_instr_cls)
    if McXtrace_instr_cls is not None and McXtrace_instr_cls is not McCode_instr_cls:
        install_on(McXtrace_instr_cls)
