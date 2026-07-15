from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Hashable

import numpy as np
import pythreejs as p3

from mcstasscript.geometry_viewer.renderer.base import RendererBackend
from mcstasscript.geometry_viewer.model.shapes import (
    Shape, BoxShape, CylinderShape, ConeShape, CircleShape,
    LineSegmentsShape, PolyhedronShape, Style,
)
from mcstasscript.geometry_viewer.transform import Transform
from mcstasscript.geometry_viewer.config import DEFAULT_COLORS, index_to_color


@dataclass
class MaterialLibrary:
    colors: list[str]
    material_class: type = p3.MeshBasicMaterial
    color_index: int = 0
    _cache: dict[tuple[type, str, tuple[tuple[str, Hashable], ...]], Any] = field(default_factory=dict)

    @property
    def color(self) -> str:
        return self.colors[self.color_index]

    def next(self) -> str:
        color = self.color
        self.color_index = (self.color_index + 1) % len(self.colors)
        return color

    def get_material(self, material_class: type | None = None, **kwargs: Any):
        cls = material_class or self.material_class
        kwargs = {"color": self.color, **kwargs}
        key = self._make_key(cls, kwargs)
        if key not in self._cache:
            self._cache[key] = cls(**kwargs)
        return self._cache[key]

    def get_material_for_color(self, color: str, material_class: type | None = None, **kwargs: Any):
        """Create or retrieve a material with a specific color (bypasses current color index)."""
        cls = material_class or self.material_class
        kwargs = {"color": color, **kwargs}
        key = self._make_key(cls, kwargs)
        if key not in self._cache:
            self._cache[key] = cls(**kwargs)
        return self._cache[key]

    def _make_key(self, cls: type, kwargs: dict[str, Any]):
        try:
            frozen_kwargs = tuple(sorted(kwargs.items()))
            hash(frozen_kwargs)
        except TypeError as exc:
            raise TypeError(
                "MaterialLibrary cache keys require hashable material arguments. "
                "For textures, arrays, or other objects, you may need to pass a stable name/id instead."
            ) from exc
        return cls, kwargs["color"], frozen_kwargs


def _compute_opacity_for_size(largest_dim: float, base_opacities: tuple = (0.9, 0.85, 0.65, 0.4)) -> float:
    """Compute opacity based on object size — smaller objects are more opaque."""
    if largest_dim <= 0.05:
        return base_opacities[0]
    elif largest_dim <= 0.5:
        return base_opacities[1]
    elif largest_dim <= 1.5:
        return base_opacities[2]
    else:
        return base_opacities[3]


