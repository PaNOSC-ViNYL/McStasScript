from __future__ import annotations

from mcstasscript.geometry_viewer.model.shapes import (
    BoxShape,
    CircleShape,
    ConeShape,
    CylinderShape,
    LineSegmentsShape,
    PolyhedronShape,
    Shape,
    SphereShape,
    Style,
)


def _opacity_for_size(size: float) -> float:
    if size <= 0.05:
        return 0.9
    if size <= 0.5:
        return 0.85
    if size <= 1.5:
        return 0.65
    return 0.4


def intrinsic_size(shape: Shape) -> float:
    """Return a rotation-independent size for visual style decisions."""
    if isinstance(shape, BoxShape):
        return max(shape.width, shape.height, shape.depth)
    if isinstance(shape, (CylinderShape, ConeShape)):
        return max(2 * shape.radius, shape.height)
    if isinstance(shape, (CircleShape, SphereShape)):
        return 2 * shape.radius
    if isinstance(shape, (LineSegmentsShape, PolyhedronShape)):
        from mcstasscript.geometry_viewer.model.bounds import local_bound_points
        points = local_bound_points(shape)
        return float((points.max(axis=0) - points.min(axis=0)).max())
    raise TypeError(f"Unknown shape type: {type(shape).__name__}")


def default_style_for_shape(shape: Shape) -> Style:
    """Build the model-owned default style for an unstyled shape."""
    if isinstance(shape, LineSegmentsShape):
        return Style()
    if isinstance(shape, BoxShape):
        # Preserve the established box appearance while making very large
        # boxes transparent like the other solid primitives.
        opacity = 0.8 if intrinsic_size(shape) <= 2.0 else _opacity_for_size(intrinsic_size(shape))
        return Style(opacity=opacity)
    if isinstance(shape, CircleShape):
        size = intrinsic_size(shape)
        opacity = (0.9 if size <= 0.1 else 0.7 if size <= 1.0
                   else 0.4 if size <= 3.0 else 0.2)
        return Style(opacity=opacity)
    if isinstance(shape, (CylinderShape, SphereShape)):
        return Style(opacity=_opacity_for_size(intrinsic_size(shape)))
    if isinstance(shape, (ConeShape, PolyhedronShape)):
        return Style(opacity=0.8)
    raise TypeError(f"Unknown shape type: {type(shape).__name__}")
