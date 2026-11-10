from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mcstasscript.geometry_viewer.model.shapes import (
    BoxShape,
    CircleShape,
    ConeShape,
    CylinderShape,
    LineSegmentsShape,
    PolyhedronShape,
    Shape,
    SphereShape,
)


@dataclass
class Bounds:
    """Axis-aligned bounds in a single coordinate system."""

    minimum: np.ndarray | None = None
    maximum: np.ndarray | None = None

    @classmethod
    def from_points(cls, points: np.ndarray) -> "Bounds":
        points = np.asarray(points, dtype=float)
        if points.size == 0:
            return cls()
        if points.ndim == 1 and points.shape == (3,):
            points = points.reshape(1, 3)
        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError("Bounds points must have shape (N, 3)")
        return cls(points.min(axis=0), points.max(axis=0))

    @property
    def is_empty(self) -> bool:
        return self.minimum is None or self.maximum is None

    @property
    def center(self) -> np.ndarray:
        if self.is_empty:
            return np.zeros(3, dtype=float)
        return (self.minimum + self.maximum) / 2.0

    @property
    def extents(self) -> np.ndarray:
        if self.is_empty:
            return np.zeros(3, dtype=float)
        return self.maximum - self.minimum

    @property
    def radius(self) -> float:
        """Radius of a sphere enclosing this axis-aligned box."""
        return float(np.linalg.norm(self.extents) / 2.0)

    def include(self, points: np.ndarray) -> None:
        other = Bounds.from_points(points)
        if other.is_empty:
            return
        if self.is_empty:
            self.minimum = other.minimum.copy()
            self.maximum = other.maximum.copy()
            return
        self.minimum = np.minimum(self.minimum, other.minimum)
        self.maximum = np.maximum(self.maximum, other.maximum)


def _box_points(minimum, maximum) -> np.ndarray:
    x0, y0, z0 = minimum
    x1, y1, z1 = maximum
    return np.array([
        [x0, y0, z0], [x1, y0, z0], [x0, y1, z0], [x1, y1, z0],
        [x0, y0, z1], [x1, y0, z1], [x0, y1, z1], [x1, y1, z1],
    ], dtype=float)


def local_bound_points(shape: Shape) -> np.ndarray:
    """Return conservative local-space points enclosing a shape."""
    if isinstance(shape, BoxShape):
        half = np.array([shape.width, shape.height, shape.depth], dtype=float) / 2.0
        return _box_points(-half, half)
    if isinstance(shape, LineSegmentsShape):
        return np.asarray(shape.points, dtype=float)
    if isinstance(shape, PolyhedronShape):
        return np.asarray(shape.vertices, dtype=float)
    if isinstance(shape, (CylinderShape, ConeShape)):
        radius = float(shape.radius)
        half_height = float(shape.height) / 2.0
        return _box_points(
            np.array([-radius, -half_height, -radius]),
            np.array([radius, half_height, radius]),
        )
    if isinstance(shape, (CircleShape, SphereShape)):
        radius = float(shape.radius)
        return _box_points(
            np.array([-radius, -radius, -radius]),
            np.array([radius, radius, radius]),
        )
    raise TypeError(f"Unknown shape type: {type(shape).__name__}")


def shape_bounds(shape: Shape) -> Bounds:
    points = local_bound_points(shape)
    if shape.transform is not None:
        points = shape.transform.transform_points(points)
    return Bounds.from_points(points)


def component_bounds(shapes: list[Shape]) -> Bounds:
    bounds = Bounds()
    for shape in shapes:
        shape_bound = shape_bounds(shape)
        if not shape_bound.is_empty:
            bounds.include(np.vstack((shape_bound.minimum, shape_bound.maximum)))
    return bounds
