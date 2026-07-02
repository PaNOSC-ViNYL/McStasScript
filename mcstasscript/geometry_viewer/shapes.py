import json
from dataclasses import dataclass
from abc import ABC, abstractmethod

import numpy as np
import pythreejs as p3

from mcstasscript.geometry_viewer.helpers import Transform
from mcstasscript.geometry_viewer.helpers import quaternion_from_vectors
from mcstasscript.geometry_viewer.helpers import quaternion_from_rotation_matrix

@dataclass
class Shape(ABC):
    transform: Transform | None = None

    @abstractmethod
    def make_geometry(self):
        pass

    def material_kwargs(self):
        return {}

    def make_mesh(self, material_library):
        geometry = self.make_geometry()

        material = material_library.get_material(**self.material_kwargs())
        """
        material_kwargs = self.material_kwargs()
        if "material_class" in material_kwargs:
            cls = material_kwargs["material_class"]
            del material_kwargs["material_class"]
        else:
            cls = p3.MeshBasicMaterial

        material = cls(**material_kwargs)
        """


        mesh = p3.Mesh(
            geometry=geometry,
            material=material,
        )

        if self.transform is not None:
            self.transform.apply_to(mesh)

        return mesh

    def __repr__(self):
        return "BaseShape"


@dataclass
class BoxShape(Shape):
    width: float | None = None
    height: float | None = None
    depth: float | None = None

    def material_kwargs(self):
        return dict(material_class=p3.MeshLambertMaterial,
                    transparent=True,
                    opacity=0.8,
                    depthWrite=False,
                    side="DoubleSide")

    def make_geometry(self):
        return p3.BoxGeometry(
            width=self.width,
            height=self.height,
            depth=self.depth,
        )

    def __repr__(self):
        return f"BoxShape w{self.width} h{self.height} d{self.depth}"


@dataclass
class LineShape(Shape):
    points: np.array | None = None

    def make_geometry(self):
        return p3.BufferGeometry(
            attributes={
                "position": p3.BufferAttribute(self.points)
            }
        )

    def material_kwargs(self):
        return dict(material_class=p3.LineBasicMaterial)

    def make_mesh(self, material_library):
        geometry = self.make_geometry()

        material = material_library.get_material(**self.material_kwargs())

        line = p3.Line(geometry=geometry, material=material)

        if self.transform is not None:
            self.transform.apply_to(line)

        return line

    def __repr__(self):
        return f"LineShape {self.points}"


@dataclass
class LineSegmentsShape(Shape):
    points: np.ndarray | None = None

    def make_geometry(self):
        points = np.asarray(self.points, dtype=np.float32)

        if len(points) < 2:
            raise ValueError("LineSegmentsShape needs at least two points")

        return p3.BufferGeometry(
            attributes={
                "position": p3.BufferAttribute(points)
            }
        )

    def material_kwargs(self):
        return dict(material_class=p3.LineBasicMaterial)

    def make_mesh(self, material_library):
        geometry = self.make_geometry()
        material = material_library.get_material(**self.material_kwargs())

        line = p3.LineSegments(
            geometry=geometry,
            material=material,
        )

        if self.transform is not None:
            self.transform.apply_to(line)

        return line

    def __repr__(self):
        return f"LineSegmentShape {self.points}"


@dataclass
class CircleShape(Shape):
    radius: float | None = None
    segments: int | None = None

    def material_kwargs(self):
        if self.radius <= 0.05:
            opacity = 0.9
        elif self.radius <= 0.5:
            opacity = 0.85
        elif self.radius <= 1.5:
            opacity = 0.65
        else:
            opacity = 0.4

        return dict(material_class=p3.MeshLambertMaterial,
                    transparent=True,
                    opacity=0.8,
                    depthWrite=False,
                    side="DoubleSide")

    def make_geometry(self):
        return p3.CircleGeometry(
            radius=self.radius,
            segments=self.segments,
        )

    def __repr__(self):
        return f"CylinderShape r{self.radius} h{self.height}"

@dataclass
class ConeShape(Shape):
    radius: float | None = None
    height: float | None = None
    radial_segments: int | None = None

    def material_kwargs(self):
        return dict(material_class=p3.MeshLambertMaterial,
                    transparent=True,
                    opacity=0.80,
                    depthWrite=True,
                    side="DoubleSide")

    def make_geometry(self):
        return p3.CylinderGeometry(
            radiusTop=0,
            radiusBottom=self.radius,
            height=self.height,
            radialSegments=self.radial_segments,
        )

    def __repr__(self):
        return f"ConeShape r{self.radius} h{self.height}"


@dataclass
class CylinderShape(Shape):
    radius: float | None = None
    height: float | None = None
    radial_segments: int | None = None

    def material_kwargs(self):
        # large cylinders more transparent
        largest_dim = max(2*self.radius, self.height)

        if largest_dim <= 0.05:
            opacity = 0.9
        elif largest_dim <= 0.5:
            opacity = 0.85
        elif largest_dim <= 1.5:
            opacity = 0.65
        else:
            opacity = 0.4

        return dict(material_class=p3.MeshLambertMaterial,
                    transparent=True,
                    opacity=opacity,
                    depthWrite=True,
                    side="DoubleSide")

    def make_geometry(self):
        return p3.CylinderGeometry(
            radiusTop=self.radius,
            radiusBottom=self.radius,
            height=self.height,
            radialSegments=self.radial_segments,
        )

    def __repr__(self):
        return f"CylinderShape r{self.radius} h{self.height}"


def triangulate_faces(faces):
    triangles = []

    for face in faces:
        indices = face["face"]

        if len(indices) == 3:
            triangles.append(indices)

        elif len(indices) == 4:
            triangles.append([indices[0], indices[1], indices[2]])
            triangles.append([indices[0], indices[2], indices[3]])

        else:
            raise ValueError(
                f"Unsupported face with {len(indices)} vertices: {indices}"
            )

    return np.array(triangles, dtype=np.uint32).reshape(-1)


@dataclass
class PolyhedronShape(Shape):
    faces_vertices_json: str = ""

    def material_kwargs(self):
        return dict(material_class=p3.MeshBasicMaterial,
                    transparent=True,
                    opacity=0.8,
                    depthWrite=False,
                    side="DoubleSide")

    def make_geometry(self):

        if isinstance(self.faces_vertices_json, list):
            faces_vertices_json = self.faces_vertices_json[0]
            if len(self.faces_vertices_json) > 1:
                print("Got case where PolyhedronShape had actual json list, assumed it only had one element")
        else:
            faces_vertices_json = self.faces_vertices_json

        parsed = json.loads(faces_vertices_json)

        vertices = np.array(parsed["vertices"], dtype=np.float32)
        indices = triangulate_faces(parsed["faces"])

        geometry = p3.BufferGeometry(
            attributes={
                "position": p3.BufferAttribute(vertices),
            },
            index=p3.BufferAttribute(indices, normalized=False),
        )

        geometry.exec_three_obj_method("computeVertexNormals")

        return geometry

    def __repr__(self):
        return f"PolyhedronShape {self.faces_vertices_json}"