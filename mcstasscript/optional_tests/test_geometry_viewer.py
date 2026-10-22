import json
import math
import os
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from mcstasscript.geometry_viewer.transform import (
    pos_rot_from_list,
    normalize,
    quaternion_from_vectors,
    quaternion_from_rotation_matrix,
    quaternion_to_rotation_matrix,
    normalize_quaternion,
    quaternion_multiply,
    Transform,
    euler_to_rotation_matrix,
    resolve_transforms,
    TransformResolutionError,
)
from mcstasscript.geometry_viewer.model.shapes import (
    Style,
    BoxShape,
    LineSegmentsShape,
    CircleShape,
    ConeShape,
    CylinderShape,
    PolyhedronShape,
    SphereShape,
    triangulate_faces,
)
from mcstasscript.geometry_viewer.model.component import (
    ComponentModel,
    DRAWCALL_PARSERS,
    _parse_box,
    _parse_cylinder,
    _parse_cone,
    _parse_circle,
    _parse_polyhedron,
    _parse_multiline,
)
from mcstasscript.geometry_viewer.model.instrument import InstrumentModel
from mcstasscript.geometry_viewer.config import (
    DEFAULT_COLORS,
    DEFAULT_CAMERA_POSITION,
    DEFAULT_CAMERA_TARGET,
    DEFAULT_FOV,
    DEFAULT_NEAR,
    DEFAULT_FAR,
    DEFAULT_RENDERER_SIZE,
    DEFAULT_RADIAL_SEGMENTS,
    DEFAULT_CIRCLE_SEGMENTS,
    DEFAULT_NAVIGATOR_DISTANCE,
    DEFAULT_PICK_TOLERANCE,
    index_to_color,
    intensity_to_color,
)
from mcstasscript.geometry_viewer.api import _get_renderer, view, view_with_guess, view_with_json
from mcstasscript.geometry_viewer.expression import safe_eval, UnsafeExpressionError
from mcstasscript.geometry_viewer.renderer.pythreejs import (
    PyThreejsRenderer,
    MaterialLibrary,
    _plain_component_text,
)


# Path to the mcdisplay JSON fixture
FIXTURE_JSON = os.path.join(
    os.path.dirname(__file__), "..", "tests", "test_geometry_viewer", "instrument.json"
)


def load_fixture():
    with open(FIXTURE_JSON) as f:
        return json.load(f)


def make_mock_component(name="test_comp"):
    """Create a minimal mock component object compatible with ComponentModel."""
    comp = MagicMock()
    comp.name = name
    comp.parameter_names = []
    comp.parameter_defaults = {}
    return comp


def make_mock_component_with_params(xwidth=1.0, yheight=2.0):
    """Create a mock component with xwidth/yheight parameters (rectangle type)."""
    comp = MagicMock()
    comp.name = "rect_comp"
    comp.parameter_names = ["xwidth", "yheight"]
    comp.xwidth = xwidth
    comp.yheight = yheight
    comp.parameter_defaults = {"xwidth": 0.0, "yheight": 0.0}
    return comp


class TestApi(unittest.TestCase):
    def test_get_renderer_pythreejs(self):
        """
        Requesting the 'pythreejs' backend should return a
        PyThreejsRenderer instance.
        """
        renderer = _get_renderer("pythreejs")
        self.assertIsInstance(renderer, PyThreejsRenderer)

    def test_get_renderer_pythreejs_reports_missing_optional_module(self):
        """The pythreejs backend reports missing optional dependencies."""
        with patch.dict("sys.modules", {"pythreejs": None}):
            with self.assertRaisesRegex(ImportError, "pythreejs.*optional module"):
                _get_renderer("pythreejs")

class TestPyThreejsComponentSelection(unittest.TestCase):
    """Tests for picking a visual and showing its source component."""

    def test_picker_maps_visual_to_component_details(self):
        import ipywidgets as ipw

        component = make_mock_component("selected")
        component.component_name = "Box"
        model = ComponentModel(component)
        model.shape_list = [BoxShape(width=1, height=1, depth=1)]

        renderer = PyThreejsRenderer()
        renderer.register_component(model)
        children = renderer.render_component(model, component_index=0)
        scene = renderer.make_scene(children)
        details = renderer.create_component_details(scene)

        self.assertIsInstance(details, ipw.Textarea)
        self.assertEqual(details.value, "Click a component in the scene.")
        self.assertEqual(len(scene.controls), 2)
        self.assertIs(renderer._component_picker.controlling, renderer._component_group)
        self.assertEqual(renderer._component_picker.lineThreshold, DEFAULT_PICK_TOLERANCE)
        self.assertEqual(
            renderer._component_picker.lineThreshold,
            renderer._component_picker.pointThreshold,
        )

        renderer._on_component_pick({"new": children[0]})
        self.assertEqual(details.value, str(component))

        renderer._on_component_pick({"new": None})
        self.assertEqual(details.value, "Click a component in the scene.")

    def test_picker_maps_line_visual_to_component_details(self):

        component = make_mock_component("line_selected")
        component.component_name = "Line"
        model = ComponentModel(component)
        model.shape_list = [LineSegmentsShape(points=[
            [0, 0, 0], [1, 0, 0],
        ])]

        renderer = PyThreejsRenderer()
        renderer.register_component(model)
        children = renderer.render_component(model, component_index=0)
        scene = renderer.make_scene(children)
        details = renderer.create_component_details(scene)

        renderer._on_component_pick({"new": children[0]})
        self.assertEqual(details.value, str(component))

    def test_navigator_selection_updates_component_details(self):
        import ipywidgets as ipw

        component = make_mock_component("selected")
        component.component_name = "Box"
        model = ComponentModel(component)
        model.shape_list = [BoxShape(width=1, height=1, depth=1)]

        renderer = PyThreejsRenderer()
        renderer.register_component(model)
        children = renderer.render_component(model, component_index=0)
        scene = renderer.make_scene(children)
        details = renderer.create_component_details(scene)
        navigator = renderer.create_component_navigator(scene)

        self.assertIsInstance(navigator, ipw.Combobox)
        navigator.value = "selected"
        self.assertEqual(details.value, str(component))

        previous_value = details.value
        navigator.value = "does_not_exist"
        self.assertEqual(details.value, previous_value)

    def test_component_details_strip_terminal_formatting(self):

        class ColoredComponent:
            def __str__(self):
                return "\033[1mCOMPONENT\033[0m"

        self.assertEqual(_plain_component_text(ColoredComponent()), "COMPONENT")

    def test_api_includes_component_details_widget(self):
        import ipywidgets as ipw

        instr = MagicMock()
        instr.component_list = [make_mock_component("selected")]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(instr, backend="pythreejs")

        details = [child for child in result.children if isinstance(child, ipw.Textarea)]
        self.assertEqual(len(details), 1)
        self.assertIs(result.children[-1], details[0])

