from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from mcstasscript.geometry_viewer.renderer.base import RendererBackend
from mcstasscript.geometry_viewer.model.shapes import (
    Shape, BoxShape, CylinderShape, ConeShape, CircleShape,
    LineSegmentsShape, PolyhedronShape, Style,
)
from mcstasscript.geometry_viewer.transform import Transform, quaternion_to_rotation_matrix
from mcstasscript.geometry_viewer.config import DEFAULT_COLORS


@dataclass
class LineDescriptor:
    points: np.ndarray
    color: str


class MatplotlibRenderer(RendererBackend):
    def __init__(self, mode: str = "3d", colors: list[str] | None = None):
        self.mode = mode
        self.colors = colors or DEFAULT_COLORS
        self._color_index = 0

    def _next_color(self) -> str:
        color = self.colors[self._color_index]
        self._color_index = (self._color_index + 1) % len(self.colors)
        return color

    def create_material(self, style: Style | None, color: str, **kwargs) -> dict:
        props = {"color": color}
        if style:
            if style.opacity != 1.0:
                props["alpha"] = style.opacity
            if style.wireframe:
                props["linewidths"] = 0.5
        props.update(kwargs)
        return props

    def render_shape(self, shape: Shape) -> Any:
        if isinstance(shape, BoxShape):
            return self._render_box(shape)
        elif isinstance(shape, CylinderShape):
            return self._render_cylinder(shape)
        elif isinstance(shape, ConeShape):
            return self._render_cone(shape)
        elif isinstance(shape, CircleShape):
            return self._render_circle(shape)
        elif isinstance(shape, LineSegmentsShape):
            return self._render_line_segments(shape)
        elif isinstance(shape, PolyhedronShape):
            return self._render_polyhedron(shape)
        raise ValueError(f"Unknown shape type: {type(shape)}")

    def _transform_points(self, points: np.ndarray, transform: Transform | None) -> np.ndarray:
        if transform is None:
            return np.asarray(points, dtype=np.float64)
        pts = np.asarray(points, dtype=np.float64)
        q = transform.final_quaternion()
        if q is not None:
            R = quaternion_to_rotation_matrix(q)
            pts = pts @ R.T
        if transform.position is not None:
            pts = pts + np.asarray(transform.position, dtype=np.float64)
        return pts

    def _remap_to_display(self, pts: np.ndarray) -> np.ndarray:
        """Remap data (X, Y, Z) → display (Z, X, Y) so Z is horizontal."""
        return pts[:, [2, 0, 1]]

    def _render_box(self, shape: BoxShape) -> Poly3DCollection:
        w, h, d = shape.width, shape.height, shape.depth
        vx = [-w / 2, w / 2]
        vy = [-h / 2, h / 2]
        vz = [-d / 2, d / 2]

        faces = [
            [[vx[0], vy[0], vz[0]], [vx[1], vy[0], vz[0]], [vx[1], vy[1], vz[0]], [vx[0], vy[1], vz[0]]],
            [[vx[0], vy[0], vz[1]], [vx[1], vy[0], vz[1]], [vx[1], vy[1], vz[1]], [vx[0], vy[1], vz[1]]],
            [[vx[0], vy[0], vz[0]], [vx[0], vy[0], vz[1]], [vx[0], vy[1], vz[1]], [vx[0], vy[1], vz[0]]],
            [[vx[1], vy[0], vz[0]], [vx[1], vy[0], vz[1]], [vx[1], vy[1], vz[1]], [vx[1], vy[1], vz[0]]],
            [[vx[0], vy[0], vz[0]], [vx[1], vy[0], vz[0]], [vx[1], vy[0], vz[1]], [vx[0], vy[0], vz[1]]],
            [[vx[0], vy[1], vz[0]], [vx[1], vy[1], vz[0]], [vx[1], vy[1], vz[1]], [vx[0], vy[1], vz[1]]],
        ]

        if shape.transform:
            for i, face in enumerate(faces):
                faces[i] = self._remap_to_display(self._transform_points(np.array(face), shape.transform)).tolist()
        else:
            faces = [self._remap_to_display(np.array(f)).tolist() for f in faces]

        color = self._next_color()
        return Poly3DCollection(
            faces, facecolors=color, edgecolors=color,
            alpha=0.8, linewidths=0.5,
        )

    def _sample_cylinder_mesh(self, radius_top, radius_bottom, height, segments):
        verts = np.linspace(0, 2 * np.pi, segments + 1)
        mesh = []
        for i in range(segments):
            v0, v1 = verts[i], verts[i + 1]
            if height > 0:
                y0, y1 = -height / 2, height / 2
            else:
                y0, y1 = 0, 0
            quad = [
                [radius_bottom * np.cos(v0), y0, radius_bottom * np.sin(v0)],
                [radius_bottom * np.cos(v1), y0, radius_bottom * np.sin(v1)],
                [radius_top * np.cos(v1), y1, radius_top * np.sin(v1)],
                [radius_top * np.cos(v0), y1, radius_top * np.sin(v0)],
            ]
            mesh.append(quad)
        return mesh

    def _render_cylinder(self, shape: CylinderShape) -> Poly3DCollection:
        mesh = self._sample_cylinder_mesh(shape.radius, shape.radius, shape.height, shape.radial_segments)
        if shape.transform:
            mesh = [self._remap_to_display(self._transform_points(np.array(f), shape.transform)).tolist() for f in mesh]
        else:
            mesh = [self._remap_to_display(np.array(f)).tolist() for f in mesh]

        largest_dim = max(2 * shape.radius, shape.height)
        if largest_dim <= 0.05:
            alpha = 0.9
        elif largest_dim <= 0.5:
            alpha = 0.85
        elif largest_dim <= 1.5:
            alpha = 0.65
        else:
            alpha = 0.4

        color = self._next_color()
        return Poly3DCollection(
            mesh, facecolors=color, edgecolors=color,
            alpha=alpha, linewidths=0.5,
        )

    def _render_cone(self, shape: ConeShape) -> Poly3DCollection:
        mesh = self._sample_cylinder_mesh(0, shape.radius, shape.height, shape.radial_segments)
        if shape.transform:
            mesh = [self._remap_to_display(self._transform_points(np.array(f), shape.transform)).tolist() for f in mesh]
        else:
            mesh = [self._remap_to_display(np.array(f)).tolist() for f in mesh]

        color = self._next_color()
        return Poly3DCollection(
            mesh, facecolors=color, edgecolors=color,
            alpha=0.8, linewidths=0.5,
        )

    def _render_circle(self, shape: CircleShape) -> Poly3DCollection:
        angles = np.linspace(0, 2 * np.pi, shape.segments + 1)
        pts = np.column_stack([
            shape.radius * np.cos(angles),
            shape.radius * np.sin(angles),
            np.zeros(shape.segments + 1),
        ])

        tri_faces = []
        for i in range(shape.segments):
            tri_faces.append([pts[0], pts[i + 1], pts[(i + 2) % (shape.segments + 1)]])

        if shape.transform:
            tri_faces = [self._remap_to_display(self._transform_points(np.array(f), shape.transform)).tolist() for f in tri_faces]
        else:
            tri_faces = [self._remap_to_display(np.array(f)).tolist() for f in tri_faces]

        if shape.radius <= 0.05:
            alpha = 0.9
        elif shape.radius <= 0.5:
            alpha = 0.7
        elif shape.radius <= 1.5:
            alpha = 0.4
        else:
            alpha = 0.2

        color = self._next_color()
        return Poly3DCollection(
            tri_faces, facecolors=color, edgecolors="none",
            alpha=alpha,
        )

    def _render_line_segments(self, shape: LineSegmentsShape) -> LineDescriptor:
        points = self._remap_to_display(self._transform_points(shape.points, shape.transform))
        color = self._next_color()
        return LineDescriptor(points=points, color=color)

    def _render_polyhedron(self, shape: PolyhedronShape) -> Poly3DCollection:
        vertices = self._remap_to_display(self._transform_points(shape.vertices, shape.transform))
        faces = vertices[shape.indices.reshape(-1, 3)]

        color = self._next_color()
        return Poly3DCollection(
            faces, facecolors=color, edgecolors=color,
            alpha=0.8, linewidths=0.5,
        )

    def apply_transform(self, visual_obj: Any, transform: Transform | None) -> Any:
        return visual_obj

    def make_scene(self, children: list[Any], show_axes: bool = True,
                   width: int = 900, height: int = 600, **kwargs) -> plt.Figure:
        if self.mode == "3d":
            return self._make_3d_scene(children, show_axes, width, height, **kwargs)
        else:
            return self._make_2d_scene(children, show_axes, width, height, **kwargs)

    def _make_3d_scene(self, children, show_axes, width, height, **kwargs):
        fig = plt.figure(figsize=(width / 100, height / 100))
        ax = fig.add_subplot(111, projection="3d")

        all_verts = []
        for child in children:
            if isinstance(child, Poly3DCollection):
                ax.add_collection3d(child)
                for paths in child.get_paths():
                    all_verts.extend(paths.vertices)
            elif isinstance(child, LineDescriptor):
                ax.plot(
                    child.points[:, 0], child.points[:, 1], child.points[:, 2],
                    c=child.color, linewidth=1,
                )
                all_verts.extend(child.points)

        if show_axes:
            ax.set_xlabel("Z")
            ax.set_ylabel("X")
            ax.set_zlabel("Y")

        if all_verts:
            all_verts = np.array(all_verts)
            margin = 0.5
            mins = all_verts.min(axis=0) - margin
            maxs = all_verts.max(axis=0) + margin
            ax.set_xlim(mins[0], maxs[0])
            ax.set_ylim(mins[1], maxs[1])
            ax.set_zlim(mins[2], maxs[2])
            extents = maxs - mins
            ax.set_box_aspect(extents.tolist())
        else:
            ax.set_xlim(-5, 5)
            ax.set_ylim(-5, 5)
            ax.set_zlim(-5, 5)

        ax.view_init(elev=0, azim=-90)
        return fig

    def _make_2d_scene(self, children, show_axes, width, height, **kwargs):
        fig = plt.figure(figsize=(width / 100, height / 100))
        ax = fig.add_subplot(111)

        all_verts = []
        for child in children:
            if isinstance(child, Poly3DCollection):
                proj_faces = []
                for face in child.get_paths():
                    verts = face.vertices[:, :2]
                    proj_faces.append(verts)
                    all_verts.extend(verts)
                if proj_faces:
                    collection = PolyCollection(
                        proj_faces,
                        facecolors=child.get_facecolors(),
                        edgecolors=child.get_edgecolors(),
                        linewidths=child.get_linewidths(),
                    )
                    ax.add_collection(collection)
            elif isinstance(child, LineDescriptor):
                ax.plot(
                    child.points[:, 0], child.points[:, 1],
                    c=child.color, linewidth=1,
                )
                all_verts.extend(child.points[:, :2])

        if show_axes:
            ax.set_xlabel("X")
            ax.set_ylabel("Y")

        if all_verts:
            all_verts = np.array(all_verts)
            margin = 0.5
            mins = all_verts.min(axis=0) - margin
            maxs = all_verts.max(axis=0) + margin
            ax.set_xlim(mins[0], maxs[0])
            ax.set_ylim(mins[1], maxs[1])
        else:
            ax.set_xlim(-5, 5)
            ax.set_ylim(-5, 5)

        ax.set_aspect("equal")
        return fig
