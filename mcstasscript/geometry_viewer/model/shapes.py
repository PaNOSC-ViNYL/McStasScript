from __future__ import annotations

from dataclasses import dataclass, field
from abc import ABC, abstractmethod

import numpy as np

from mcstasscript.geometry_viewer.transform import Transform


@dataclass
class Style:
    opacity: float = 1.0
    color: str | None = None
    wireframe: bool = False


@dataclass(kw_only=True)
class Shape(ABC):
    transform: Transform | None = None
    style: Style | None = None


@dataclass
class BoxShape(Shape):
    width: float
    height: float
    depth: float

    def __repr__(self):
        return f"BoxShape w={self.width} h={self.height} d={self.depth}"


@dataclass
class LineSegmentsShape(Shape):
    points: np.ndarray

    def __post_init__(self):
        self.points = np.asarray(self.points, dtype=np.float32)
        if self.points.size == 0:
            raise ValueError("LineSegmentsShape needs at least two points")

    def __repr__(self):
        return f"LineSegmentsShape points={self.points.shape}"


@dataclass
class CircleShape(Shape):
    radius: float
    segments: int = 64

    def __repr__(self):
        return f"CircleShape r={self.radius}"


@dataclass
class ConeShape(Shape):
    radius: float
    height: float
    radial_segments: int = 32

    def __repr__(self):
        return f"ConeShape r={self.radius} h={self.height}"


@dataclass
class CylinderShape(Shape):
    radius: float
    height: float
    radial_segments: int = 32

    def __repr__(self):
        return f"CylinderShape r={self.radius} h={self.height}"


@dataclass
class PolyhedronShape(Shape):
    vertices: np.ndarray
    indices: np.ndarray

    def __post_init__(self):
        self.vertices = np.asarray(self.vertices, dtype=np.float32)
        self.indices = np.asarray(self.indices, dtype=np.uint32)

    def __repr__(self):
        return f"PolyhedronShape vertices={self.vertices.shape} indices={self.indices.shape}"


def triangulate_faces(faces):
    """Convert a list of face dicts with 'face' keys into flat triangle indices."""
    triangles = []
    for face in faces:
        indices = face["face"]
        if len(indices) == 3:
            triangles.append(indices)
        elif len(indices) == 4:
            triangles.append([indices[0], indices[1], indices[2]])
            triangles.append([indices[0], indices[2], indices[3]])
        else:
            raise ValueError(f"Unsupported face with {len(indices)} vertices: {indices}")
    return np.array(triangles, dtype=np.uint32).reshape(-1)