class TestPyThreejsIntensity(unittest.TestCase):
    """Tests for PyThreejsRenderer intensity colormode."""

    def setUp(self):
        self.intensity_map = {"comp1": 1.0, "comp2": 10.0, "comp3": 100.0}
        self.renderer = PyThreejsRenderer(
            intensity_map=self.intensity_map,
            colormode="intensity",
            cmap="inferno",
            log_scale=True,
        )

    def test_init_with_intensity_map(self):
        """Renderer should store intensity params and compute min/max."""
        self.assertEqual(self.renderer.intensity_map, self.intensity_map)
        self.assertEqual(self.renderer._min_I, 1.0)
        self.assertEqual(self.renderer._max_I, 100.0)
        self.assertEqual(self.renderer.cmap, "inferno")
        self.assertEqual(self.renderer.log_scale, True)

    def test_render_component_intensity_color(self):
        """Rendering a component in intensity mode should set _temp_color."""
        comp = make_mock_component("comp2")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        self.renderer.render_component(comp_model, component_index=0)
        self.assertIsNotNone(self.renderer._temp_color)
        expected = intensity_to_color(10.0, 1.0, 100.0, "inferno", True)
        self.assertEqual(self.renderer._temp_color, expected)

    def test_render_component_missing_intensity(self):
        """A component not in the intensity_map should use 0.0 intensity."""
        comp = make_mock_component("unknown_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        self.renderer.render_component(comp_model, component_index=0)
        expected = intensity_to_color(0.0, 1.0, 100.0, "inferno", True)
        self.assertEqual(self.renderer._temp_color, expected)

    def test_colormode_selector_has_intensity(self):
        """The colormode selector should include 'Intensity' when intensity_map is set."""
        selector = self.renderer.create_colormode_selector()
        self.assertIn("Intensity", selector.options)

    def test_colormode_selector_without_map_omits_intensity(self):
        """Intensity is unavailable until a map or controls are provided."""
        renderer = PyThreejsRenderer()
        selector = renderer.create_colormode_selector()
        self.assertNotIn("Intensity", selector.options)

    def test_colormode_selector_with_controls_has_intensity(self):
        """Intensity is available when the renderer can run diagnostics."""
        renderer = PyThreejsRenderer()
        renderer.create_intensity_controls()
        selector = renderer.create_colormode_selector()
        self.assertIn("Intensity", selector.options)

    def test_no_intensity_map_falls_through(self):
        """Without intensity_map, default colormode should work as before."""
        renderer = PyThreejsRenderer(colormode="default")
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.render_component(comp_model, component_index=0)
        self.assertIsNone(renderer._temp_color)

    def test_intensity_controls_exist(self):
        """create_intensity_controls returns a VBox with hidden display."""
        container = self.renderer.create_intensity_controls()
        import ipywidgets as ipw
        self.assertIsInstance(container, ipw.VBox)
        self.assertEqual(container.layout.display, "none")

    def test_intensity_widgets_populated(self):
        """After creating controls, _intensity_widgets dict is populated."""
        self.renderer.create_intensity_controls()
        expected_keys = {"ncount", "variable", "limits_check", "limits_min", "limits_max", "aggregate", "log_scale", "orders_of_mag", "run_button"}
        self.assertEqual(set(self.renderer._intensity_widgets.keys()), expected_keys)

    def test_orders_of_mag_control_updates_renderer(self):
        """Changing orders of magnitude updates the renderer range setting."""
        self.renderer.create_intensity_controls()
        orders_widget = self.renderer._intensity_widgets["orders_of_mag"]

        orders_widget.value = "4.5"

        self.assertEqual(self.renderer.orders_of_mag, 4.5)

    def test_orders_of_mag_limits_log_colorbar(self):
        """Log colorbar keeps the maximum and limits its lower decade range."""

        renderer = PyThreejsRenderer(
            intensity_map={"low": 1e-9, "high": 1.0},
            colormode="intensity",
            orders_of_mag=3,
        )
        renderer.create_colorbar()

        self.assertAlmostEqual(renderer._colorbar_cbar.norm.vmin, 1e-3)
        self.assertAlmostEqual(renderer._colorbar_cbar.norm.vmax, 1.0)

    def test_negative_intensity_data_uses_linear_colorbar(self):
        """Negative values disable logarithmic scaling and remain visible."""

        renderer = PyThreejsRenderer(
            intensity_map={"low": -2.0, "high": 1.0},
            colormode="intensity",
            log_scale=True,
        )
        renderer.create_colorbar()

        self.assertEqual(renderer._colorbar_cbar.norm.vmin, -2.0)
        self.assertEqual(renderer._colorbar_cbar.norm.vmax, 1.0)

    def test_run_failure_warns_and_marks_data_stale(self):
        """Intensity failures should be visible and leave the widget stale."""
        renderer = PyThreejsRenderer(instrument_object=MagicMock())
        renderer.create_intensity_controls()
        button = renderer._intensity_widgets["run_button"]
        with patch(
            "mcstasscript.instrument_diagnostics.intensity_diagnostics.IntensityDiagnostics",
            side_effect=RuntimeError("simulation failed"),
        ):
            with self.assertWarnsRegex(RuntimeWarning, "simulation failed"):
                renderer._on_run_click(button)
        self.assertTrue(renderer._data_stale)

    def test_run_uses_diagnostic_ncount_setting(self):
        """The ncount widget value persists through the diagnostic reset."""

        renderer = PyThreejsRenderer(instrument_object=MagicMock())
        renderer.create_intensity_controls()
        renderer._intensity_widgets["ncount"].value = 12345
        button = renderer._intensity_widgets["run_button"]

        diagnostic = MagicMock()
        diagnostic.data = object()
        diagnostic.monitors = []
        diagnostic.data_dim = 0
        with patch(
            "mcstasscript.instrument_diagnostics.intensity_diagnostics.IntensityDiagnostics",
            return_value=diagnostic,
        ):
            renderer._on_run_click(button)

        diagnostic.settings.assert_called_once_with(ncount=12345)
        diagnostic.instr.settings.assert_not_called()

    def test_variable_dropdown_options(self):
        """Variable dropdown includes common McStas variables."""
        self.renderer.create_intensity_controls()
        var_widget = self.renderer._intensity_widgets["variable"]
        self.assertIsNone(var_widget.value)
        self.assertIn(None, var_widget.options.values())
        self.assertIn("lambda", var_widget.options.values())
        self.assertIn("kx", var_widget.options.values())
        self.assertIn("energy", var_widget.options.values())
        self.assertIn("user9", var_widget.options.values())
        self.assertNotIn("px", var_widget.options.values())
        self.assertNotIn("p4", var_widget.options.values())
        self.assertNotIn("s1", var_widget.options.values())

    def test_selecting_stale_intensity_mode_greys_components(self):
        """Selecting intensity mode greys components until data is available."""

        renderer = PyThreejsRenderer()
        comp_model = ComponentModel(make_mock_component("comp"))
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        renderer.create_intensity_controls()
        renderer.create_colorbar()
        selector = renderer.create_colormode_selector()

        selector.value = "intensity"

        self.assertEqual(renderer.component_colors[0], "#808080")

    def test_log_scale_control_requires_nonnegative_data(self):
        """Log scale is enabled only for nonnegative intensity data."""

        renderer = PyThreejsRenderer()
        renderer.create_intensity_controls()
        log_scale = renderer._intensity_widgets["log_scale"]
        self.assertTrue(log_scale.disabled)

        renderer.intensity_map = {"comp": 1.0, "other": 2.0}
        renderer._data_stale = False
        renderer._update_log_scale_control()
        self.assertFalse(log_scale.disabled)

        renderer.intensity_map = {"comp": -1.0, "other": 2.0}
        renderer.log_scale = True
        log_scale.value = True
        renderer._update_log_scale_control()
        self.assertTrue(log_scale.disabled)
        self.assertFalse(log_scale.value)
        self.assertFalse(renderer.log_scale)

    def test_aggregate_dropdown_options(self):
        """Aggregate dropdown includes all aggregation modes."""
        self.renderer.create_intensity_controls()
        agg_widget = self.renderer._intensity_widgets["aggregate"]
        self.assertEqual(agg_widget.value, "total")
        expected = {"total", "min", "max", "average", "median", "span", "ncount"}
        self.assertEqual(set(agg_widget.options.keys()), expected)

    def test_grey_all_components(self):
        """_grey_all_components sets all component colors to grey."""
        renderer = PyThreejsRenderer()
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.render_component(comp_model, component_index=0)
        renderer._grey_all_components()
        self.assertEqual(renderer.component_colors[0], "#808080")

    def test_data_stale_default(self):
        """Without intensity_map, _data_stale should be True."""
        renderer = PyThreejsRenderer()
        self.assertTrue(renderer._data_stale)

    def test_data_not_stale_with_map(self):
        """With intensity_map, _data_stale should be False."""
        renderer = PyThreejsRenderer(intensity_map={"a": 1.0})
        self.assertFalse(renderer._data_stale)

    def test_colorbar_stale_intensity(self):
        """In intensity mode without data, colorbar VBox has canvas but no colorbar content."""
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(colormode="intensity")
        cb = renderer.create_colorbar()
        self.assertIsInstance(cb, ipw.VBox)
        self.assertEqual(len(cb.children), 1)

class TestPyThreejsColorbar(unittest.TestCase):
    """Tests for PyThreejsRenderer colorbar widget."""

    def test_colorbar_intensity_mode(self):
        """In intensity mode, create_colorbar should return a VBox with content."""
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        cb = renderer.create_colorbar()
        self.assertIsInstance(cb, ipw.VBox)
        self.assertGreater(len(cb.children), 0)

    def test_colorbar_default_mode(self):
        """In default mode, create_colorbar should return a VBox with canvas but no colorbar."""
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(colormode="default")
        cb = renderer.create_colorbar()
        self.assertIsInstance(cb, ipw.VBox)
        self.assertEqual(len(cb.children), 1)

    def test_colorbar_component_mode(self):
        """In component mode, create_colorbar should return a VBox with content."""
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(colormode="component", num_components=10)
        cb = renderer.create_colorbar()
        self.assertIsInstance(cb, ipw.VBox)
        self.assertGreater(len(cb.children), 0)

    def test_colorbar_label_stored(self):
        """colorbar_label should be stored on the renderer."""
        renderer = PyThreejsRenderer(colorbar_label="Wavelength [Å]")
        self.assertEqual(renderer.colorbar_label, "Wavelength [Å]")

    def test_colorbar_no_duplicates_on_update(self):
        """Updating colorbar mode should not accumulate multiple colorbars."""
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        cb = renderer.create_colorbar()
        self.assertEqual(len(cb.children), 1)
        renderer.colormode = "component"
        renderer.num_components = 5
        renderer._update_colorbar()
        self.assertEqual(len(cb.children), 1)
        renderer.colormode = "intensity"
        renderer._update_colorbar()
        self.assertEqual(len(cb.children), 1)
        renderer.colormode = "default"
        renderer._update_colorbar()
        self.assertEqual(len(cb.children), 1)

    def test_colorbar_figure_not_in_pyplot_manager(self):
        """The colorbar figure must not be registered in pyplot's manager.

        Regression test: plt.figure() registers the figure with pyplot's
        figure manager, causing IPython/Jupyter to auto-display it at cell
        end — producing a duplicate colorbar below the embedded widget.
        The figure is constructed directly (bypassing pyplot) so it is
        never registered, and the ipympl canvas remains fully live.
        """
        import matplotlib.pyplot as plt
        import matplotlib._pylab_helpers as ph

        # Ensure clean state
        plt.close("all")

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        cb = renderer.create_colorbar()

        # The figure should NOT be in pyplot's manager at all
        fig = renderer._colorbar_fig
        all_managed = [fm.canvas.figure for fm in ph.Gcf.get_all_fig_managers()]
        self.assertNotIn(fig, all_managed,
                         "colorbar figure must not be in pyplot manager "
                         "to prevent notebook auto-display")

        # The canvas must be a live ipympl Canvas (DOMWidget)
        import ipympl.backend_nbagg as ipympl_backend
        canvas = cb.children[0]
        self.assertIsInstance(canvas, ipympl_backend.Canvas,
                              "VBox child must be a live ipympl Canvas widget")
        self.assertIs(canvas, renderer._colorbar_canvas)
        self.assertIs(canvas.figure, fig)

        # The canvas must still be drawable (colormode switch uses draw_idle)
        renderer.colormode = "component"
        renderer.num_components = 5
        renderer._update_colorbar()
        self.assertEqual(len(cb.children), 1)
        self.assertIs(cb.children[0], canvas)

        renderer.colormode = "intensity"
        renderer._update_colorbar()
        self.assertEqual(len(cb.children), 1)
        self.assertIs(cb.children[0], canvas)

        plt.close("all")

    def test_colorbar_canvas_receives_draw(self):
        """The ipympl canvas must receive draw_idle calls on colormode change.

        Regression test: plt.close(fig) prevented auto-display but also
        destroyed the canvas, leaving a blank widget.  With direct
        Figure + FigureCanvasNbAgg construction, draw_idle must succeed
        and the canvas must remain the same live instance.
        """
        import ipympl.backend_nbagg as ipympl_backend

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        cb = renderer.create_colorbar()
        canvas = cb.children[0]

        # Verify canvas is live and has a draw_idle method
        self.assertIsInstance(canvas, ipympl_backend.Canvas)
        self.assertTrue(hasattr(canvas, 'draw_idle'))

        # Wrap draw_idle to verify it gets called
        draw_called = []
        original_draw_idle = canvas.draw_idle
        def tracking_draw_idle(*args, **kwargs):
            draw_called.append(True)
            return original_draw_idle(*args, **kwargs)
        canvas.draw_idle = tracking_draw_idle

        # Switch colormode and update — should trigger draw_idle
        renderer.colormode = "component"
        renderer.num_components = 5
        renderer._update_colorbar()
        self.assertTrue(draw_called, "draw_idle should be called on colormode update")

        draw_called.clear()
        renderer.colormode = "intensity"
        renderer._update_colorbar()
        self.assertTrue(draw_called, "draw_idle should be called on intensity update")

        draw_called.clear()
        renderer.colormode = "default"
        renderer._update_colorbar()
        self.assertTrue(draw_called, "draw_idle should be called on default update")

    def test_colorbar_label_intensity_to_component_to_intensity(self):
        """Switching intensity -> component -> intensity restores correct labels.

        Regression: after intensity mode set a custom label, switching back
        to component mode kept that label instead of 'Component index'.
        """
        import ipywidgets as ipw

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        # Set a computed intensity label (simulating _apply_intensity_from_data)
        renderer._intensity_computed_label = "Wavelength [A]"
        cb = renderer.create_colorbar()

        # Intensity mode should show the computed label
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Wavelength [A]",
            "intensity mode should show computed label",
        )

        # Switch to component mode — should show "Component index"
        renderer.colormode = "component"
        renderer.num_components = 5
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Component index",
            "component mode should always show 'Component index'",
        )

        # Switch back to intensity — should restore the computed label
        renderer.colormode = "intensity"
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Wavelength [A]",
            "switching back to intensity should restore computed label",
        )

    def test_colorbar_label_aggregate_total_restores_intensity(self):
        """Selecting 'total' aggregation restores 'Intensity [n/s]' label.

        Regression: changing intensity aggregation changed the label, but
        selecting 'total' should restore the intensity label.
        """

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        cb = renderer.create_colorbar()

        # Simulate non-total aggregation setting a metadata-based label
        renderer._intensity_computed_label = "Wavelength [A]"
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Wavelength [A]",
        )

        # Simulate switching to 'total' aggregation
        renderer._intensity_computed_label = "Intensity [n/s]"
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Intensity [n/s]",
            "total aggregation should restore 'Intensity [n/s]'",
        )

    def test_colorbar_label_explicit_api_preserved(self):
        """Explicit colorbar_label from API takes priority over computed label."""

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
            colorbar_label="Custom API Label",
        )
        # Even with a computed label, the explicit API label wins
        renderer._intensity_computed_label = "Wavelength [A]"
        cb = renderer.create_colorbar()
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Custom API Label",
            "explicit API colorbar_label should take priority",
        )

    def test_colorbar_label_component_ignores_intensity_state(self):
        """Component mode label is unaffected by intensity computed label."""

        renderer = PyThreejsRenderer(
            colormode="component",
            num_components=5,
        )
        # Set intensity state that should NOT affect component mode
        renderer._intensity_computed_label = "Wavelength [A]"
        renderer._colorbar_label = "Some Intensity Label"
        cb = renderer.create_colorbar()
        renderer._update_colorbar()
        self.assertEqual(
            renderer._colorbar_cbar.ax.get_ylabel(),
            "Component index",
            "component mode must ignore intensity label state",
        )

