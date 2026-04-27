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


@dataclass
class LineShape(Shape):
    width: float = 1.0


    def make_geometry(self):
        return p3.BoxGeometry(
            width=self.width,
            height=self.height,
            depth=self.depth,
        )


@dataclass
class BoxShape(Shape):
    points: np.array = None

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

@dataclass
class CylinderShape(Shape):
    radius: float = 1.0
    height: float = 1.0
    radial_segments: int = 32
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

        if self.transform is not None:
            self.transform.apply_to(mesh)

        return mesh


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