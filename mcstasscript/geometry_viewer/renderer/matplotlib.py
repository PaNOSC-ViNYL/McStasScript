from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize, LogNorm
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from mcstasscript.geometry_viewer.renderer.base import RendererBackend
from mcstasscript.geometry_viewer.model.shapes import (
    Shape, BoxShape, CylinderShape, ConeShape, CircleShape,
    LineSegmentsShape, PolyhedronShape, Style,
)
from mcstasscript.geometry_viewer.transform import Transform, quaternion_to_rotation_matrix
from mcstasscript.geometry_viewer.config import DEFAULT_COLORS, index_to_color, intensity_to_color


@dataclass
class LineDescriptor:
    points: np.ndarray
    color: str


class MatplotlibRenderer(RendererBackend):
    def __init__(self, mode: str = "3d", colors: list[str] | None = None, projection: str = "zx",
                 colormode: str = "default", num_components: int = 0,
                 intensity_map: dict | None = None, cmap: str = "inferno", log_scale: bool = True,
                 colorbar_label: str | None = None):
        self.mode = mode
        self.colors = colors or DEFAULT_COLORS
        self._color_index = 0
        self.projection = projection.lower() if self.mode == "2d" else "xy"
        self.colormode = colormode
        self.num_components = num_components
        self.intensity_map = intensity_map
        self.cmap = cmap
        self.log_scale = log_scale
        self.colorbar_label = colorbar_label
        self._validate_projection()
        self.component_children: dict[int, list] = {}
        self.component_colors: dict[int, str] = {}
        self._temp_color = None
        if intensity_map and intensity_map.values():
            self._min_I = min(intensity_map.values())
            self._max_I = max(intensity_map.values())
        else:
            self._min_I = 0.0
            self._max_I = 1.0

    @property
    def current_color(self) -> str:
        """Return the current color without advancing the index."""
        if hasattr(self, '_temp_color') and self._temp_color is not None:
            return self._temp_color
        if self.colormode == "component" and self.num_components > 0:
            return index_to_color(self._color_index, self.num_components)
        return self.colors[self._color_index]

    def _next_color(self) -> str:
        color = self.current_color
        self._color_index = (self._color_index + 1) % len(self.colors)
        return color

    def next_component(self) -> None:
        """Advance to the next color for the upcoming component."""
        self._temp_color = None
        if self.colormode == "component" and self.num_components > 0:
            self._color_index += 1
        else:
            self._next_color()

    def _validate_projection(self):
        if self.projection not in ("xy", "zx", "zy"):
            raise ValueError(f"Invalid projection: {self.projection!r}. Must be one of 'xy', 'zx', 'zy'.")

    def render_component(self, component: Any, component_index: int = 0) -> list[Any]:
        if self.colormode == "intensity" and self.intensity_map is not None:
            comp_name = component.comp.name
            I = self.intensity_map.get(comp_name, 0.0)
            self._temp_color = intensity_to_color(I, self._min_I, self._max_I, self.cmap, self.log_scale)
        else:
            self._temp_color = None
        color = self.current_color
        children = super().render_component(component, component_index)
        self.component_children[component_index] = children
        self.component_colors[component_index] = color
        return children

    def update_component_color(self, component_index: int, color: str) -> None:
        """Update the color of all artists belonging to a component."""
        if component_index not in self.component_children:
            return
        self.component_colors[component_index] = color
        for child in self.component_children[component_index]:
            if isinstance(child, PolyCollection):
                child.set_facecolors(color)
                if child.get_edgecolors() is not None and not np.array_equal(child.get_edgecolors(), [[0, 0, 0, 0]]):
                    child.set_edgecolors(color)
            elif isinstance(child, Poly3DCollection):
                child.set_facecolors(color)
                if child.get_edgecolors() is not None and not np.array_equal(child.get_edgecolors(), [[0, 0, 0, 0]]):
                    child.set_edgecolors(color)
            elif hasattr(child, 'set_color'):
                child.set_color(color)

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
        if self.mode == "3d":
            return pts[:, [2, 0, 1]]
        mapping = {"xy": [0, 1, 2], "zx": [2, 0, 1], "zy": [2, 1, 0]}
        return pts[:, mapping[self.projection]]

    def _make_collection(self, faces, color, alpha, edge_color="none", lw=0.5):
        """Create a PolyCollection (2D) or Poly3DCollection (3D) from face data."""
        if self.mode == "2d":
            faces_2d = [np.array(f)[:, :2] for f in faces]
            return PolyCollection(
                faces_2d, facecolors=color, edgecolors=edge_color,
                alpha=alpha, linewidths=lw,
            )
        else:
            return Poly3DCollection(
                faces, facecolors=color, edgecolors=edge_color,
                alpha=alpha, linewidths=lw,
            )

    def _render_box(self, shape: BoxShape):
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

        color = self.current_color
        return self._make_collection(faces, color, 0.8, edge_color=color)

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

    def _render_cylinder(self, shape: CylinderShape):
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

        color = self.current_color
        return self._make_collection(mesh, color, alpha, edge_color=color)

    def _render_cone(self, shape: ConeShape):
        mesh = self._sample_cylinder_mesh(0, shape.radius, shape.height, shape.radial_segments)
        if shape.transform:
            mesh = [self._remap_to_display(self._transform_points(np.array(f), shape.transform)).tolist() for f in mesh]
        else:
            mesh = [self._remap_to_display(np.array(f)).tolist() for f in mesh]

        color = self.current_color
        return self._make_collection(mesh, color, 0.8, edge_color=color)

    def _render_circle(self, shape: CircleShape):
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

        color = self.current_color
        return self._make_collection(tri_faces, color, alpha)

    def _render_line_segments(self, shape: LineSegmentsShape) -> LineDescriptor:
        points = self._remap_to_display(self._transform_points(shape.points, shape.transform))
        color = self.current_color
        return LineDescriptor(points=points, color=color)

    def _render_polyhedron(self, shape: PolyhedronShape):
        vertices = self._remap_to_display(self._transform_points(shape.vertices, shape.transform))
        faces = vertices[shape.indices.reshape(-1, 3)]

        color = self.current_color
        return self._make_collection(faces, color, 0.8, edge_color=color)

    def apply_transform(self, visual_obj: Any, transform: Transform | None) -> Any:
        return visual_obj

    def _add_colorbar(self, fig):
        """Add a colorbar to the figure for non-default colormodes."""
        if self.colormode == "default":
            return
        if self.colormode == "intensity" and self.intensity_map is not None:
            label = self.colorbar_label or "Value"
            if self.log_scale and self._max_I > 0 and self._min_I > 0:
                norm = LogNorm(vmin=self._min_I, vmax=self._max_I)
            else:
                norm = Normalize(vmin=max(self._min_I, 0), vmax=self._max_I)
            sm = ScalarMappable(cmap=self.cmap, norm=norm)
        else:
            label = self.colorbar_label or "Component index"
            norm = Normalize(vmin=0, vmax=max(self.num_components - 1, 1))
            sm = ScalarMappable(cmap="viridis", norm=norm)
        sm.set_array([])
        fig.subplots_adjust(right=0.88)
        cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
        fig.colorbar(sm, cax=cbar_ax, label=label)

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
                line, = ax.plot(
                    child.points[:, 0], child.points[:, 1], child.points[:, 2],
                    c=child.color, linewidth=1,
                )
                all_verts.extend(child.points)
                comp_idx = getattr(child, '_component_index', 0)
                if comp_idx in self.component_children:
                    for i, c in enumerate(self.component_children[comp_idx]):
                        if c is child:
                            self.component_children[comp_idx][i] = line
                            break

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
        self._add_colorbar(fig)
        return fig

    def _make_2d_scene(self, children, show_axes, width, height, **kwargs):
        fig = plt.figure(figsize=(width / 100, height / 100))
        ax = fig.add_subplot(111)

        all_verts = []
        for child in children:
            if isinstance(child, PolyCollection):
                ax.add_collection(child)
                for face in child.get_paths():
                    all_verts.extend(face.vertices)
            elif isinstance(child, Poly3DCollection):
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
                line, = ax.plot(
                    child.points[:, 0], child.points[:, 1],
                    c=child.color, linewidth=1,
                )
                all_verts.extend(child.points[:, :2])
                comp_idx = getattr(child, '_component_index', 0)
                if comp_idx in self.component_children:
                    for i, c in enumerate(self.component_children[comp_idx]):
                        if c is child:
                            self.component_children[comp_idx][i] = line
                            break

        if show_axes:
            label_map = {"xy": ("X", "Y"), "zx": ("Z", "X"), "zy": ("Z", "Y")}
            ax.set_xlabel(label_map[self.projection][0])
            ax.set_ylabel(label_map[self.projection][1])

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
        self._add_colorbar(fig)
        return fig
