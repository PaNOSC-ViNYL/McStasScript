from __future__ import annotations

import math
import re
import operator
from typing import Any

import numpy as np


# Whitelisted math functions available in safe expression evaluation
SAFE_MATH_FUNCTIONS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "sqrt": math.sqrt,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "abs": abs,
    "floor": math.floor,
    "ceil": math.ceil,
    "fmod": math.fmod,
    "pow": pow,
    "min": min,
    "max": max,
    "round": round,
}

# Built-in constants
SAFE_CONSTANTS = {
    "PI": math.pi,
    "DEG2RAD": math.pi / 180.0,
    "RAD2DEG": 180.0 / math.pi,
}

# Token pattern for the expression parser
_NUMBER = r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
_IDENT = r"[A-Za-z_]\w*"
_TOKEN_RE = re.compile(
    rf"(?P<number>{_NUMBER})"
    rf"|(?P<ident>{_IDENT})"
    rf"|(?P<op>[+\-*/%(){{}}<>=!,])"
    rf"|(?P<ws>\s+)"
)


class UnsafeExpressionError(ValueError):
    """Raised when an expression contains unsafe constructs."""


def safe_eval(expression: str, variables: dict[str, float] | None = None) -> float:
    """Safely evaluate a numeric expression.

    Supports:
    - Numeric literals (int, float, scientific notation)
    - Instrument variables (resolved from *variables* dict)
    - Built-in constants: PI, DEG2RAD, RAD2DEG
    - Whitelisted math functions: sin, cos, tan, sqrt, exp, log, abs, etc.
    - Arithmetic operators: +, -, *, /, %, parentheses; use pow() for powers

    Parameters
    ----------
    expression : str
        The expression string to evaluate.
    variables : dict, optional
        Mapping of variable names to numeric values.

    Returns
    -------
    float
        The evaluated numeric result.

    Raises
    ------
    UnsafeExpressionError
        If the expression contains unresolved variables or unsafe constructs.
    ValueError
        If the expression is empty or cannot be parsed.
    """
    if expression is None:
        raise ValueError("Expression is None")

    expr = str(expression).strip()
    if not expr:
        raise ValueError("Empty expression")

    if "^" in expr:
        raise UnsafeExpressionError(
            "The '^' operator is not supported in McStas expressions; use pow() for exponentiation."
        )

    # Try direct numeric conversion first
    try:
        return float(expr)
    except ValueError:
        pass

    # Build evaluation namespace
    namespace = dict(SAFE_CONSTANTS)
    namespace.update(SAFE_MATH_FUNCTIONS)
    if variables:
        for k, v in variables.items():
            try:
                namespace[k] = float(v)
            except (TypeError, ValueError):
                pass  # Skip non-numeric variables

    # Tokenize and validate
    tokens = list(_TOKEN_RE.finditer(expr))
    if not tokens:
        raise UnsafeExpressionError(f"Cannot parse expression: {expr!r}")

    # Check for unresolved identifiers
    remaining = expr
    for m in _TOKEN_RE.finditer(expr):
        if m.group("ident"):
            name = m.group("ident")
            if name not in namespace:
                raise UnsafeExpressionError(
                    f"Unresolved or unsafe identifier '{name}' in expression: {expr!r}"
                )

    # Use Python's eval with restricted namespace
    try:
        result = eval(expr, {"__builtins__": {}}, namespace)
        return float(result)
    except Exception as exc:
        raise UnsafeExpressionError(
            f"Failed to evaluate expression: {expr!r} — {exc}"
        ) from exc


def resolve_at_rotated_values(
    data: list,
    variables: dict[str, float] | None = None,
) -> list[float]:
    """Resolve AT or ROTATED data list to numeric values.

    Each element may be a number, a string variable name, or an expression.

    Parameters
    ----------
    data : list
        List of 3 elements (e.g., AT_data or ROTATED_data).
    variables : dict, optional
        Variable name -> value mapping.

    Returns
    -------
    list of float
        Resolved numeric values.
    """
    result = []
    for elem in data:
        if isinstance(elem, (int, float)):
            result.append(float(elem))
        elif isinstance(elem, str):
            result.append(safe_eval(elem, variables))
        else:
            result.append(float(elem))
    return result