class PyThreejsRenderer(RendererBackend):
    def __init__(self, colors: list[str] | None = None, colormode: str = "default", num_components: int = 0):
        self.material_library = MaterialLibrary(colors=colors or DEFAULT_COLORS)
        self.colormode = colormode
        self.num_components = num_components
        self.simple_components = []
        self.component_children: dict[int, list] = {}
        self.component_colors: dict[int, str] = {}

    def register_component(self, component_model):
        self.simple_components.append({
            "pos": component_model.global_position,
            "rotation": component_model.rotation_matrix,
            "name": component_model.comp.name,
            "component_name": component_model.comp.component_name,
        })

    def next_component(self) -> None:
        if self.colormode != "component":
            self.material_library.next()

    def render_component(self, component: Any, component_index: int = 0) -> list[Any]:
        self._current_component_index = component_index
        if self.colormode == "component" and self.num_components > 0:
            self._temp_color = index_to_color(component_index, self.num_components)
        else:
            self._temp_color = None
        children = super().render_component(component, component_index)
        self.component_children[component_index] = children
        self.component_colors[component_index] = self._temp_color or self.material_library.color
        return children

    def _get_material(self, material_class: type | None = None, **kwargs: Any):
        """Get a material, using temp_color if in component colormode."""
        if self._temp_color is not None:
            return self.material_library.get_material_for_color(self._temp_color, material_class=material_class, **kwargs)
        return self.material_library.get_material(material_class=material_class, **kwargs)

    def update_component_color(self, component_index: int, color: str) -> None:
        """Update the color of all meshes belonging to a component."""
        if component_index not in self.component_children:
            return
        self.component_colors[component_index] = color
        for child in self.component_children[component_index]:
            if hasattr(child, 'material') and hasattr(child.material, 'color'):
                child.material.color = color

    def create_material(self, style: Style | None, color: str, **kwargs) -> Any:
        mat_kwargs = {}
        if style and style.opacity != 1.0:
            mat_kwargs["transparent"] = True
            mat_kwargs["opacity"] = style.opacity
            mat_kwargs["depthWrite"] = False
            mat_kwargs["side"] = "DoubleSide"
        return self.material_library.get_material(**mat_kwargs, **kwargs)

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

    def _render_box(self, shape: BoxShape) -> p3.Mesh:
        geometry = p3.BoxGeometry(width=shape.width, height=shape.height, depth=shape.depth)
        material = self._get_material(
            material_class=p3.MeshLambertMaterial,
            transparent=True,
            opacity=0.8,
            depthWrite=False,
            side="DoubleSide",
        )
        mesh = p3.Mesh(geometry=geometry, material=material)
        self.apply_transform(mesh, shape.transform)
        return mesh

    def _render_cylinder(self, shape: CylinderShape) -> p3.Mesh:
        largest_dim = max(2 * shape.radius, shape.height)
        opacity = _compute_opacity_for_size(largest_dim)
        geometry = p3.CylinderGeometry(
            radiusTop=shape.radius,
            radiusBottom=shape.radius,
            height=shape.height,
            radialSegments=shape.radial_segments,
        )
        material = self._get_material(
            material_class=p3.MeshLambertMaterial,
            transparent=True,
            opacity=opacity,
            depthWrite=True,
            side="DoubleSide",
        )
        mesh = p3.Mesh(geometry=geometry, material=material)
        self.apply_transform(mesh, shape.transform)
        return mesh

    def _render_cone(self, shape: ConeShape) -> p3.Mesh:
        geometry = p3.CylinderGeometry(
            radiusTop=0,
            radiusBottom=shape.radius,
            height=shape.height,
            radialSegments=shape.radial_segments,
        )
        material = self._get_material(
            material_class=p3.MeshLambertMaterial,
            transparent=True,
            opacity=0.80,
            depthWrite=True,
            side="DoubleSide",
        )
        mesh = p3.Mesh(geometry=geometry, material=material)
        self.apply_transform(mesh, shape.transform)
        return mesh

    def _render_circle(self, shape: CircleShape) -> p3.Mesh:
        if shape.radius <= 0.05:
            opacity = 0.9
        elif shape.radius <= 0.5:
            opacity = 0.7
        elif shape.radius <= 1.5:
            opacity = 0.4
        else:
            opacity = 0.2
        geometry = p3.CircleGeometry(radius=shape.radius, segments=shape.segments)
        material = self._get_material(
            material_class=p3.MeshLambertMaterial,
            transparent=True,
            opacity=opacity,
            depthWrite=False,
            side="DoubleSide",
        )
        mesh = p3.Mesh(geometry=geometry, material=material)
        self.apply_transform(mesh, shape.transform)
        return mesh

    def _render_line_segments(self, shape: LineSegmentsShape) -> p3.LineSegments:
        points = np.asarray(shape.points, dtype=np.float32)
        geometry = p3.BufferGeometry(
            attributes={"position": p3.BufferAttribute(points)}
        )
        material = self._get_material(material_class=p3.LineBasicMaterial)
        line = p3.LineSegments(geometry=geometry, material=material)
        self.apply_transform(line, shape.transform)
        return line

    def _render_polyhedron(self, shape: PolyhedronShape) -> p3.Mesh:
        geometry = p3.BufferGeometry(
            attributes={"position": p3.BufferAttribute(shape.vertices)},
            index=p3.BufferAttribute(shape.indices, normalized=False),
        )
        geometry.exec_three_obj_method("computeVertexNormals")
        material = self._get_material(
            material_class=p3.MeshBasicMaterial,
            transparent=True,
            opacity=0.8,
            depthWrite=False,
            side="DoubleSide",
        )
        mesh = p3.Mesh(geometry=geometry, material=material)
        self.apply_transform(mesh, shape.transform)
        return mesh

    def apply_transform(self, visual_obj: Any, transform: Transform | None) -> Any:
        if transform is None:
            return visual_obj
        if transform.position is not None:
            visual_obj.position = tuple(np.asarray(transform.position, dtype=float))
        q = transform.final_quaternion()
        if q is not None:
            visual_obj.quaternion = q
        return visual_obj

    def make_scene(self, children: list[Any], show_axes: bool = True,
                    width: int = 900, height: int = 600, **kwargs) -> p3.Renderer:
        scene = p3.Scene(children=[])
        ambient = p3.AmbientLight(intensity=1.0)
        scene.add(ambient)

        if show_axes:
            scene.add(p3.AxesHelper(size=1))

        scene.add(p3.Group(children=children))

        camera = p3.PerspectiveCamera(
            position=[5, 3, 10],
            aspect=width / height,
            fov=50,
            near=0.01,
            far=2000,
        )
        camera.lookAt([0, 0, 2])

        controls = p3.OrbitControls(controlling=camera)
        renderer = p3.Renderer(
            camera=camera, scene=scene, controls=[controls],
            width=width, height=height,
        )
        return renderer

    def create_component_navigator(self, renderer):
        import ipywidgets as ipw

        SKIP_TYPES = []
        component_options = [
            (f"{comp['name']} ({comp['component_name']})", i)
            for i, comp in enumerate(self.simple_components)
            if comp["component_name"].lower() not in SKIP_TYPES
        ]

        dropdown = ipw.Dropdown(
            options=component_options,
            description="Take me to: ",
            style={"description_width": "initial"},
        )

        def on_component_select(change):
            if change["type"] != "change":
                return
            idx = change["new"]
            component = self.simple_components[idx]
            pos = np.asarray(component["pos"], dtype=float)
            distance = 2.0
            camera_pos = [
                float(pos[0] - distance * 0.5),
                float(pos[1] + distance * 0.7),
                float(pos[2] + distance * 0.5),
            ]
            target = [float(pos[0]), float(pos[1]), float(pos[2])]

            camera = renderer.camera
            controls = renderer.controls[0]

            with camera.hold_sync(), controls.hold_sync():
                camera.position = camera_pos
                camera.lookAt(target)
                controls.target = target

            controls.exec_three_obj_method("update")

        dropdown.observe(on_component_select, names="value")
        return dropdown

    def create_colormode_selector(self):
        import ipywidgets as ipw

        selector = ipw.Dropdown(
            options={"Default": "default", "Component": "component"},
            value=self.colormode,
            description="Colormode: ",
            style={"description_width": "initial"},
        )

        def on_colormode_change(change):
            if change["type"] != "change":
                return
            self.colormode = change["new"]
            for idx in self.component_children:
                if self.colormode == "component" and self.num_components > 0:
                    color = index_to_color(idx, self.num_components)
                else:
                    color = DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]
                self.update_component_color(idx, color)

        selector.observe(on_colormode_change, names="value")
        return selector