class TestPyThreejsCustomColors(unittest.TestCase):
    """Tests for PyThreejsRenderer custom component colors feature."""

    def test_init_without_component_colors(self):
        """Renderer without component_colors should have empty map."""
        renderer = PyThreejsRenderer()
        self.assertEqual(renderer.component_colors_map, {})
        self.assertFalse(renderer._custom_colors_active)
        self.assertIsNone(renderer._custom_colors_checkbox)

    def test_init_with_component_colors(self):
        """Renderer with component_colors should store the mapping."""
        color_map = {"guide1": "#ff0000", "sample": "#00ff00"}
        renderer = PyThreejsRenderer(component_colors=color_map)
        self.assertEqual(renderer.component_colors_map, color_map)
        self.assertFalse(renderer._custom_colors_active)

    def test_create_custom_colors_checkbox_with_map(self):
        """create_custom_colors_checkbox returns a Checkbox when map is provided."""
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(component_colors={"comp1": "#ff0000"})
        checkbox = renderer.create_custom_colors_checkbox()
        self.assertIsInstance(checkbox, ipw.Checkbox)
        self.assertEqual(checkbox.value, False)
        self.assertEqual(checkbox.description, "Custom colors")
        self.assertIs(renderer._custom_colors_checkbox, checkbox)

    def test_create_custom_colors_checkbox_without_map(self):
        """create_custom_colors_checkbox returns None when no map provided."""
        renderer = PyThreejsRenderer()
        checkbox = renderer.create_custom_colors_checkbox()
        self.assertIsNone(checkbox)

    def test_apply_custom_colors(self):
        """_apply_custom_colors applies colors to registered components."""
        renderer = PyThreejsRenderer(component_colors={"test_comp": "#ff0000", "other": "#00ff00"})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        renderer._apply_custom_colors()
        self.assertTrue(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], "#ff0000")

    def test_apply_custom_colors_partial_match(self):
        """Mapped components get custom color; unmapped keep their existing color."""
        renderer = PyThreejsRenderer(component_colors={"comp_a": "#ff0000"})
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        orig_color_b = renderer.component_colors[1]
        renderer._apply_custom_colors()
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        self.assertEqual(renderer.component_colors[1], orig_color_b)

    def test_reset_to_colormode_colors(self):
        """_reset_to_colormode_colors restores default colors."""
        renderer = PyThreejsRenderer(component_colors={"test_comp": "#ff0000"})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        renderer._apply_custom_colors()
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        renderer._reset_to_colormode_colors()
        self.assertFalse(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], DEFAULT_COLORS[0])

    def test_checkbox_toggle_on(self):
        """Checking the checkbox applies custom colors."""
        renderer = PyThreejsRenderer(component_colors={"test_comp": "#ff0000"})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        checkbox = renderer.create_custom_colors_checkbox()
        orig_color = renderer.component_colors[0]
        checkbox.value = True
        self.assertTrue(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], "#ff0000")

    def test_checkbox_toggle_off(self):
        """Unchecking the checkbox resets to colormode colors."""
        renderer = PyThreejsRenderer(component_colors={"test_comp": "#ff0000"})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        checkbox = renderer.create_custom_colors_checkbox()
        checkbox.value = True
        self.assertTrue(renderer._custom_colors_active)
        checkbox.value = False
        self.assertFalse(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], DEFAULT_COLORS[0])

    def test_checkbox_on_only_changes_mapped_components(self):
        """Checking with a single-component map only changes that one component."""
        renderer = PyThreejsRenderer(component_colors={"guide1": "#ff0000"})
        comp1 = make_mock_component("guide1")
        comp1_model = ComponentModel(comp1)
        comp1_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp2 = make_mock_component("sample1")
        comp2_model = ComponentModel(comp2)
        comp2_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp3 = make_mock_component("detector1")
        comp3_model = ComponentModel(comp3)
        comp3_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp1_model)
        renderer.render_component(comp1_model, component_index=0)
        renderer.register_component(comp2_model)
        renderer.render_component(comp2_model, component_index=1)
        renderer.register_component(comp3_model)
        renderer.render_component(comp3_model, component_index=2)
        # Capture pre-check colors
        before = {i: renderer.component_colors[i] for i in renderer.component_colors}
        checkbox = renderer.create_custom_colors_checkbox()
        checkbox.value = True
        # Only mapped component changes
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        self.assertEqual(renderer.component_colors[1], before[1])
        self.assertEqual(renderer.component_colors[2], before[2])

    def test_checkbox_off_restores_colormode(self):
        """Unchecking restores all components to active colormode colors."""
        renderer = PyThreejsRenderer(component_colors={"guide1": "#ff0000"})
        comp1 = make_mock_component("guide1")
        comp1_model = ComponentModel(comp1)
        comp1_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp2 = make_mock_component("sample1")
        comp2_model = ComponentModel(comp2)
        comp2_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp1_model)
        renderer.render_component(comp1_model, component_index=0)
        renderer.register_component(comp2_model)
        renderer.render_component(comp2_model, component_index=1)
        checkbox = renderer.create_custom_colors_checkbox()
        checkbox.value = True
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        checkbox.value = False
        self.assertFalse(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], DEFAULT_COLORS[0])
        self.assertEqual(renderer.component_colors[1], DEFAULT_COLORS[1])

    def test_intensity_mode_unchecked_uses_intensity(self):
        """In intensity mode with checkbox unchecked, all components use intensity colors."""
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"guide1": 1.0, "sample1": 100.0},
            component_colors={"guide1": "#ff0000"},
        )
        comp1 = make_mock_component("guide1")
        comp1_model = ComponentModel(comp1)
        comp1_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp2 = make_mock_component("sample1")
        comp2_model = ComponentModel(comp2)
        comp2_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp1_model)
        renderer.render_component(comp1_model, component_index=0)
        renderer.register_component(comp2_model)
        renderer.render_component(comp2_model, component_index=1)
        # Checkbox is off by default
        checkbox = renderer.create_custom_colors_checkbox()
        self.assertFalse(checkbox.value)
        self.assertFalse(renderer._custom_colors_active)
        # Both components use intensity colors
        self.assertEqual(renderer.component_colors[0],
                         intensity_to_color(1.0, 1.0, 100.0, "inferno", True))
        self.assertEqual(renderer.component_colors[1],
                         intensity_to_color(100.0, 1.0, 100.0, "inferno", True))

    def test_intensity_mode_check_uncheck_roundtrip(self):
        """Intensity mode: check applies custom, uncheck restores intensity colors."""
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"guide1": 1.0, "sample1": 100.0},
            component_colors={"guide1": "#ff0000"},
        )
        comp1 = make_mock_component("guide1")
        comp1_model = ComponentModel(comp1)
        comp1_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp2 = make_mock_component("sample1")
        comp2_model = ComponentModel(comp2)
        comp2_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp1_model)
        renderer.render_component(comp1_model, component_index=0)
        renderer.register_component(comp2_model)
        renderer.render_component(comp2_model, component_index=1)
        checkbox = renderer.create_custom_colors_checkbox()
        # Check: only mapped component changes
        checkbox.value = True
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        intensity_b = intensity_to_color(100.0, 1.0, 100.0, "inferno", True)
        self.assertEqual(renderer.component_colors[1], intensity_b)
        # Uncheck: both restore to intensity colors
        checkbox.value = False
        self.assertFalse(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0],
                         intensity_to_color(1.0, 1.0, 100.0, "inferno", True))
        self.assertEqual(renderer.component_colors[1], intensity_b)

    def test_colormode_change_preserves_custom_colors(self):
        """Colormode change keeps checkbox checked; mapped components retain custom color."""
        renderer = PyThreejsRenderer(
            component_colors={"comp_a": "#ff0000"},
            colormode="component",
            num_components=5,
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        checkbox = renderer.create_custom_colors_checkbox()
        checkbox.value = True
        self.assertTrue(renderer._custom_colors_active)
        renderer.create_colorbar()
        renderer.create_intensity_controls()
        selector = renderer.create_colormode_selector()
        selector.value = "default"
        # Checkbox stays checked, mapped component keeps custom color
        self.assertTrue(renderer._custom_colors_active)
        self.assertTrue(checkbox.value)
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        # Unmapped component follows new colormode (default)
        self.assertEqual(renderer.component_colors[1], DEFAULT_COLORS[1])

    def test_intensity_refresh_preserves_custom_colors(self):
        """Intensity data refresh keeps mapped components at custom color."""
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp_a": 1.0, "comp_b": 100.0},
            component_colors={"comp_a": "#ff0000"},
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        renderer._custom_colors_active = True
        # Simulate intensity refresh: re-recolor all by intensity, then overlay
        new_map = {"comp_a": 50.0, "comp_b": 200.0}
        renderer.intensity_map = new_map
        renderer._min_I = 50.0
        renderer._max_I = 200.0
        for idx in renderer.component_children:
            comp_name = renderer.simple_components[idx]["name"]
            I = new_map.get(comp_name, 0.0)
            color = intensity_to_color(I, 50.0, 200.0, "inferno", True)
            renderer.update_component_color(idx, color)
        renderer._overlay_custom_colors()
        # Mapped component keeps custom color
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        # Unmapped component follows new intensity
        expected_b = intensity_to_color(200.0, 50.0, 200.0, "inferno", True)
        self.assertEqual(renderer.component_colors[1], expected_b)

    def test_grey_all_preserves_custom_colors(self):
        """_grey_all_components greys unmapped but preserves mapped custom colors."""
        renderer = PyThreejsRenderer(component_colors={"comp_a": "#ff0000"})
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        renderer._custom_colors_active = True
        renderer._grey_all_components()
        # Mapped component keeps custom color
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        # Unmapped component is grey
        self.assertEqual(renderer.component_colors[1], "#808080")

    def test_empty_component_colors_no_checkbox(self):
        """Empty dict for component_colors should not create a checkbox."""
        renderer = PyThreejsRenderer(component_colors={})
        checkbox = renderer.create_custom_colors_checkbox()
        self.assertIsNone(checkbox)

    def test_apply_custom_colors_empty_map(self):
        """_apply_custom_colors with empty map is a no-op."""
        renderer = PyThreejsRenderer()
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        orig_color = renderer.component_colors[0]
        renderer._apply_custom_colors()
        self.assertFalse(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], orig_color)

    def test_colormode_color_for_index_default(self):
        """_colormode_color_for_index returns DEFAULT_COLORS in default mode."""
        renderer = PyThreejsRenderer()
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        self.assertEqual(renderer._colormode_color_for_index(0), DEFAULT_COLORS[0])
        self.assertEqual(renderer._colormode_color_for_index(1), DEFAULT_COLORS[1])

    def test_colormode_color_for_index_component_mode(self):
        """_colormode_color_for_index returns viridis colors in component mode."""
        renderer = PyThreejsRenderer(colormode="component", num_components=5)
        c0 = renderer._colormode_color_for_index(0)
        c4 = renderer._colormode_color_for_index(4)
        self.assertNotEqual(c0, c4)
        self.assertEqual(c0, index_to_color(0, 5))
        self.assertEqual(c4, index_to_color(4, 5))

    def test_colormode_color_for_index_intensity_mode(self):
        """_colormode_color_for_index returns intensity colors in intensity mode."""
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp_a": 1.0, "comp_b": 100.0},
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        c_a = renderer._colormode_color_for_index(0)
        c_b = renderer._colormode_color_for_index(1)
        self.assertNotEqual(c_a, c_b)
        self.assertEqual(c_a, intensity_to_color(1.0, 1.0, 100.0, "inferno", True))
        self.assertEqual(c_b, intensity_to_color(100.0, 1.0, 100.0, "inferno", True))

    def test_apply_custom_colors_overlays_on_intensity(self):
        """Custom colors overlay on top of intensity colormode for unmapped components."""
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp_a": 1.0, "comp_b": 100.0},
            component_colors={"comp_a": "#ff0000"},
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        orig_color_b = renderer.component_colors[1]
        renderer._apply_custom_colors()
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        # Unmapped component keeps its pre-existing color
        self.assertEqual(renderer.component_colors[1], orig_color_b)

