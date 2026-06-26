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
    #material: p3.Material
    transform: Transform | None = None

    @abstractmethod
    def make_geometry(self):
        pass

    def make_mesh(self, material):
        geometry = self.make_geometry()

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

    def make_mesh(self, material):
        geometry = self.make_geometry()

        line = p3.Line(geometry=geometry, material=material)

        if self.transform is not None:
            self.transform.apply_to(line)

        return line

    def __repr__(self):
        return f"LineShape {self.points}"


@dataclass
class CircleShape(Shape):
    radius: float | None = None
    segments: int | None = None
    align_axis: tuple[float, float, float] | None = None

    def make_geometry(self):
        print(self.segments)
        return p3.CircleGeometry(
            radius=self.radius,
            segments=self.segments,
        )

    def make_mesh(self, material):
        mesh = super().make_mesh(material)

        if self.align_axis is not None:
            mesh.quaternion = quaternion_from_vectors(
                (0, 0, 1),  # default circle axis
                self.align_axis,
            )

        #if self.transform is not None:
        #    self.transform.apply_to(mesh)

        return mesh

    def __repr__(self):
        return f"CylinderShape r{self.radius} h{self.height}"

@dataclass
class CylinderShape(Shape):
    radius: float | None = None
    height: float | None = None
    radial_segments: int | None = None
    align_axis: tuple[float, float, float] | None = None

    def make_geometry(self):
        return p3.CylinderGeometry(
            radiusTop=self.radius,
            radiusBottom=self.radius,
            height=self.height,
            radialSegments=self.radial_segments,
        )

    def make_mesh(self, material):
        mesh = super().make_mesh(material)

        if self.align_axis is not None:
            mesh.quaternion = quaternion_from_vectors(
                (0, 1, 0),  # default cylinder axis
                self.align_axis,
            )

        #if self.transform is not None:
        #    self.transform.apply_to(mesh)

        return mesh

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

    def make_geometry(self):
        parsed = json.loads(self.faces_vertices_json)

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