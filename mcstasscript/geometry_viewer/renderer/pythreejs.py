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
from mcstasscript.geometry_viewer.config import DEFAULT_COLORS, index_to_color, intensity_to_color


@dataclass
class MaterialLibrary:
    colors: list[str]
    material_class: type = p3.MeshBasicMaterial
    color_index: int = 0
    _cache: dict[tuple[type, str, tuple[tuple[str, Hashable], ...], int | None], Any] = field(default_factory=dict)

    @property
    def color(self) -> str:
        return self.colors[self.color_index]

    def next(self) -> str:
        color = self.color
        self.color_index = (self.color_index + 1) % len(self.colors)
        return color

    def get_material(self, material_class: type | None = None, component_index: int | None = None, **kwargs: Any):
        cls = material_class or self.material_class
        kwargs = {"color": self.color, **kwargs}
        key = self._make_key(cls, kwargs, component_index)
        if key not in self._cache:
            self._cache[key] = cls(**kwargs)
        return self._cache[key]

    def get_material_for_color(self, color: str, material_class: type | None = None, component_index: int | None = None, **kwargs: Any):
        """Create or retrieve a material with a specific color (bypasses current color index)."""
        cls = material_class or self.material_class
        kwargs = {"color": color, **kwargs}
        key = self._make_key(cls, kwargs, component_index)
        if key not in self._cache:
            self._cache[key] = cls(**kwargs)
        return self._cache[key]

    def _make_key(self, cls: type, kwargs: dict[str, Any], component_index: int | None = None):
        try:
            frozen_kwargs = tuple(sorted(kwargs.items()))
            hash(frozen_kwargs)
        except TypeError as exc:
            raise TypeError(
                "MaterialLibrary cache keys require hashable material arguments. "
                "For textures, arrays, or other objects, you may need to pass a stable name/id instead."
            ) from exc
        return cls, kwargs["color"], frozen_kwargs, component_index


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
                  colorbar_label: str | None = None, instrument_object=None,
                  component_colors: dict[str, str] | None = None,
                  component_opacity: dict[str, float] | None = None):
        self.material_library = MaterialLibrary(colors=colors or DEFAULT_COLORS)
        self.colormode = colormode
        self.num_components = num_components
        self.intensity_map = intensity_map
        self.cmap = cmap
        self.log_scale = log_scale
        self._colorbar_label = colorbar_label
        self._colorbar_widget = None
        self._intensity_computed_label = None
        self.simple_components = []
        self.component_children: dict[int, list] = {}
        self.component_colors: dict[int, str] = {}
        self.component_colors_map = component_colors or {}
        self._custom_colors_active = False
        self._custom_colors_checkbox = None
        self.component_opacity: dict[int, float] = {}
        self._base_opacities: dict[int, float] = {}
        self.component_opacity_map = component_opacity or {}
        self._custom_opacities_active = False
        self._custom_opacities_checkbox = None
        if self.component_opacity_map:
            for name, val in self.component_opacity_map.items():
                if not isinstance(val, (int, float)):
                    raise TypeError(
                        f"component_opacity values must be numeric, got {type(val).__name__} for {name!r}"
                    )
                if not (0.0 <= val <= 1.0):
                    raise ValueError(
                        f"component_opacity values must be in [0.0, 1.0], got {val} for {name!r}"
                    )
                self.component_opacity_map[name] = float(val)
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

    @property
    def colorbar_label(self) -> str | None:
        """Public accessor — returns the explicit API-supplied label."""
        return self._colorbar_label

    @colorbar_label.setter
    def colorbar_label(self, value: str | None) -> None:
        """Public setter — stores the explicit API-supplied label."""
        self._colorbar_label = value

    def _compute_colorbar_label(self) -> str:
        """Compute the correct colorbar label for the current colormode.

        Component mode always uses 'Component index'.
        Intensity mode uses the explicitly supplied label (if any),
        or a dynamically computed label based on aggregation/data.
        """
        if self.colormode == "intensity":
            if self._colorbar_label is not None:
                return self._colorbar_label
            if self._intensity_computed_label is not None:
                return self._intensity_computed_label
            return "Value"
        else:
            return "Component index"

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
        # Capture original opacity from the first mesh child (all shapes in a component
        # typically share the same opacity; we store one representative value per component)
        orig_opacity = 1.0
        for child in children:
            if hasattr(child, 'material') and hasattr(child.material, 'opacity'):
                orig_opacity = child.material.opacity
                break
        self.component_opacity[component_index] = orig_opacity
        self._base_opacities[component_index] = orig_opacity
        return children

    def _get_material(self, material_class: type | None = None, **kwargs: Any):
        """Get a material, using temp_color if in component colormode.

        Materials are scoped by component_index so that mutating one
        component's material color does not affect another component.
        """
        ci = getattr(self, '_current_component_index', None)
        if self._temp_color is not None:
            return self.material_library.get_material_for_color(
                self._temp_color, material_class=material_class,
                component_index=ci, **kwargs,
            )
        return self.material_library.get_material(
            material_class=material_class, component_index=ci, **kwargs,
        )

    def update_component_color(self, component_index: int, color: str) -> None:
        """Update the color of all meshes belonging to a component."""
        if component_index not in self.component_children:
            return
        self.component_colors[component_index] = color
        for child in self.component_children[component_index]:
            if hasattr(child, 'material') and hasattr(child.material, 'color'):
                child.material.color = color

    def update_component_opacity(self, component_index: int, opacity: float) -> None:
        """Update the opacity of all meshes belonging to a component."""
        if component_index not in self.component_children:
            return
        self.component_opacity[component_index] = opacity
        for child in self.component_children[component_index]:
            if hasattr(child, 'material') and hasattr(child.material, 'opacity'):
                child.material.opacity = opacity
                child.material.transparent = opacity < 1.0

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
        import matplotlib
        matplotlib.use('module://ipympl.backend_nbagg', force=True)
        from matplotlib.figure import Figure
        import ipympl.backend_nbagg as ipympl_backend

        self._colorbar_widget = ipw.VBox()
        # Construct Figure + ipympl Canvas directly, bypassing pyplot entirely.
        # This prevents IPython/Jupyter from auto-displaying a duplicate
        # figure at cell end, while keeping the ipympl canvas fully live.
        self._colorbar_fig = Figure(figsize=(1.5, 3.5), dpi=100)
        self._colorbar_canvas = ipympl_backend.Canvas(self._colorbar_fig)
        # Create manager so the canvas is fully initialised, but do NOT
        # register it with pyplot's Gcf — that's what causes auto-display.
        ipympl_backend.FigureManager(self._colorbar_canvas, 0)
        self._colorbar_ax = self._colorbar_fig.add_axes([0.25, 0.08, 0.35, 0.78])
        self._colorbar_cbar = None
        self._colorbar_widget.children = (self._colorbar_canvas,)
        self._update_colorbar_figure()
        return self._colorbar_widget

    def _update_colorbar_figure(self):
        """Update the embedded matplotlib colorbar in-place."""
        from matplotlib.cm import ScalarMappable
        from matplotlib.colors import Normalize, LogNorm
        from matplotlib.ticker import MaxNLocator, LogLocator, LogFormatterMathtext

        if self.colormode == "default" or \
            (self.colormode == "intensity" and self.intensity_map is None):
            self._colorbar_ax.cla()
            self._colorbar_ax.axis('off')
            self._colorbar_cbar = None
            self._colorbar_canvas.draw_idle()
            return

        if self.colormode == "intensity":
            label = self._compute_colorbar_label()
            cmap_name = self.cmap
            vmin, vmax = self._min_I, self._max_I
            log_scale = self.log_scale
        else:
            label = self._compute_colorbar_label()
            cmap_name = "viridis"
            vmin, vmax = 0, max(self.num_components - 1, 1)
            log_scale = False

        use_log = log_scale and vmax > 0 and vmin > 0

        if use_log:
            norm = LogNorm(vmin=vmin, vmax=vmax)
        else:
            norm = Normalize(vmin=max(vmin, 0), vmax=vmax)

        sm = ScalarMappable(cmap=cmap_name, norm=norm)
        sm.set_array([])

        self._colorbar_ax.cla()
        self._colorbar_cbar = self._colorbar_fig.colorbar(sm, cax=self._colorbar_ax, label=label)

        if use_log:
            self._colorbar_cbar.locator = LogLocator(base=10)
            self._colorbar_cbar.formatter = LogFormatterMathtext(base=10)
        else:
            self._colorbar_cbar.locator = MaxNLocator(nbins=5)
        self._colorbar_cbar.update_ticks()

        self._colorbar_cbar.ax.tick_params(labelsize=10)
        self._colorbar_cbar.ax.set_ylabel(label, fontsize=11, rotation=90, labelpad=10)
        self._colorbar_canvas.draw_idle()

    def _update_colorbar(self):
        """Update the colorbar widget in-place after a colormode change."""
        self._update_colorbar_figure()

    def _grey_all_components(self):
        """Set all components to grey to indicate stale/no data.

        If custom colors are active, only grey unmapped components.
        If custom opacities are active, re-apply mapped opacities.
        """
        for idx in self.component_children:
            self.update_component_color(idx, "#808080")
        if self._custom_colors_active:
            self._overlay_custom_colors()
        if self._custom_opacities_active:
            self._overlay_custom_opacities()

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

        # Update colorbar label — store in mode-specific state
        try:
            first_mon_name = self._diag_monitors[0][0]
            first_mon_data = name_search(first_mon_name, self._diag_data)
            if aggregation == "total":
                self._intensity_computed_label = "Intensity [n/s]"
            elif aggregation == "ncount":
                self._intensity_computed_label = "N rays"
            elif self._diag_data_dim == 1 and first_mon_data.metadata.xlabel:
                self._intensity_computed_label = first_mon_data.metadata.xlabel
            else:
                self._intensity_computed_label = "Intensity [n/s]"
        except Exception:
            self._intensity_computed_label = "Intensity [n/s]"

        for idx in self.component_children:
            comp_name = self.simple_components[idx]["name"]
            I = intensity_map.get(comp_name, 0.0)
            color = intensity_to_color(I, self._min_I, self._max_I, self.cmap, self.log_scale)
            self.update_component_color(idx, color)
        if self._custom_colors_active:
            self._overlay_custom_colors()
        if self._custom_opacities_active:
            self._overlay_custom_opacities()
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
            "ncount": "ncount",
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

    def _colormode_color_for_index(self, idx: int) -> str:
        """Compute the color for a component index based on the current colormode."""
        if self.colormode == "intensity" and self.intensity_map is not None and not self._data_stale:
            comp_name = self.simple_components[idx]["name"]
            I = self.intensity_map.get(comp_name, 0.0)
            return intensity_to_color(I, self._min_I, self._max_I, self.cmap, self.log_scale)
        elif self.colormode == "component" and self.num_components > 0:
            return index_to_color(idx, self.num_components)
        else:
            return DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]

    def _overlay_custom_colors(self):
        """Recolor only mapped components from component_colors_map.

        Does NOT touch unmapped components — they keep whatever color
        they currently have. Used after any recoloring operation to
        restore custom colors when the checkbox is active.
        """
        if not self.component_colors_map:
            return
        for idx, comp_info in enumerate(self.simple_components):
            comp_name = comp_info["name"]
            if comp_name in self.component_colors_map:
                self.update_component_color(idx, self.component_colors_map[comp_name])

    def _apply_custom_colors(self):
        """Apply custom colors to mapped components only; leave others untouched."""
        if not self.component_colors_map:
            return
        self._overlay_custom_colors()
        self._custom_colors_active = True

    def _reset_to_colormode_colors(self):
        """Reset all components to colors determined by the current colormode."""
        self._custom_colors_active = False
        for idx in self.component_children:
            self.update_component_color(idx, self._colormode_color_for_index(idx))

    def _on_custom_colors_toggle(self, change):
        """Handle custom colors checkbox toggle."""
        if change["type"] != "change":
            return
        if change["new"]:
            self._apply_custom_colors()
        else:
            self._reset_to_colormode_colors()

    def create_custom_colors_checkbox(self):
        """Create a checkbox to toggle custom component colors.

        Returns None if no component_colors_map was provided.
        """
        import ipywidgets as ipw

        if not self.component_colors_map:
            return None

        checkbox = ipw.Checkbox(
            value=False,
            description="Custom colors",
            tooltip="Override colors for specified components",
            style={"description_width": "initial"},
        )
        checkbox.observe(self._on_custom_colors_toggle, names="value")
        self._custom_colors_checkbox = checkbox
        return checkbox

    def _overlay_custom_opacities(self):
        """Re-apply opacity only to mapped components from component_opacity_map.

        Does NOT touch unmapped components — they keep whatever opacity
        they currently have. Used after any recoloring operation to
        restore custom opacities when the checkbox is active.
        """
        if not self.component_opacity_map:
            return
        for idx, comp_info in enumerate(self.simple_components):
            comp_name = comp_info["name"]
            if comp_name in self.component_opacity_map:
                self.update_component_opacity(idx, self.component_opacity_map[comp_name])

    def _apply_custom_opacities(self):
        """Apply custom opacities to mapped components only; leave others untouched."""
        if not self.component_opacity_map:
            return
        self._overlay_custom_opacities()
        self._custom_opacities_active = True

    def _reset_to_base_opacities(self):
        """Reset all components to their original/base opacity captured at render time."""
        self._custom_opacities_active = False
        for idx in self.component_children:
            if idx in self._base_opacities:
                self.update_component_opacity(idx, self._base_opacities[idx])

    def _on_custom_opacities_toggle(self, change):
        """Handle custom opacities checkbox toggle."""
        if change["type"] != "change":
            return
        if change["new"]:
            self._apply_custom_opacities()
        else:
            self._reset_to_base_opacities()

    def create_custom_opacities_checkbox(self):
        """Create a checkbox to toggle custom component opacities.

        Returns None if no component_opacity_map was provided.
        """
        import ipywidgets as ipw

        if not self.component_opacity_map:
            return None

        checkbox = ipw.Checkbox(
            value=False,
            description="Custom opacity",
            tooltip="Override opacity for specified components",
            style={"description_width": "initial"},
        )
        checkbox.observe(self._on_custom_opacities_toggle, names="value")
        self._custom_opacities_checkbox = checkbox
        return checkbox

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
                self.update_component_color(idx, self._colormode_color_for_index(idx))
            if self._custom_colors_active:
                self._overlay_custom_colors()
            if self._custom_opacities_active:
                self._overlay_custom_opacities()
            self._update_colorbar()

        selector.observe(on_colormode_change, names="value")
        return selector