class TestApiComponentColors(unittest.TestCase):
    def test_get_renderer_pythreejs_passes_component_colors(self):
        """_get_renderer passes component_colors to PyThreejsRenderer."""
        renderer = _get_renderer("pythreejs", component_colors={"a": "#ff0000"})
        self.assertEqual(renderer.component_colors_map, {"a": "#ff0000"})

    def test_view_with_guess_renders_components(self):
        """view_with_guess registers components with the renderer (navigator has entries)."""
        instr = MagicMock()
        comp1 = make_mock_component("guide1")
        comp2 = make_mock_component("sample1")
        instr.component_list = [comp1, comp2]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(instr, backend="pythreejs")
        import ipywidgets as ipw
        self.assertIsInstance(result, ipw.VBox)
        # The navigator is the first child of the top control row.
        controls = result.children[0]
        navigator = controls.children[0]
        self.assertIsInstance(navigator, ipw.Combobox)
        self.assertEqual(len(navigator.options), 2)
        self.assertIn("guide1", navigator.options[0])
        self.assertIn("sample1", navigator.options[1])

    def test_view_with_guess_component_colors_checkbox_works(self):
        """Custom colors checkbox applies colors to rendered components."""
        instr = MagicMock()
        comp1 = make_mock_component("guide1")
        comp2 = make_mock_component("sample1")
        instr.component_list = [comp1, comp2]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(
            instr,
            backend="pythreejs",
            component_colors={"guide1": "#ff0000"},
        )
        import ipywidgets as ipw
        # Locate the custom colors checkbox
        custom_cb = None
        controls = result.children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom colors":
                custom_cb = child
                break
        self.assertIsNotNone(custom_cb)
        self.assertFalse(custom_cb.value)
        # Check the checkbox — should apply custom color to guide1
        custom_cb.value = True
        # The scene/colorbar HBox follows the top control row.
        hbox = result.children[1]
        scene = hbox.children[0]
        # Verify scene has children (rendered geometry)
        self.assertGreater(len(scene.scene.children), 0)

    def test_view_with_guess_no_checkbox_without_colors(self):
        """view_with_guess without component_colors produces no custom colors checkbox."""
        instr = MagicMock()
        comp = make_mock_component("test_comp")
        instr.component_list = [comp]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(instr, backend="pythreejs")
        import ipywidgets as ipw
        self.assertIsInstance(result, ipw.VBox)
        children = result.children
        custom_cb = None
        controls = children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom colors":
                custom_cb = child
                break
        self.assertIsNone(custom_cb)

    def test_view_with_guess_checkbox_present_with_colors(self):
        """view_with_guess with component_colors produces a custom colors checkbox."""
        instr = MagicMock()
        comp = make_mock_component("test_comp")
        instr.component_list = [comp]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(
            instr,
            backend="pythreejs",
            component_colors={"test_comp": "#ff0000"},
        )
        import ipywidgets as ipw
        children = result.children
        custom_cb = None
        controls = children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom colors":
                custom_cb = child
                break
        self.assertIsNotNone(custom_cb)

    def test_view_with_guess_omits_intensity_without_map(self):
        """Guess geometry does not expose an unusable intensity mode."""
        instr = MagicMock()
        instr.component_list = [make_mock_component("test_comp")]
        instr._simulation_parameters = {}
        instr._declared_variables = {}

        result = view_with_guess(instr, backend="pythreejs")
        selector = result.children[0].children[1]

        self.assertNotIn("Intensity", selector.options)

    def test_view_with_guess_keeps_static_intensity_mode(self):
        """Guess geometry can display a caller-supplied intensity map."""
        instr = MagicMock()
        instr.component_list = [make_mock_component("test_comp")]
        instr._simulation_parameters = {}
        instr._declared_variables = {}

        result = view_with_guess(
            instr,
            backend="pythreejs",
            intensity_map={"test_comp": 1.0},
        )
        selector = result.children[0].children[1]

        self.assertIn("Intensity", selector.options)

