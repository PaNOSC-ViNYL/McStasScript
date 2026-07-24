from mcstasscript.geometry_viewer.api import view, view_with_json, view_with_guess, view_with_analysis
from mcstasscript.geometry_viewer.model import (
    Shape, BoxShape, CylinderShape, ConeShape, CircleShape,
    LineSegmentsShape, PolyhedronShape, SphereShape, Style,
    ComponentModel, InstrumentModel, Bounds,
)
from mcstasscript.geometry_viewer.renderer import (
    RendererBackend, MatplotlibRenderer,
)
from mcstasscript.geometry_viewer.transform import (
    Transform, euler_to_rotation_matrix, resolve_transforms, TransformResolutionError,
)
from mcstasscript.geometry_viewer.mcdisplay import (
    McdisplayError,
    generate_json,
    run_mcdisplay,
    display_mcdisplay_html,
)
from mcstasscript.geometry_viewer.rules import GeometryRule, GeometryRuleRegistry
from mcstasscript.geometry_viewer.expression import safe_eval, UnsafeExpressionError


def __getattr__(name):
    if name == "PyThreejsRenderer":
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        return PyThreejsRenderer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "view", "view_with_json", "view_with_guess", "view_with_analysis",
    "Shape", "BoxShape", "CylinderShape", "ConeShape", "CircleShape",
    "LineSegmentsShape", "PolyhedronShape", "SphereShape", "Style",
    "ComponentModel", "InstrumentModel",
    "Bounds",
    "RendererBackend", "PyThreejsRenderer", "MatplotlibRenderer",
    "Transform",
    "generate_json", "run_mcdisplay", "display_mcdisplay_html", "McdisplayError",
    "GeometryRule", "GeometryRuleRegistry",
    "safe_eval", "UnsafeExpressionError",
    "euler_to_rotation_matrix", "resolve_transforms", "TransformResolutionError",
]
