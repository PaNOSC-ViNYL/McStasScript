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
from mcstasscript.geometry_viewer.config import DEFAULT_COLORS, index_to_color, intensity_to_color, create_colorbar_image


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
    def __init__(self, colors: list[str] | None = None, colormode: str = "default", num_components: int = 0,
                  intensity_map: dict | None = None, cmap: str = "inferno", log_scale: bool = True,
                  colorbar_label: str | None = None, instrument_object=None):
        self.material_library = MaterialLibrary(colors=colors or DEFAULT_COLORS)
        self.colormode = colormode
        self.num_components = num_components
        self.intensity_map = intensity_map
        self.cmap = cmap
        self.log_scale = log_scale
        self.colorbar_label = colorbar_label
        self._colorbar_widget = None
        self.simple_components = []
        self.component_children: dict[int, list] = {}
        self.component_colors: dict[int, str] = {}
        if intensity_map and intensity_map.values():
            self._min_I = min(intensity_map.values())
            self._max_I = max(intensity_map.values())
        else:
            self._min_I = 0.0
            self._max_I = 1.0

        # Intensity simulation state
        self.instrument_object = instrument_object
        self._diag_data = None
        self._diag_monitors = None
        self._diag_data_dim = None
        self._diag_variable = None
        self._data_stale = intensity_map is None
        self._intensity_controls_container = None
        self._intensity_widgets = {}

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
        if self.colormode == "intensity" and self.intensity_map is not None:
            comp_name = component.comp.name
            I = self.intensity_map.get(comp_name, 0.0)
            self._temp_color = intensity_to_color(I, self._min_I, self._max_I, self.cmap, self.log_scale)
        elif self.colormode == "component" and self.num_components > 0:
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

    def create_colorbar(self):
        """Create a colorbar widget for the current colormode."""
        import ipywidgets as ipw
        self._colorbar_widget = self._make_colorbar_image()
        return self._colorbar_widget

    def _make_colorbar_image(self):
        """Generate a colorbar image widget for the current colormode."""
        import ipywidgets as ipw
        if self.colormode == "default":
            return ipw.Image(value=b'', format='png', layout=ipw.Layout(width='60px'))
        if self.colormode == "intensity":
            if self.intensity_map is not None:
                label = self.colorbar_label or "Value"
                img = create_colorbar_image(self.cmap, self._min_I, self._max_I,
                                              label, self.log_scale)
                return ipw.Image(value=img, format='png', layout=ipw.Layout(width='60px'))
            return ipw.Image(value=b'', format='png', layout=ipw.Layout(width='60px'))
        label = self.colorbar_label or "Component index"
        img = create_colorbar_image("viridis", 0, max(self.num_components - 1, 1),
                                      label, log_scale=False)
        return ipw.Image(value=img, format='png', layout=ipw.Layout(width='60px'))

    def _update_colorbar(self):
        """Update the colorbar widget in-place after a colormode change."""
        if self._colorbar_widget is not None:
            new = self._make_colorbar_image()
            self._colorbar_widget.value = new.value
            self._colorbar_widget.layout = new.layout

    def _grey_all_components(self):
        """Set all components to grey to indicate stale/no data."""
        for idx in self.component_children:
            self.update_component_color(idx, "#808080")

    def _apply_intensity_from_data(self, aggregation: str | None = None):
        """Build intensity_map from cached diagnostic data and re-color components."""
        if self._diag_data is None or self._diag_monitors is None:
            return
        from mcstasscript.geometry_viewer.api import _aggregate_intensity
        from mcstasscript.interface.functions import name_search

        if aggregation is None:
            aggregation = self._intensity_widgets.get("aggregate", "total")
            if hasattr(aggregation, "value"):
                aggregation = aggregation.value

        intensity_map = {}
        for mon_name, comp_name in self._diag_monitors:
            try:
                mon_data = name_search(mon_name, self._diag_data)
                intensity_map[comp_name] = _aggregate_intensity(mon_data, aggregation)
            except Exception:
                intensity_map[comp_name] = 0.0

        # Also color the source component using first monitor data
        if self._diag_monitors and self.simple_components:
            try:
                first_mon_name = self._diag_monitors[0][0]
                first_mon_data = name_search(first_mon_name, self._diag_data)
                source_name = self.instrument_object.component_list[0].name
                intensity_map[source_name] = _aggregate_intensity(first_mon_data, aggregation)
            except Exception:
                pass

        self.intensity_map = intensity_map
        if intensity_map and intensity_map.values():
            self._min_I = min(intensity_map.values())
            self._max_I = max(intensity_map.values())

        # Update colorbar label
        try:
            first_mon_name = self._diag_monitors[0][0]
            first_mon_data = name_search(first_mon_name, self._diag_data)
            if self._diag_data_dim == 1 and first_mon_data.metadata.xlabel:
                self.colorbar_label = first_mon_data.metadata.xlabel
            else:
                self.colorbar_label = "Intensity [n/s]"
        except Exception:
            self.colorbar_label = "Intensity [n/s]"

        for idx in self.component_children:
            comp_name = self.simple_components[idx]["name"]
            I = intensity_map.get(comp_name, 0.0)
            color = intensity_to_color(I, self._min_I, self._max_I, self.cmap, self.log_scale)
            self.update_component_color(idx, color)
        self._update_colorbar()

    def _disable_intensity_controls(self, disabled: bool):
        """Enable/disable all intensity control widgets."""
        for w in self._intensity_widgets.values():
            if hasattr(w, "disabled"):
                w.disabled = disabled

    def _update_limits_visibility(self):
        """Show/hide limits fields based on variable selection and limits checkbox."""
        variable_widget = self._intensity_widgets.get("variable")
        limits_check = self._intensity_widgets.get("limits_check")
        limits_min = self._intensity_widgets.get("limits_min")
        limits_max = self._intensity_widgets.get("limits_max")
        if not (variable_widget and limits_check and limits_min and limits_max):
            return
        has_variable = variable_widget.value is not None
        use_limits = limits_check.value
        show = has_variable and use_limits
        limits_min.layout.display = "" if show else "none"
        limits_max.layout.display = "" if show else "none"

    def _on_variable_change(self, change):
        """Handle variable dropdown change — mark data stale, grey components, toggle limits."""
        if change["type"] != "change":
            return
        self._data_stale = True
        self._diag_variable = change["new"]
        self._update_limits_visibility()
        if self.colormode == "intensity":
            self._grey_all_components()

    def _on_limits_check_change(self, change):
        """Handle limits checkbox change — show/hide limits fields."""
        if change["type"] != "change":
            return
        self._update_limits_visibility()

    def _on_run_click(self, btn):
        """Run intensity simulation and apply results."""
        if self.instrument_object is None:
            return
        self._disable_intensity_controls(True)
        btn.icon = "hourglass"
        btn.description = "Running..."

        try:
            from mcstasscript.instrument_diagnostics.intensity_diagnostics import IntensityDiagnostics

            ncount_val = self._intensity_widgets.get("ncount")
            variable_val = self._intensity_widgets.get("variable")
            limits_min_val = self._intensity_widgets.get("limits_min")
            limits_max_val = self._intensity_widgets.get("limits_max")

            ncount = int(ncount_val.value) if ncount_val else 1000000
            variable = variable_val.value if variable_val else None

            limits = None
            limits_check = self._intensity_widgets.get("limits_check")
            if variable is not None and limits_check and limits_check.value:
                if limits_min_val and limits_max_val:
                    try:
                        limits = [float(limits_min_val.value), float(limits_max_val.value)]
                    except (ValueError, TypeError):
                        limits = None

            diag = IntensityDiagnostics(self.instrument_object)
            if ncount:
                diag.instr.settings(ncount=ncount)
            if variable is not None:
                diag.run_general(variable=variable, limits=limits)
            else:
                diag.run()

            self._diag_data = diag.data
            self._diag_monitors = diag.monitors
            self._diag_data_dim = diag.data_dim
            self._diag_variable = variable
            self._data_stale = False

            agg = self._intensity_widgets.get("aggregate")
            aggregation = agg.value if hasattr(agg, "value") else "total"
            self._apply_intensity_from_data(aggregation)

        except Exception:
            pass
        finally:
            btn.icon = "play"
            btn.description = "Run"
            self._disable_intensity_controls(False)

    def _on_aggregate_change(self, change):
        """Handle aggregate dropdown change — re-apply from cached data if not stale."""
        if change["type"] != "change":
            return
        if not self._data_stale and self._diag_data is not None:
            self._apply_intensity_from_data(change["new"])

    def create_intensity_controls(self):
        """Create the intensity simulation control widgets."""
        import ipywidgets as ipw

        default_ncount = 1000000
        if self.instrument_object and hasattr(self.instrument_object, "_run_settings"):
            default_ncount = self.instrument_object._run_settings.get("ncount", 1000000)

        ncount_widget = ipw.IntText(
            value=int(default_ncount),
            description="ncount:",
            style={"description_width": "initial"},
            layout=ipw.Layout(width="160px"),
        )

        variable_options = {
            "None (0D total)": None,
            "l (wavelength)": "l",
            "x (position)": "x",
            "y (position)": "y",
            "z (position)": "z",
            "t (time)": "t",
            "px": "px",
            "py": "py",
            "pz": "pz",
            "p4": "p4",
            "e (energy)": "e",
            "s1": "s1",
            "s2": "s2",
            "s3": "s3",
        }
        variable_widget = ipw.Dropdown(
            options=variable_options,
            value=None,
            description="Variable:",
            style={"description_width": "initial"},
            layout=ipw.Layout(width="180px"),
        )

        limits_check_widget = ipw.Checkbox(
            value=False,
            description="Limits",
            tooltip="Enable min/max limits for variable scan",
            style={"description_width": "initial"},
            layout=ipw.Layout(width="90px"),
        )

        limits_min_widget = ipw.Text(
            value="",
            description="Min:",
            style={"description_width": "initial"},
            layout=ipw.Layout(width="100px", display="none"),
        )
        limits_max_widget = ipw.Text(
            value="",
            description="Max:",
            style={"description_width": "initial"},
            layout=ipw.Layout(width="100px", display="none"),
        )

        aggregate_options = {
            "total": "total",
            "min": "min",
            "max": "max",
            "average": "average",
            "median": "median",
            "span": "span",
        }
        aggregate_widget = ipw.Dropdown(
            options=aggregate_options,
            value="total",
            description="Aggregate:",
            style={"description_width": "initial"},
            layout=ipw.Layout(width="140px"),
        )

        run_button = ipw.Button(
            description="Run",
            button_style="",
            icon="play",
            layout=ipw.Layout(width="100px"),
        )

        variable_widget.observe(self._on_variable_change, names="value")
        limits_check_widget.observe(self._on_limits_check_change, names="value")
        aggregate_widget.observe(self._on_aggregate_change, names="value")
        run_button.on_click(self._on_run_click)

        self._intensity_widgets = {
            "ncount": ncount_widget,
            "variable": variable_widget,
            "limits_check": limits_check_widget,
            "limits_min": limits_min_widget,
            "limits_max": limits_max_widget,
            "aggregate": aggregate_widget,
            "run_button": run_button,
        }

        row1 = ipw.HBox([ncount_widget, variable_widget, limits_check_widget, limits_min_widget, limits_max_widget, run_button])
        row2 = ipw.HBox([aggregate_widget])
        container = ipw.VBox([row1, row2], layout=ipw.Layout(display="none"))
        self._intensity_controls_container = container
        return container

    def create_colormode_selector(self):
        import ipywidgets as ipw

        options = {"Default": "default", "Component": "component", "Intensity": "intensity"}
        selector = ipw.Dropdown(
            options=options,
            value=self.colormode,
            description="Colormode: ",
            style={"description_width": "initial"},
        )

        def on_colormode_change(change):
            if change["type"] != "change":
                return
            self.colormode = change["new"]

            if self._intensity_controls_container is not None:
                if self.colormode == "intensity":
                    self._intensity_controls_container.layout.display = ""
                    if self._data_stale:
                        self._grey_all_components()
                    elif self.intensity_map is not None:
                        agg = self._intensity_widgets.get("aggregate")
                        aggregation = agg.value if hasattr(agg, "value") else "total"
                        self._apply_intensity_from_data(aggregation)
                else:
                    self._intensity_controls_container.layout.display = "none"

            for idx in self.component_children:
                if self.colormode == "intensity" and self.intensity_map is not None and not self._data_stale:
                    comp_name = self.simple_components[idx]["name"]
                    I = self.intensity_map.get(comp_name, 0.0)
                    color = intensity_to_color(I, self._min_I, self._max_I, self.cmap, self.log_scale)
                elif self.colormode == "component" and self.num_components > 0:
                    color = index_to_color(idx, self.num_components)
                else:
                    color = DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]
                self.update_component_color(idx, color)
            self._update_colorbar()

        selector.observe(on_colormode_change, names="value")
        return selector