class TestMaterialIsolation(unittest.TestCase):
    """Tests for component-scoped material isolation in PyThreejsRenderer.

    MaterialLibrary caches pythreejs materials by class/color/properties,
    so multiple components could share one material instance.
    update_component_color() mutates the shared material color, causing
    a custom color or intensity recolor on one component to affect others.

    The fix scopes materials by component_index in the cache key.
    """

    def _render_two_components(self, renderer):
        """Render two box components and return their child lists."""
        comp1 = make_mock_component("comp1")
        model1 = ComponentModel(comp1)
        model1.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model1)
        children1 = renderer.render_component(model1, component_index=0)

        comp2 = make_mock_component("comp2")
        model2 = ComponentModel(comp2)
        model2.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model2)
        children2 = renderer.render_component(model2, component_index=1)
        return children1, children2

    def test_materials_not_shared_between_components(self):
        """Materials for different components must be distinct objects."""
        renderer = PyThreejsRenderer()
        children1, children2 = self._render_two_components(renderer)
        mat1 = children1[0].material
        mat2 = children2[0].material
        self.assertIsNot(mat1, mat2,
                         "Materials from different components must not be the same object")

    def test_changing_one_component_color_does_not_affect_other(self):
        """update_component_color on comp1 must not change comp2's material color."""
        renderer = PyThreejsRenderer()
        children1, children2 = self._render_two_components(renderer)
        orig_color2 = children2[0].material.color
        renderer.update_component_color(0, "#ff0000")
        self.assertEqual(children1[0].material.color, "#ff0000")
        self.assertEqual(children2[0].material.color, orig_color2,
                         "Component 2's material color must not change when component 1 is recolored")

    def test_custom_single_component_mapping_affects_only_that_component(self):
        """Custom color for comp_a must not change comp_b's color."""
        renderer = PyThreejsRenderer(component_colors={"comp_a": "#ff0000"})
        comp_a = make_mock_component("comp_a")
        model_a = ComponentModel(comp_a)
        model_a.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_a)
        renderer.render_component(model_a, component_index=0)

        comp_b = make_mock_component("comp_b")
        model_b = ComponentModel(comp_b)
        model_b.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_b)
        children_b = renderer.render_component(model_b, component_index=1)
        orig_color_b = children_b[0].material.color

        renderer._apply_custom_colors()
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        self.assertEqual(children_b[0].material.color, orig_color_b,
                         "Unmapped component's material must not change")

    def test_intensity_recoloring_isolated_between_components(self):
        """Intensity recoloring of one component must not affect another's material."""
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp1": 1.0, "comp2": 100.0},
        )
        children1, children2 = self._render_two_components(renderer)
        orig_color2 = children2[0].material.color
        new_color = intensity_to_color(50.0, 1.0, 100.0, "inferno", True)
        renderer.update_component_color(0, new_color)
        self.assertEqual(children1[0].material.color, new_color)
        self.assertEqual(children2[0].material.color, orig_color2,
                         "Component 2's material must not change when component 1 is intensity-recolor ed")

    def test_intensity_recoloring_independent_with_checkbox_enabled(self):
        """Intensity recoloring isolation holds when custom colors checkbox is active."""
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp1": 1.0, "comp2": 100.0},
            component_colors={"comp1": "#ff0000"},
        )
        children1, children2 = self._render_two_components(renderer)
        renderer._custom_colors_active = True
        orig_color2 = children2[0].material.color
        renderer.update_component_color(0, "#00ff00")
        self.assertEqual(children2[0].material.color, orig_color2,
                         "Component 2 must not change when component 1 is recolored with checkbox active")

    def test_shapes_within_same_component_share_material(self):
        """Multiple shapes within the same component may share a material."""
        renderer = PyThreejsRenderer()
        comp = make_mock_component("multi_shape")
        model = ComponentModel(comp)
        model.shape_list = [
            BoxShape(width=1, height=1, depth=1),
            BoxShape(width=2, height=2, depth=2),
        ]
        renderer.register_component(model)
        children = renderer.render_component(model, component_index=0)
        # Both shapes are boxes with same material properties, so they share
        self.assertIs(children[0].material, children[1].material,
                      "Shapes within the same component with identical properties should share a material")

    def test_material_library_cache_key_includes_component_index(self):
        """MaterialLibrary cache key must include component_index to ensure isolation."""
        lib = MaterialLibrary(colors=["#ff0000", "#00ff00"])
        mat0 = lib.get_material(component_index=0)
        mat1 = lib.get_material(component_index=1)
        self.assertIsNot(mat0, mat1,
                         "Same color/properties with different component_index must yield different materials")
        # Same component_index should return cached material
        mat0_again = lib.get_material(component_index=0)
        self.assertIs(mat0, mat0_again,
                      "Same component_index should return the cached material")

    def test_material_library_without_component_index(self):
        """Without component_index, materials are cached globally (backward compat)."""
        lib = MaterialLibrary(colors=["#ff0000", "#00ff00"])
        mat1 = lib.get_material()
        mat2 = lib.get_material()
        self.assertIs(mat1, mat2,
                      "Without component_index, same color/properties should share cached material")

    def test_update_component_color_reflects_in_component_colors_dict(self):
        """update_component_color updates both the material and component_colors dict."""
        renderer = PyThreejsRenderer()
        children1, _ = self._render_two_components(renderer)
        renderer.update_component_color(0, "#ff0000")
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        self.assertEqual(children1[0].material.color, "#ff0000")

    def test_multiple_components_same_color_independent(self):
        """Even when components happen to have the same color, materials are independent."""
        # Force same color by using a small color palette
        renderer = PyThreejsRenderer(colors=["#aaaaaa"])
        children1, children2 = self._render_two_components(renderer)
        self.assertEqual(children1[0].material.color, "#aaaaaa")
        self.assertEqual(children2[0].material.color, "#aaaaaa")
        self.assertIsNot(children1[0].material, children2[0].material,
                         "Same color across components must still yield distinct material objects")
        renderer.update_component_color(0, "#ff0000")
        self.assertEqual(children1[0].material.color, "#ff0000")
        self.assertEqual(children2[0].material.color, "#aaaaaa")

