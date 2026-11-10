from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable, Any


@dataclass
class GeometryRule:
    """Rule that determines whether a component matches a geometry factory.

    Attributes
    ----------
    component_names : tuple of str, optional
        If set, rule only applies to components whose component_name is in this set.
    must_have : dict[str, bool]
        Parameter names that must (True) or must not (False) exist in the
        component's parameter_names.
    must_not_have : dict[str, bool]
        Alias for must_have with False values; kept for clarity.
    must_be_set : dict[str, bool]
        Parameter names that must (True) or must not (False) have a non-default
        value on the component instance.
    must_not_be_set : dict[str, bool]
        Alias for must_be_set with False values; kept for clarity.
    priority : int
        Lower value = higher priority.  Rules are matched in priority order.
    factory : callable
        Called as ``factory(comp, instr_parameters) -> Shape | None``.
        ``comp`` is the Component (or mock) object, ``instr_parameters`` is the
        dict of instrument-level parameter values (may be None).
    require_empty_params : bool
        If True, the rule only matches components with no declared parameters.
    """

    component_names: tuple[str, ...] = ()
    must_have: Any = field(default_factory=dict)
    must_not_have: Any = field(default_factory=dict)
    must_be_set: Any = field(default_factory=dict)
    must_not_be_set: Any = field(default_factory=dict)
    priority: int = 100
    factory: Callable | None = None
    require_empty_params: bool = False

    def matches(self, comp: Any) -> bool:
        """Return True if *comp* satisfies all conditions of this rule."""
        parameter_names = getattr(comp, "parameter_names", []) or []

        if self.require_empty_params and len(parameter_names) > 0:
            return False

        if self.component_names:
            comp_name = getattr(comp, "component_name", None)
            if comp_name not in self.component_names:
                return False

        parameter_defaults = getattr(comp, "parameter_defaults", {}) or {}

        def conditions(values, default):
            if isinstance(values, dict):
                return values.items()
            return ((value, default) for value in values)

        have_conditions = list(conditions(self.must_have, True))
        have_conditions.extend(conditions(self.must_not_have, False))
        for par, required in have_conditions:
            has = par in parameter_names
            if required and not has:
                return False
            if not required and has:
                return False

        # must_be_set / must_not_be_set
        # Only check parameters that are actually declared on the component.
        # For parameters not in parameter_names, is_set is always False.
        set_conditions = list(conditions(self.must_be_set, True))
        set_conditions.extend(conditions(self.must_not_be_set, False))
        for par, required in set_conditions:
            if par not in parameter_names:
                # Parameter not declared on this component -> not set
                is_set = False
            else:
                val = getattr(comp, par, None)
                default = parameter_defaults.get(par)
                is_set = val is not None and val != default
                if is_set:
                    try:
                        is_set = float(val) != float(default)
                    except (TypeError, ValueError):
                        pass
            if required and not is_set:
                return False
            if not required and is_set:
                return False

        return True


class GeometryRuleRegistry:
    """Ordered registry of GeometryRule instances.

    Rules are stored in priority order (lowest number first).
    """

    def __init__(self):
        self._rules: list[GeometryRule] = []

    def register(self, rule: GeometryRule) -> None:
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority)

    add = register

    def match(self, comp: Any) -> GeometryRule | None:
        """Return the first matching rule, or None."""
        for rule in self._rules:
            if rule.matches(comp):
                return rule
        return None

    def guess(self, comp: Any, instr_parameters: dict | None = None):
        """Create geometry using the first matching rule, if any."""
        rule = self.match(comp)
        if rule is None or rule.factory is None:
            return None
        return rule.factory(comp, instr_parameters)

    @property
    def rules(self) -> list[GeometryRule]:
        return list(self._rules)
