"""Classical-syntax fluent methods on the component object.

Each method delegates to an existing McStasScript method on
``mcstasscript.helper.mcstas_objects.Component`` and returns ``self`` so
that component placement can be chained in one expression that reads like
a .instr TRACE block.
"""
from __future__ import annotations

_INSTALLED_ON: set = set()  # component classes we have already patched


def install_on(component_cls):
    """Idempotently add classical uppercase chain methods to *component_cls*."""
    if component_cls in _INSTALLED_ON:
        return
    _INSTALLED_ON.add(component_cls)

    def AT(self, position, RELATIVE=None):
        if RELATIVE is None:
            self.set_AT(position)
        else:
            self.set_AT(position, RELATIVE=str(RELATIVE))
        return self

    def ROTATED(self, rotation, RELATIVE=None):
        if RELATIVE is None:
            self.set_ROTATED(rotation)
        else:
            self.set_ROTATED(rotation, RELATIVE=str(RELATIVE))
        return self

    def RELATIVE(self, reference):
        self.set_RELATIVE(str(reference))
        return self

    def WHEN(self, expr):
        self.set_WHEN(expr)
        return self

    def GROUP(self, name):
        self.set_GROUP(name)
        return self

    def EXTEND(self, code):
        for line in _iter_lines(code):
            self.append_EXTEND(line)
        return self

    def SPLIT(self, n):
        self.set_SPLIT(n)
        return self

    def JUMP(self, target, WHEN=None, ITERATE=None):
        # Real set_JUMP takes a single string; assemble it here so the
        # classical WHEN/ITERATE clauses can be written as Python kwargs.
        parts = []
        if ITERATE is not None:
            parts.append("ITERATE " + str(ITERATE))
        else:
            parts.append(str(target))
        if WHEN is not None:
            parts.append("WHEN (" + str(WHEN) + ")")
        self.set_JUMP(" ".join(parts))
        return self

    def COMMENT(self, text):
        self.set_comment(text)
        return self

    def C_CODE_BEFORE(self, code):
        self.set_c_code_before(code)
        return self

    def C_CODE_AFTER(self, code):
        self.set_c_code_after(code)
        return self

    component_cls.AT = AT
    component_cls.ROTATED = ROTATED
    component_cls.RELATIVE = RELATIVE
    component_cls.WHEN = WHEN
    component_cls.GROUP = GROUP
    component_cls.EXTEND = EXTEND
    component_cls.SPLIT = SPLIT
    component_cls.JUMP = JUMP
    component_cls.COMMENT = COMMENT
    component_cls.C_CODE_BEFORE = C_CODE_BEFORE
    component_cls.C_CODE_AFTER = C_CODE_AFTER


def _iter_lines(code):
    if isinstance(code, (list, tuple)):
        for line in code:
            yield line
        return
    for raw in str(code).splitlines():
        line = raw.strip()
        if line:
            yield line