class TestNcountDropdownAndLabel(unittest.TestCase):
    """Tests for ncount dropdown option and 'N rays' colorbar label."""

    def test_aggregate_dropdown_includes_ncount(self):
        """Aggregate dropdown includes 'ncount' option mapping to 'ncount'."""
        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        renderer.create_intensity_controls()
        agg_widget = renderer._intensity_widgets["aggregate"]
        self.assertIn("ncount", agg_widget.options.keys())
        self.assertEqual(agg_widget.options["ncount"], "ncount")

    def test_aggregate_dropdown_still_has_all_original_options(self):
        """Adding ncount does not remove any existing aggregate options."""
        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        renderer.create_intensity_controls()
        agg_widget = renderer._intensity_widgets["aggregate"]
        expected = {"total", "min", "max", "average", "median", "span", "ncount"}
        self.assertEqual(set(agg_widget.options.keys()), expected)

    def test_ncount_colorbar_label_in_apply_intensity(self):
        """_apply_intensity_from_data sets 'N rays' label for ncount aggregation."""
        from unittest.mock import patch

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        renderer.create_intensity_controls()
        renderer.create_colorbar()

        # Set up mock diagnostic data
        mock_data = MagicMock()
        mock_data.metadata.dimension = 0
        mock_data.metadata.total_I = 100.0
        mock_data.metadata.total_N = 500.0
        mock_data.Intensity = np.array([100.0])
        mock_data.Ncount = np.array([500.0])
        mock_data.xaxis = np.array([0.0])
        mock_data.metadata.xlabel = None

        renderer._diag_data = [mock_data]
        renderer._diag_monitors = [("mon1", "comp_a")]
        renderer._diag_data_dim = 0
        renderer._data_stale = False
        renderer.intensity_map = {"comp_a": 1.0}
        renderer.simple_components = [{"name": "comp_a"}]
        renderer.component_children = {0: []}

        with patch("mcstasscript.interface.functions.name_search", return_value=mock_data):
            renderer._apply_intensity_from_data("ncount")
        self.assertEqual(renderer._intensity_computed_label, "N rays")

    def test_cached_aggregate_refresh_ncount(self):
        """Changing aggregate dropdown to ncount re-applies from cached data."""
        from unittest.mock import patch

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        renderer.create_intensity_controls()
        renderer.create_colorbar()

        # Set up mock diagnostic data
        mock_data = MagicMock()
        mock_data.metadata.dimension = 1
        mock_data.metadata.total_I = 100.0
        mock_data.metadata.total_N = 500.0
        mock_data.Intensity = np.array([10.0, 20.0, 30.0])
        mock_data.Ncount = np.array([100.0, 200.0, 200.0])
        mock_data.xaxis = np.array([1.0, 2.0, 3.0])
        mock_data.metadata.xlabel = "wavelength"

        renderer._diag_data = [mock_data]
        renderer._diag_monitors = [("mon1", "comp_a")]
        renderer._diag_data_dim = 1
        renderer._data_stale = False
        renderer.intensity_map = {"comp_a": 1.0}
        renderer.simple_components = [{"name": "comp_a"}]
        renderer.component_children = {0: []}

        with patch("mcstasscript.interface.functions.name_search", return_value=mock_data):
            # Simulate aggregate dropdown change to ncount
            agg_widget = renderer._intensity_widgets["aggregate"]
            agg_widget.value = "ncount"

        self.assertEqual(renderer._intensity_computed_label, "N rays")
        self.assertEqual(renderer.intensity_map["comp_a"], 500.0)

    def test_cached_aggregate_refresh_total_after_ncount(self):
        """Switching from ncount back to total restores 'Intensity [n/s]' label."""
        from unittest.mock import patch

        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0, "b": 10.0},
            colormode="intensity",
        )
        renderer.create_intensity_controls()
        renderer.create_colorbar()

        mock_data = MagicMock()
        mock_data.metadata.dimension = 1
        mock_data.metadata.total_I = 100.0
        mock_data.metadata.total_N = 500.0
        mock_data.Intensity = np.array([10.0, 20.0, 30.0])
        mock_data.Ncount = np.array([100.0, 200.0, 200.0])
        mock_data.xaxis = np.array([1.0, 2.0, 3.0])
        mock_data.metadata.xlabel = "wavelength"

        renderer._diag_data = [mock_data]
        renderer._diag_monitors = [("mon1", "comp_a")]
        renderer._diag_data_dim = 1
        renderer._data_stale = False
        renderer.intensity_map = {"comp_a": 1.0}
        renderer.simple_components = [{"name": "comp_a"}]
        renderer.component_children = {0: []}

        with patch("mcstasscript.interface.functions.name_search", return_value=mock_data):
            # Switch to ncount
            agg_widget = renderer._intensity_widgets["aggregate"]
            agg_widget.value = "ncount"
            self.assertEqual(renderer._intensity_computed_label, "N rays")

            # Switch back to total
            agg_widget.value = "total"
            self.assertEqual(renderer._intensity_computed_label, "Intensity [n/s]")

class TestNcountPreservesExistingBehavior(unittest.TestCase):
    def test_default_aggregate_is_still_total(self):
        """Default aggregate value in dropdown is still 'total'."""
        renderer = PyThreejsRenderer(
            intensity_map={"a": 1.0},
            colormode="intensity",
        )
        renderer.create_intensity_controls()
        agg_widget = renderer._intensity_widgets["aggregate"]
        self.assertEqual(agg_widget.value, "total")

    def test_custom_colors_unaffected_by_ncount(self):
        """Custom colors overlay works correctly when ncount aggregation is active."""
        from unittest.mock import patch

        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp_a": 1.0, "comp_b": 100.0},
            component_colors={"comp_a": "#ff0000"},
        )
        comp_a = make_mock_component("comp_a")
        model_a = ComponentModel(comp_a)
        model_a.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        model_b = ComponentModel(comp_b)
        model_b.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_a)
        renderer.render_component(model_a, component_index=0)
        renderer.register_component(model_b)
        renderer.render_component(model_b, component_index=1)
        renderer.create_colorbar()

        # Set up mock diagnostic data with ncount
        mock_data = MagicMock()
        mock_data.metadata.dimension = 0
        mock_data.metadata.total_I = 100.0
        mock_data.metadata.total_N = 500.0
        mock_data.Intensity = np.array([100.0])
        mock_data.Ncount = np.array([500.0])
        mock_data.xaxis = np.array([0.0])
        mock_data.metadata.xlabel = None

        renderer._diag_data = [mock_data]
        renderer._diag_monitors = [("mon1", "comp_a")]
        renderer._diag_data_dim = 0
        renderer._data_stale = False
        renderer.simple_components = [
            {"name": "comp_a"},
            {"name": "comp_b"},
        ]
        renderer.component_children = {0: [], 1: []}

        with patch("mcstasscript.interface.functions.name_search", return_value=mock_data):
            # Apply ncount aggregation
            renderer._apply_intensity_from_data("ncount")
        self.assertEqual(renderer._intensity_computed_label, "N rays")

        # Now enable custom colors
        renderer._custom_colors_active = True
        renderer._overlay_custom_colors()
        self.assertEqual(renderer.component_colors[0], "#ff0000")

