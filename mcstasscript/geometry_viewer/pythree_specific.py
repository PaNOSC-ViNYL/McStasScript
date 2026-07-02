from __future__ import annotations

import numpy as np

from dataclasses import dataclass, field
from typing import Any, Hashable

import pythreejs as p3
import ipywidgets as ipw


@dataclass
class MaterialLibrary:
    colors: list[str]
    material_class: type = p3.MeshBasicMaterial # Default
    color_index: int = 0
    _cache: dict[tuple[type, str, tuple[tuple[str, Hashable], ...]], Any] = field(default_factory=dict)

    @property
    def color(self) -> str:
        return self.colors[self.color_index]

    def next(self) -> str:
        """Advance to the next color and return it."""
        self.color_index = (self.color_index + 1) % len(self.colors)
        return self.color

    def get_material(self, material_class: type | None = None, **kwargs: Any):
        """
        Return a cached material for the current color + material options.

        Example:
            mat = lib.get_material(p3.LineBasicMaterial, linewidth=1)
            mat = lib.get_material(p3.MeshPhongMaterial, transparent=True, opacity=0.4)
        """
        cls = material_class or self.material_class

        # Unless explicitly overridden, use the current library color.
        kwargs = {"color": self.color, **kwargs}

        key = self._make_key(cls, kwargs)

        if key not in self._cache:
            self._cache[key] = cls(**kwargs)

        return self._cache[key]

    def _make_key(self, cls: type, kwargs: dict[str, Any]):
        """
        Convert material parameters into a stable cache key.
        Assumes kwargs are simple hashable values: strings, numbers, bools, None.
        """
        try:
            frozen_kwargs = tuple(sorted(kwargs.items()))
            hash(frozen_kwargs)
        except TypeError as exc:
            raise TypeError(
                "MaterialLibrary cache keys require hashable material arguments. "
                "For textures, arrays, or other objects, you may need to pass a stable name/id instead."
            ) from exc

        return cls, kwargs["color"], frozen_kwargs


class PyThreeComponent:
    def __init__(self, component_model):
        self.pos = component_model.global_position
        self.rotation = component_model.rotation_matrix
        self.name = component_model.comp.name
        self.component_name = component_model.comp.component_name

class PyThreeGeometryModel:
    def __init__(self):
        self.mesh_objects = []  # Holds the mesh objects that are added to the scene

        default_colors = ["#ff0000", "#808080", "#00ff00", "#ffff00", "#0000ff",
                          "#ff00ff", "#00ffff", "#ffa500", "#444444", "#cccccc"]
        self.material_library = MaterialLibrary(colors=default_colors)

        self.simple_components = []

    def next_component(self):
        self.material_library.next()

    def add_component_model(self, model):
        """
        for shape in model.shape_list:
            self.group.add(shape.make_mesh(self.material_library))
        """

        self.simple_components.append(PyThreeComponent(model))

        children = [
            shape.make_mesh(self.material_library)
            for shape in model.shape_list
        ]

        self.mesh_objects += children

    def make_renderer(self, show_axes=True, width=900, height=600):
        scene = p3.Scene(children=[])
        ambient = p3.AmbientLight(intensity=1.0)
        scene.add(ambient)

        if show_axes:
            axes = p3.AxesHelper(size=1)
            scene.add(axes)

        scene.add(p3.Group(children=self.mesh_objects))

        camera = p3.PerspectiveCamera(
            position=[5, 3, 10], aspect=width / height, fov=50, near=0.01, far=2000
        )
        camera.lookAt([0, 0, 2])

        # Create renderer with orbit controls
        controls = p3.OrbitControls(controlling=camera)
        renderer = p3.Renderer(
            camera=camera, scene=scene, controls=[controls], width=width, height=height
        )

        return renderer

    def create_component_navigator(self, renderer):
        SKIP_TYPES = []

        component_options = [
            (f"{comp.name} ({comp.component_name})", i)
            for i, comp in enumerate(self.simple_components)
            if comp.component_name.lower() not in SKIP_TYPES
        ]

        dropdown = ipw.Dropdown(
            options=component_options,
            description="Take me to: ",
            style={"description_width": "initial"},
        )

        """
        def on_component_select(change):
            # idx = self.component_mapping.get(change["new"], None)
            # if idx is None:
            #     return
            idx = change["new"]
            component = self.simple_components[idx]
            pos = component.pos

            # Calculate camera position (offset to top-left and back)
            # Determine a reasonable distance based on component type
            comp_type = component.component_name.lower()

            # dynamic distance would be nice
            distance = 2.0

            # Position camera at an angle (top-left-front)
            cam_x = pos[0] - distance * 0.5
            cam_y = pos[1] + distance * 0.7
            cam_z = pos[2] + distance * 0.5

            # Update camera position
            renderer.camera.position = [cam_x, cam_y, cam_z]

            # Update controls target to component center
            renderer.controls[0].target = [float(pos[0]), float(pos[1]), float(pos[2])]

            # Reset the camera to look at the target
            renderer.camera.lookAt([float(pos[0]), float(pos[1]), float(pos[2])])
        """

        def on_component_select(change):
            if change["type"] != "change":
                return

            idx = change["new"]
            component = self.simple_components[idx]
            pos = np.asarray(component.pos, dtype=float)

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
