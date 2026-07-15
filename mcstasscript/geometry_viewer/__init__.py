from mcstasscript.geometry_viewer.api import view, view_with_json, view_with_guess
from mcstasscript.geometry_viewer.model import (
    Shape, BoxShape, CylinderShape, ConeShape, CircleShape,
    LineSegmentsShape, PolyhedronShape, Style,
    ComponentModel, InstrumentModel,
)
from mcstasscript.geometry_viewer.renderer import (
    RendererBackend, MatplotlibRenderer,
)
from mcstasscript.geometry_viewer.transform import Transform
from mcstasscript.geometry_viewer.mcdisplay import (
    generate_json,
    run_mcdisplay,
    display_mcdisplay_html,
)


def __getattr__(name):
    if name == "PyThreejsRenderer":
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        return PyThreejsRenderer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "view", "view_with_json", "view_with_guess",
    "Shape", "BoxShape", "CylinderShape", "ConeShape", "CircleShape",
    "LineSegmentsShape", "PolyhedronShape", "Style",
    "ComponentModel", "InstrumentModel",
    "RendererBackend", "PyThreejsRenderer", "MatplotlibRenderer",
    "Transform",
    "generate_json", "run_mcdisplay", "display_mcdisplay_html",
]