class TestPyThreejsCustomOpacities(unittest.TestCase):
    """Tests for PyThreejsRenderer custom component opacities feature."""

    def test_init_without_component_opacity(self):
        """Renderer without component_opacity should have empty map."""
        renderer = PyThreejsRenderer()
        self.assertEqual(renderer.component_opacity_map, {})
        self.assertFalse(renderer._custom_opacities_active)
        self.assertIsNone(renderer._custom_opacities_checkbox)

    def test_init_with_component_opacity(self):
        """Renderer with component_opacity should store the mapping."""
        opacity_map = {"guide1": 0.3, "sample": 0.7}
        renderer = PyThreejsRenderer(component_opacity=opacity_map)
        self.assertEqual(renderer.component_opacity_map, opacity_map)
        self.assertFalse(renderer._custom_opacities_active)

    def test_init_validates_non_numeric_value(self):
        """Non-numeric opacity values should raise TypeError."""
        with self.assertRaises(TypeError):
            PyThreejsRenderer(component_opacity={"guide1": "0.5"})

    def test_init_validates_out_of_range_value(self):
        """Opacity values outside [0.0, 1.0] should raise ValueError."""
        with self.assertRaises(ValueError):
            PyThreejsRenderer(component_opacity={"guide1": 1.5})
        with self.assertRaises(ValueError):
            PyThreejsRenderer(component_opacity={"guide1": -0.1})

    def test_init_converts_int_to_float(self):
        """Integer opacity values should be converted to float."""
        renderer = PyThreejsRenderer(component_opacity={"guide1": 0, "sample": 1})
        self.assertEqual(renderer.component_opacity_map, {"guide1": 0.0, "sample": 1.0})

    def test_create_custom_opacities_checkbox_with_map(self):
        """create_custom_opacities_checkbox returns a Checkbox when map is provided."""
        import ipywidgets as ipw
        renderer = PyThreejsRenderer(component_opacity={"comp1": 0.5})
        checkbox = renderer.create_custom_opacities_checkbox()
        self.assertIsInstance(checkbox, ipw.Checkbox)
        self.assertEqual(checkbox.value, False)
        self.assertEqual(checkbox.description, "Custom opacity")
        self.assertIs(renderer._custom_opacities_checkbox, checkbox)

    def test_create_custom_opacities_checkbox_without_map(self):
        """create_custom_opacities_checkbox returns None when no map provided."""
        renderer = PyThreejsRenderer()
        checkbox = renderer.create_custom_opacities_checkbox()
        self.assertIsNone(checkbox)

    def test_apply_custom_opacities(self):
        """_apply_custom_opacities applies opacities to registered components."""
        renderer = PyThreejsRenderer(component_opacity={"test_comp": 0.3})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        renderer._apply_custom_opacities()
        self.assertTrue(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], 0.3)

    def test_apply_custom_opacities_partial_match(self):
        """Mapped components get custom opacity; unmapped keep their existing opacity."""
        renderer = PyThreejsRenderer(component_opacity={"comp_a": 0.2})
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        orig_opacity_b = renderer.component_opacity[1]
        renderer._apply_custom_opacities()
        self.assertEqual(renderer.component_opacity[0], 0.2)
        self.assertEqual(renderer.component_opacity[1], orig_opacity_b)

    def test_reset_to_base_opacities(self):
        """_reset_to_base_opacities restores original opacities."""
        renderer = PyThreejsRenderer(component_opacity={"test_comp": 0.3})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        orig_opacity = renderer.component_opacity[0]
        renderer._apply_custom_opacities()
        self.assertEqual(renderer.component_opacity[0], 0.3)
        renderer._reset_to_base_opacities()
        self.assertFalse(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], orig_opacity)

    def test_checkbox_toggle_on(self):
        """Checking the checkbox applies custom opacities."""
        renderer = PyThreejsRenderer(component_opacity={"test_comp": 0.25})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        checkbox = renderer.create_custom_opacities_checkbox()
        orig_opacity = renderer.component_opacity[0]
        checkbox.value = True
        self.assertTrue(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], 0.25)

    def test_checkbox_toggle_off(self):
        """Unchecking the checkbox resets to base opacities."""
        renderer = PyThreejsRenderer(component_opacity={"test_comp": 0.25})
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        orig_opacity = renderer.component_opacity[0]
        checkbox = renderer.create_custom_opacities_checkbox()
        checkbox.value = True
        self.assertTrue(renderer._custom_opacities_active)
        checkbox.value = False
        self.assertFalse(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], orig_opacity)

    def test_checkbox_on_only_changes_mapped_components(self):
        """Checking with a single-component map only changes that one component."""
        renderer = PyThreejsRenderer(component_opacity={"guide1": 0.15})
        comp1 = make_mock_component("guide1")
        comp1_model = ComponentModel(comp1)
        comp1_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp2 = make_mock_component("sample1")
        comp2_model = ComponentModel(comp2)
        comp2_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp3 = make_mock_component("detector1")
        comp3_model = ComponentModel(comp3)
        comp3_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp1_model)
        renderer.render_component(comp1_model, component_index=0)
        renderer.register_component(comp2_model)
        renderer.render_component(comp2_model, component_index=1)
        renderer.register_component(comp3_model)
        renderer.render_component(comp3_model, component_index=2)
        before = {i: renderer.component_opacity[i] for i in renderer.component_opacity}
        checkbox = renderer.create_custom_opacities_checkbox()
        checkbox.value = True
        self.assertEqual(renderer.component_opacity[0], 0.15)
        self.assertEqual(renderer.component_opacity[1], before[1])
        self.assertEqual(renderer.component_opacity[2], before[2])

    def test_checkbox_off_restores_base_opacity(self):
        """Unchecking restores all components to base opacity."""
        renderer = PyThreejsRenderer(component_opacity={"guide1": 0.15})
        comp1 = make_mock_component("guide1")
        comp1_model = ComponentModel(comp1)
        comp1_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp2 = make_mock_component("sample1")
        comp2_model = ComponentModel(comp2)
        comp2_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp1_model)
        renderer.render_component(comp1_model, component_index=0)
        renderer.register_component(comp2_model)
        renderer.render_component(comp2_model, component_index=1)
        orig_op1 = renderer.component_opacity[0]
        orig_op2 = renderer.component_opacity[1]
        checkbox = renderer.create_custom_opacities_checkbox()
        checkbox.value = True
        self.assertEqual(renderer.component_opacity[0], 0.15)
        checkbox.value = False
        self.assertFalse(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], orig_op1)
        self.assertEqual(renderer.component_opacity[1], orig_op2)

    def test_empty_component_opacity_no_checkbox(self):
        """Empty dict for component_opacity should not create a checkbox."""
        renderer = PyThreejsRenderer(component_opacity={})
        checkbox = renderer.create_custom_opacities_checkbox()
        self.assertIsNone(checkbox)

    def test_apply_custom_opacities_empty_map(self):
        """_apply_custom_opacities with empty map is a no-op."""
        renderer = PyThreejsRenderer()
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        orig_opacity = renderer.component_opacity[0]
        renderer._apply_custom_opacities()
        self.assertFalse(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], orig_opacity)

    def test_opacity_preserves_color(self):
        """Applying custom opacity must not change the component's color."""
        renderer = PyThreejsRenderer(
            component_colors={"test_comp": "#ff0000"},
            component_opacity={"test_comp": 0.3},
        )
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        renderer._apply_custom_colors()
        renderer._apply_custom_opacities()
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        self.assertEqual(renderer.component_opacity[0], 0.3)

    def test_opacity_independent_of_colors(self):
        """Custom opacity checkbox is independent from custom colors checkbox."""
        renderer = PyThreejsRenderer(
            component_colors={"test_comp": "#ff0000"},
            component_opacity={"test_comp": 0.3},
        )
        comp = make_mock_component("test_comp")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        color_cb = renderer.create_custom_colors_checkbox()
        opacity_cb = renderer.create_custom_opacities_checkbox()
        self.assertIsNotNone(color_cb)
        self.assertIsNotNone(opacity_cb)
        self.assertIsNot(color_cb, opacity_cb)
        # Enable only opacity
        opacity_cb.value = True
        self.assertTrue(renderer._custom_opacities_active)
        self.assertFalse(renderer._custom_colors_active)
        self.assertEqual(renderer.component_opacity[0], 0.3)
        # Enable only color
        opacity_cb.value = False
        color_cb.value = True
        self.assertFalse(renderer._custom_opacities_active)
        self.assertTrue(renderer._custom_colors_active)
        self.assertEqual(renderer.component_colors[0], "#ff0000")

    def test_grey_all_preserves_custom_opacities(self):
        """_grey_all_components greys unmapped but preserves mapped custom opacities."""
        renderer = PyThreejsRenderer(component_opacity={"comp_a": 0.1})
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        renderer._custom_opacities_active = True
        renderer._grey_all_components()
        self.assertEqual(renderer.component_opacity[0], 0.1)
        # Unmapped component keeps its original opacity (not changed by grey)
        self.assertEqual(renderer.component_colors[1], "#808080")

    def test_intensity_refresh_preserves_custom_opacities(self):
        """Intensity data refresh keeps mapped components at custom opacity."""
        renderer = PyThreejsRenderer(
            colormode="intensity",
            intensity_map={"comp_a": 1.0, "comp_b": 100.0},
            component_opacity={"comp_a": 0.2},
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        orig_op_b = renderer.component_opacity[1]
        renderer._custom_opacities_active = True
        # Simulate intensity refresh: re-recolor all by intensity, then overlay
        new_map = {"comp_a": 50.0, "comp_b": 200.0}
        renderer.intensity_map = new_map
        renderer._min_I = 50.0
        renderer._max_I = 200.0
        for idx in renderer.component_children:
            comp_name = renderer.simple_components[idx]["name"]
            I = new_map.get(comp_name, 0.0)
            color = intensity_to_color(I, 50.0, 200.0, "inferno", True)
            renderer.update_component_color(idx, color)
        renderer._overlay_custom_opacities()
        self.assertEqual(renderer.component_opacity[0], 0.2)
        self.assertEqual(renderer.component_opacity[1], orig_op_b)

    def test_colormode_change_preserves_custom_opacities(self):
        """Colormode change keeps checkbox checked; mapped components retain custom opacity."""
        renderer = PyThreejsRenderer(
            component_opacity={"comp_a": 0.15},
            colormode="component",
            num_components=5,
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        comp_b = make_mock_component("comp_b")
        comp_b_model = ComponentModel(comp_b)
        comp_b_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        renderer.register_component(comp_b_model)
        renderer.render_component(comp_b_model, component_index=1)
        checkbox = renderer.create_custom_opacities_checkbox()
        checkbox.value = True
        self.assertTrue(renderer._custom_opacities_active)
        renderer.create_colorbar()
        renderer.create_intensity_controls()
        selector = renderer.create_colormode_selector()
        selector.value = "default"
        self.assertTrue(renderer._custom_opacities_active)
        self.assertTrue(checkbox.value)
        self.assertEqual(renderer.component_opacity[0], 0.15)

    def test_update_component_opacity_sets_material(self):
        """update_component_opacity sets material.opacity and material.transparent."""
        renderer = PyThreejsRenderer()
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        children = renderer.render_component(comp_model, component_index=0)
        mesh = children[0]
        orig_opacity = mesh.material.opacity
        renderer.update_component_opacity(0, 0.25)
        self.assertEqual(mesh.material.opacity, 0.25)
        self.assertTrue(mesh.material.transparent)
        # Color should be unchanged
        orig_color = mesh.material.color
        renderer.update_component_opacity(0, 0.9)
        self.assertEqual(mesh.material.color, orig_color)

    def test_original_opacity_captured_at_render(self):
        """Original opacity is captured from rendered mesh at render time."""
        renderer = PyThreejsRenderer()
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        # BoxShape renders with opacity 0.8
        self.assertAlmostEqual(renderer.component_opacity[0], 0.8)

    def test_reset_restores_shape_specific_opacity(self):
        """Reset restores the shape-specific opacity (e.g., 0.8 for box)."""
        renderer = PyThreejsRenderer(component_opacity={"test": 0.1})
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        self.assertAlmostEqual(renderer.component_opacity[0], 0.8)
        renderer._apply_custom_opacities()
        self.assertEqual(renderer.component_opacity[0], 0.1)
        renderer._reset_to_base_opacities()
        self.assertAlmostEqual(renderer.component_opacity[0], 0.8)

    def test_reset_restores_each_shape_opacity(self):
        """A component with mixed shapes restores every base opacity."""
        renderer = PyThreejsRenderer(component_opacity={"test": 0.1})
        comp = make_mock_component("test")
        comp_model = ComponentModel(comp)
        comp_model.shape_list = [
            BoxShape(width=1.0, height=1.0, depth=1.0),
            CylinderShape(radius=1.0, height=2.0),
        ]
        renderer.register_component(comp_model)
        children = renderer.render_component(comp_model, component_index=0)
        base = [child.material.opacity for child in children]

        renderer._apply_custom_opacities()
        self.assertEqual([child.material.opacity for child in children], [0.1, 0.1])
        renderer._reset_to_base_opacities()
        self.assertEqual([child.material.opacity for child in children], base)

    def test_cylinder_shape_specific_opacity(self):
        """Cylinder opacity is size-based and correctly captured."""
        renderer = PyThreejsRenderer()
        comp = make_mock_component("cyl")
        comp_model = ComponentModel(comp)
        # Large cylinder -> smaller opacity
        comp_model.shape_list = [CylinderShape(radius=1.0, height=2.0)]
        renderer.register_component(comp_model)
        renderer.render_component(comp_model, component_index=0)
        # largest_dim = max(2*1.0, 2.0) = 2.0 -> > 1.5 -> opacity 0.4
        self.assertAlmostEqual(renderer.component_opacity[0], 0.4)

    def test_both_color_and_opacity_together(self):
        """Custom colors and opacities can be active simultaneously."""
        renderer = PyThreejsRenderer(
            component_colors={"comp_a": "#ff0000"},
            component_opacity={"comp_a": 0.2},
        )
        comp_a = make_mock_component("comp_a")
        comp_a_model = ComponentModel(comp_a)
        comp_a_model.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(comp_a_model)
        renderer.render_component(comp_a_model, component_index=0)
        color_cb = renderer.create_custom_colors_checkbox()
        opacity_cb = renderer.create_custom_opacities_checkbox()
        color_cb.value = True
        opacity_cb.value = True
        self.assertTrue(renderer._custom_colors_active)
        self.assertTrue(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_colors[0], "#ff0000")
        self.assertEqual(renderer.component_opacity[0], 0.2)
        # Disable color, keep opacity
        color_cb.value = False
        self.assertFalse(renderer._custom_colors_active)
        self.assertTrue(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_opacity[0], 0.2)
        # Disable opacity, keep color
        opacity_cb.value = False
        color_cb.value = True
        self.assertTrue(renderer._custom_colors_active)
        self.assertFalse(renderer._custom_opacities_active)
        self.assertEqual(renderer.component_colors[0], "#ff0000")

class TestApiComponentOpacities(unittest.TestCase):
    def test_get_renderer_pythreejs_passes_component_opacity(self):
        """_get_renderer passes component_opacity to PyThreejsRenderer."""
        renderer = _get_renderer("pythreejs", component_opacity={"a": 0.5})
        self.assertEqual(renderer.component_opacity_map, {"a": 0.5})

    def test_view_with_guess_component_opacity_checkbox_works(self):
        """Custom opacity checkbox applies opacities to rendered components."""
        instr = MagicMock()
        comp1 = make_mock_component("guide1")
        comp2 = make_mock_component("sample1")
        instr.component_list = [comp1, comp2]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(
            instr,
            backend="pythreejs",
            component_opacity={"guide1": 0.3},
        )
        import ipywidgets as ipw
        custom_cb = None
        controls = result.children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom opacity":
                custom_cb = child
                break
        self.assertIsNotNone(custom_cb)
        self.assertFalse(custom_cb.value)
        custom_cb.value = True
        hbox = result.children[1]
        scene = hbox.children[0]
        self.assertGreater(len(scene.scene.children), 0)

    def test_view_with_guess_no_opacity_checkbox_without_opacities(self):
        """view_with_guess without component_opacity produces no custom opacity checkbox."""
        instr = MagicMock()
        comp = make_mock_component("test_comp")
        instr.component_list = [comp]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(instr, backend="pythreejs")
        import ipywidgets as ipw
        children = result.children
        custom_cb = None
        controls = children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom opacity":
                custom_cb = child
                break
        self.assertIsNone(custom_cb)

    def test_view_with_guess_opacity_checkbox_present_with_opacities(self):
        """view_with_guess with component_opacity produces a custom opacity checkbox."""
        instr = MagicMock()
        comp = make_mock_component("test_comp")
        instr.component_list = [comp]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(
            instr,
            backend="pythreejs",
            component_opacity={"test_comp": 0.5},
        )
        import ipywidgets as ipw
        children = result.children
        custom_cb = None
        controls = children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom opacity":
                custom_cb = child
                break
        self.assertIsNotNone(custom_cb)

    def test_view_with_guess_both_checkboxes_independent(self):
        """Both custom colors and custom opacity checkboxes appear when both mappings provided."""
        instr = MagicMock()
        comp = make_mock_component("test_comp")
        instr.component_list = [comp]
        instr._simulation_parameters = {}
        instr._declared_variables = {}
        result = view_with_guess(
            instr,
            backend="pythreejs",
            component_colors={"test_comp": "#ff0000"},
            component_opacity={"test_comp": 0.5},
        )
        import ipywidgets as ipw
        color_cb = None
        opacity_cb = None
        controls = result.children[0]
        for child in controls.children:
            if isinstance(child, ipw.Checkbox) and child.description == "Custom colors":
                color_cb = child
            elif isinstance(child, ipw.Checkbox) and child.description == "Custom opacity":
                opacity_cb = child
        self.assertIsNotNone(color_cb)
        self.assertIsNotNone(opacity_cb)
        self.assertIsNot(color_cb, opacity_cb)

class TestMaterialIsolationOpacity(unittest.TestCase):
    """Tests for component-scoped material isolation with opacity changes."""

    def test_changing_one_component_opacity_does_not_affect_other(self):
        """update_component_opacity on comp1 must not change comp2's material opacity."""
        renderer = PyThreejsRenderer()
        comp1 = make_mock_component("comp1")
        model1 = ComponentModel(comp1)
        model1.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model1)
        children1 = renderer.render_component(model1, component_index=0)

        comp2 = make_mock_component("comp2")
        model2 = ComponentModel(comp2)
        model2.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model2)
        children2 = renderer.render_component(model2, component_index=1)

        orig_opacity2 = children2[0].material.opacity
        renderer.update_component_opacity(0, 0.1)
        self.assertEqual(children1[0].material.opacity, 0.1)
        self.assertEqual(children2[0].material.opacity, orig_opacity2,
                         "Component 2's material opacity must not change")

    def test_custom_single_component_opacity_affects_only_that_component(self):
        """Custom opacity for comp_a must not change comp_b's opacity."""
        renderer = PyThreejsRenderer(component_opacity={"comp_a": 0.15})
        comp_a = make_mock_component("comp_a")
        model_a = ComponentModel(comp_a)
        model_a.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_a)
        renderer.render_component(model_a, component_index=0)

        comp_b = make_mock_component("comp_b")
        model_b = ComponentModel(comp_b)
        model_b.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_b)
        children_b = renderer.render_component(model_b, component_index=1)
        orig_opacity_b = children_b[0].material.opacity

        renderer._apply_custom_opacities()
        self.assertEqual(renderer.component_opacity[0], 0.15)
        self.assertEqual(children_b[0].material.opacity, orig_opacity_b,
                         "Unmapped component's material must not change")

    def test_custom_opacity_does_not_affect_color(self):
        """Applying custom opacity must not mutate the material color."""
        renderer = PyThreejsRenderer(component_opacity={"comp_a": 0.15})
        comp_a = make_mock_component("comp_a")
        model_a = ComponentModel(comp_a)
        model_a.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_a)
        children = renderer.render_component(model_a, component_index=0)
        orig_color = children[0].material.color
        renderer._apply_custom_opacities()
        self.assertEqual(children[0].material.color, orig_color)

    def test_custom_color_does_not_affect_opacity(self):
        """Applying custom color must not mutate the material opacity."""
        renderer = PyThreejsRenderer(component_colors={"comp_a": "#ff0000"})
        comp_a = make_mock_component("comp_a")
        model_a = ComponentModel(comp_a)
        model_a.shape_list = [BoxShape(width=1, height=1, depth=1)]
        renderer.register_component(model_a)
        children = renderer.render_component(model_a, component_index=0)
        orig_opacity = children[0].material.opacity
        renderer._apply_custom_colors()
        self.assertEqual(children[0].material.opacity, orig_opacity)

class TestSphereShape(unittest.TestCase):
    def test_pythreejs_render(self):
        """PyThreejsRenderer can render a SphereShape."""
        renderer = PyThreejsRenderer()
        renderer._temp_color = None  # Initialize for standalone render_shape
        shape = SphereShape(radius=0.5)
        result = renderer.render_shape(shape)
        self.assertIsNotNone(result)
