import os
import io
import unittest
import unittest.mock
import copy
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from mcstasscript.tests.helpers_for_tests import WorkInTestDir
from mcstasscript.interface.instr import McStas_instr
from mcstasscript.helper.mcstas_objects import Component, DeclareVariable
from mcstasscript.data.data import McStasMetaData, McStasDataEvent
from mcstasscript.instrument_diagnostics.view import View
from mcstasscript.instrument_diagnostics.diagnostics_instrument import DiagnosticsInstrument
from mcstasscript.instrument_diagnostics.beam_diagnostics import (
    BeamDiagnostics, DiagnosticsPoint, sanitise_comp_name
)
from mcstasscript.instrument_diagnostics.intensity_diagnostics import (
    IntensityDiagnostics, common_range_limits
)
from mcstasscript.instrument_diagnostics.event_plotter import EventPlotter
from mcstasscript.instrument_diagnostics.plot_overview import PlotOverview


def setup_instr_no_path():
    """
    Sets up a neutron instrument without a package_path
    """
    with WorkInTestDir() as handler:
        instrument = McStas_instr("test_instrument")
    return instrument


def setup_populated_instr():
    """
    Sets up a neutron instrument with parameters, declare vars and three components
    """
    instr = setup_instr_no_path()
    instr.add_parameter("double", "theta")
    instr.add_declare_var("double", "two_theta")
    instr.append_initialize("two_theta = 2.0*theta;")
    instr.add_component("first_component", "test_for_reading")
    instr.add_component("second_component", "test_for_reading")
    instr.add_component("third_component", "test_for_reading")
    return instr


def setup_instr_with_flags():
    """
    Sets up a populated instrument with two extra variables usable as flags
    """
    instr = setup_populated_instr()
    instr.add_declare_var("double", "my_flag1")
    instr.add_user_var("double", "my_flag2")
    return instr


def setup_instr_with_dummy_path():
    """
    Sets up a populated instrument using the dummy McStas installation,
    so that Monitor_nD is available as a component type
    """
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    dummy_path = os.path.join(THIS_DIR, "dummy_mcstas")
    with WorkInTestDir() as handler:
        instrument = McStas_instr("test_instrument",
                                  package_path=dummy_path, executable_path=dummy_path)
    instr = instrument
    instr.add_parameter("double", "theta")
    instr.add_declare_var("double", "two_theta")
    instr.append_initialize("two_theta = 2.0*theta;")
    instr.add_component("first_component", "test_for_reading")
    instr.add_component("second_component", "test_for_reading")
    instr.add_component("third_component", "test_for_reading")
    return instr


def make_dummy_event_data(n_events=100, variables="t x y z vx vy vz p U1 U2 U3"):
    """
    Creates a dummy McStasDataEvent object with random event data
    """
    metadata = McStasMetaData()
    metadata.component_name = "test_monitor"
    metadata.info["variables"] = variables
    n_cols = len(variables.split())
    events = np.random.rand(n_events, n_cols)
    events[:, 7] = 1.0
    events[:, 2:] = 100.0
    return McStasDataEvent(metadata, events)


class TestView(unittest.TestCase):
    """
    Tests for the View class which defines plot axis specifications
    """

    def test_1d_view_init(self):
        """
        Check that a 1D view initialises with correct default attributes
        """
        view = View(axis1="x", bins=50)
        self.assertEqual(view.axis1, "x")
        self.assertIsNone(view.axis2)
        self.assertEqual(view.bins, 50)
        self.assertFalse(view.same_scale)
        self.assertIsNone(view.axis1_limits)
        self.assertIsNone(view.axis2_limits)

    def test_2d_view_init(self):
        """
        Check that a 2D view stores axis2 and same_scale correctly
        """
        view = View(axis1="x", axis2="y", bins=[50, 60], same_scale=True)
        self.assertEqual(view.axis1, "x")
        self.assertEqual(view.axis2, "y")
        self.assertEqual(view.bins, [50, 60])
        self.assertTrue(view.same_scale)

    def test_axis1_values_single_float(self):
        """
        Check that a single float for axis1_values is wrapped into a list
        """
        view = View(axis1="x", axis1_values=0.5)
        self.assertEqual(view.axis1_values, [0.5])

    def test_axis1_values_list(self):
        """
        Check that a list of axis1_values is stored as-is
        """
        view = View(axis1="x", axis1_values=[0.1, 0.2, 0.3])
        self.assertEqual(view.axis1_values, [0.1, 0.2, 0.3])

    def test_axis2_values_single_int(self):
        """
        Check that a single int for axis2_values is wrapped into a list
        """
        view = View(axis1="x", axis2="y", axis2_values=42)
        self.assertEqual(view.axis2_values, [42])

    def test_axis1_values_none(self):
        """
        Check that None for axis1_values remains None (not wrapped)
        """
        view = View(axis1="x", axis1_values=None)
        self.assertIsNone(view.axis1_values)

    def test_plot_options_passed_through(self):
        """
        Check that extra kwargs are stored in plot_options dict
        """
        view = View(axis1="x", cmap="viridis", log=True)
        self.assertEqual(view.plot_options, {"cmap": "viridis", "log": True})

    def test_repr_1d(self):
        """
        Check that __repr__ of a 1D view contains axis and bin info
        """
        view = View(axis1="x", bins=100)
        r = repr(view)
        self.assertIn("View (x)", r)
        self.assertIn("bins: 100", r)

    def test_repr_2d(self):
        """
        Check that __repr__ of a 2D view contains both axes and bin info
        """
        view = View(axis1="x", axis2="y", bins=50)
        r = repr(view)
        self.assertIn("View (x, y)", r)
        self.assertIn("bins: 50", r)

    def test_set_axis1_limits(self):
        """
        Check that set_axis1_limits stores the limits tuple correctly
        """
        view = View(axis1="x")
        view.set_axis1_limits(0.0, 1.0)
        self.assertEqual(view.axis1_limits, (0.0, 1.0))

    def test_set_axis2_limits(self):
        """
        Check that set_axis2_limits stores the limits tuple correctly
        """
        view = View(axis1="x", axis2="y")
        view.set_axis2_limits(-1.0, 1.0)
        self.assertEqual(view.axis2_limits, (-1.0, 1.0))

    def test_set_axis1_limits_reversed_raises(self):
        """
        Check that set_axis1_limits raises ValueError when start > end
        """
        view = View(axis1="x")
        with self.assertRaises(ValueError):
            view.set_axis1_limits(1.0, 0.0)

    def test_set_axis2_limits_reversed_raises(self):
        """
        Check that set_axis2_limits raises ValueError when start > end
        """
        view = View(axis1="x", axis2="y")
        with self.assertRaises(ValueError):
            view.set_axis2_limits(1.0, 0.0)

    def test_clear_limits(self):
        """
        Check that clear_limits resets both axis limits to None
        """
        view = View(axis1="x", axis2="y")
        view.set_axis1_limits(0.0, 1.0)
        view.set_axis2_limits(-1.0, 1.0)
        view.clear_limits()
        self.assertIsNone(view.axis1_limits)
        self.assertIsNone(view.axis2_limits)


class TestDiagnosticsPoint(unittest.TestCase):
    """
    Tests for the DiagnosticsPoint class which represents a beam
    diagnostics measurement point before or after a component
    """

    def test_init_before(self):
        """
        Check that a before-point initialises with correct attributes
        """
        instr = setup_populated_instr()
        point = DiagnosticsPoint(instr, "first_component", before=True, rays=1000)
        self.assertEqual(point.component, "first_component")
        self.assertTrue(point.before)
        self.assertEqual(point.rays, 1000)
        self.assertIsNone(point.filename)
        self.assertIsNone(point.recorded_rays)

    def test_init_after(self):
        """
        Check that an after-point with rays='all' initialises correctly
        """
        instr = setup_populated_instr()
        point = DiagnosticsPoint(instr, "first_component", before=False, rays="all")
        self.assertEqual(point.component, "first_component")
        self.assertFalse(point.before)
        self.assertEqual(point.rays, "all")

    def test_init_invalid_component_raises(self):
        """
        Check that initialising with a non-existent component raises NameError
        """
        instr = setup_populated_instr()
        with self.assertRaises(NameError):
            DiagnosticsPoint(instr, "nonexistent_component")

    def test_init_invalid_rays_raises(self):
        """
        Check that rays must be an integer or the string 'all'
        """
        instr = setup_populated_instr()
        with self.assertRaises(ValueError):
            DiagnosticsPoint(instr, "first_component", rays="invalid")

    def test_set_filename(self):
        """
        Check that set_filename stores the given filename string
        """
        instr = setup_populated_instr()
        point = DiagnosticsPoint(instr, "first_component")
        point.set_filename("test.diag")
        self.assertEqual(point.filename, "test.diag")

    def test_set_recorded_rays(self):
        """
        Check that set_recorded_rays stores the given ray count
        """
        instr = setup_populated_instr()
        point = DiagnosticsPoint(instr, "first_component")
        point.set_recorded_rays(500)
        self.assertEqual(point.recorded_rays, 500)

    def test_eq_same_point(self):
        """
        Check that two points on the same component and side are equal,
        regardless of their rays setting
        """
        instr = setup_populated_instr()
        p1 = DiagnosticsPoint(instr, "first_component", before=True, rays=1000)
        p2 = DiagnosticsPoint(instr, "first_component", before=True, rays=2000)
        self.assertEqual(p1, p2)

    def test_eq_different_component(self):
        """
        Check that points on different components are not equal
        """
        instr = setup_populated_instr()
        p1 = DiagnosticsPoint(instr, "first_component", before=True)
        p2 = DiagnosticsPoint(instr, "second_component", before=True)
        self.assertNotEqual(p1, p2)

    def test_eq_different_before_after(self):
        """
        Check that before and after points on the same component are not equal
        """
        instr = setup_populated_instr()
        p1 = DiagnosticsPoint(instr, "first_component", before=True)
        p2 = DiagnosticsPoint(instr, "first_component", before=False)
        self.assertNotEqual(p1, p2)

    def test_repr_without_recorded_rays(self):
        """
        Check that __repr__ shows component name and requested rays when
        no data has been recorded yet
        """
        instr = setup_populated_instr()
        point = DiagnosticsPoint(instr, "first_component", before=True, rays=50000)
        r = repr(point)
        self.assertIn("before:", r)
        self.assertIn("first_component", r)
        self.assertIn("50000", r)

    def test_repr_with_recorded_rays(self):
        """
        Check that __repr__ shows both recorded and requested ray counts
        when data has been read
        """
        instr = setup_populated_instr()
        point = DiagnosticsPoint(instr, "first_component", before=True, rays=50000)
        point.set_recorded_rays(49999)
        r = repr(point)
        self.assertIn("49999", r)
        self.assertIn("50000", r)


class TestSanitiseCompName(unittest.TestCase):
    """
    Tests for the sanitise_comp_name helper function
    """

    def test_string_passthrough(self):
        """
        Check that a plain string component name is returned unchanged
        """
        result = sanitise_comp_name("my_component")
        self.assertEqual(result, "my_component")

    def test_invalid_type_raises(self):
        """
        Check that passing a non-string, non-Component value raises ValueError
        """
        with self.assertRaises(ValueError):
            sanitise_comp_name(123)


class TestDiagnosticsInstrument(unittest.TestCase):
    """
    Tests for the DiagnosticsInstrument base class which manages a
    deep-copied instrument for diagnostics modifications
    """

    def test_init_deep_copies_instrument(self):
        """
        Check that initialisation creates a deep copy of the instrument
        while keeping a reference to the original
        """
        instr = setup_populated_instr()
        diag = DiagnosticsInstrument(instr)
        self.assertIsNot(diag.instr, instr)
        self.assertIs(diag.original_instr, instr)

    def test_modify_copy_doesnt_affect_original(self):
        """
        Check that adding components to the diagnostics copy does not
        change the original instrument
        """
        instr = setup_populated_instr()
        diag = DiagnosticsInstrument(instr)
        original_count = len(instr.make_component_subset())
        diag.instr.add_component("extra_comp", "test_for_reading")
        self.assertEqual(len(instr.make_component_subset()), original_count)

    def test_settings_persist_across_reset(self):
        """
        Check that settings applied via .settings() survive a reset_instr call
        """
        instr = setup_populated_instr()
        diag = DiagnosticsInstrument(instr)
        diag.settings(ncount=1000)
        diag.reset_instr()
        self.assertIn("ncount", diag.instr_settings)
        self.assertEqual(diag.instr_settings["ncount"], 1000)

    def test_parameters_persist_across_reset(self):
        """
        Check that parameters applied via .set_parameters() survive a reset
        """
        instr = setup_populated_instr()
        diag = DiagnosticsInstrument(instr)
        diag.set_parameters(theta=1.5)
        diag.reset_instr()
        self.assertIn("theta", diag.instr_parameters)

    def test_remove_previous_use_replaces_references(self):
        """
        Check that remove_previous_use replaces PREVIOUS references in AT
        and ROTATED with actual component names
        """
        with WorkInTestDir() as handler:
            instr = McStas_instr("test_prev_instr")
            A = instr.add_component("A", "test_for_reading")
            B = instr.add_component("B", "test_for_reading")
            C = instr.add_component("C", "test_for_reading")
            B.set_AT(0, RELATIVE="PREVIOUS")
            C.set_ROTATED([0, 90, 0], RELATIVE="PREVIOUS")

        diag = DiagnosticsInstrument(instr)
        diag.remove_previous_use()

        b_comp = diag.instr.get_component("B")
        c_comp = diag.instr.get_component("C")
        self.assertNotEqual(b_comp.AT_reference, "PREVIOUS")
        self.assertNotEqual(c_comp.ROTATED_reference, "PREVIOUS")


class TestBeamDiagnostics(unittest.TestCase):
    """
    Tests for the BeamDiagnostics class which sets up event monitors at
    selected points along the beam path
    """

    def test_init(self):
        """
        Check that a new BeamDiagnostics object starts with empty lists
        and no data
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        self.assertEqual(diag.points, [])
        self.assertEqual(diag.views, [])
        self.assertEqual(diag.flags, [])
        self.assertIsNone(diag.data)

    def test_repr_no_points_no_views(self):
        """
        Check that __repr__ reports empty state when no points or views added
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        r = repr(diag)
        self.assertIn("test_instrument", r)
        self.assertIn("No diagnostics points yet", r)
        self.assertIn("No views yet", r)
        self.assertIn("Does not yet contain simulated data", r)

    def test_add_point_before(self):
        """
        Check that add_point with before= creates a DiagnosticsPoint
        with before=True
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        diag.add_point(before="first_component")
        self.assertEqual(len(diag.points), 1)
        self.assertTrue(diag.points[0].before)
        self.assertEqual(diag.points[0].component, "first_component")

    def test_add_point_after(self):
        """
        Check that add_point with after= creates a DiagnosticsPoint
        with before=False
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        diag.add_point(after="second_component")
        self.assertEqual(len(diag.points), 1)
        self.assertFalse(diag.points[0].before)
        self.assertEqual(diag.points[0].component, "second_component")

    def test_add_point_both_before_and_after(self):
        """
        Check that add_point accepts both before= and after= simultaneously,
        creating two separate points
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        diag.add_point(before="first_component", after="second_component")
        self.assertEqual(len(diag.points), 2)

    def test_add_point_neither_raises(self):
        """
        Check that add_point raises ValueError when neither before nor
        after is specified
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        with self.assertRaises(ValueError):
            diag.add_point()

    def test_add_point_overwrites_existing(self):
        """
        Check that adding a point at an already-tracked location replaces
        the existing point rather than creating a duplicate
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        diag.add_point(before="first_component", rays=1000)
        diag.add_point(before="first_component", rays=2000)
        self.assertEqual(len(diag.points), 1)
        self.assertEqual(diag.points[0].rays, 2000)

    def test_remove_point_before(self):
        """
        Check that remove_point with before= removes the correct point
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        diag.add_point(before="first_component")
        diag.add_point(before="second_component")
        diag.remove_point(before="first_component")
        self.assertEqual(len(diag.points), 1)
        self.assertEqual(diag.points[0].component, "second_component")

    def test_remove_point_after(self):
        """
        Check that remove_point with after= removes the correct point
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        diag.add_point(after="first_component")
        diag.add_point(after="second_component")
        diag.remove_point(after="first_component")
        self.assertEqual(len(diag.points), 1)
        self.assertEqual(diag.points[0].component, "second_component")

    def test_remove_point_neither_raises(self):
        """
        Check that remove_point raises ValueError when neither before nor
        after is specified
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        with self.assertRaises(ValueError):
            diag.remove_point()

    def test_clear_points(self):
        """
        Check that clear_points removes all diagnostics points
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        diag.add_point(before="first_component")
        diag.add_point(after="second_component")
        diag.clear_points()
        self.assertEqual(len(diag.points), 0)

    def test_add_flag_valid(self):
        """
        Check that add_flag accepts a variable name from declare_list
        """
        instr = setup_instr_with_flags()
        diag = BeamDiagnostics(instr)
        diag.add_flag("my_flag1")
        self.assertEqual(diag.flags, ["my_flag1"])

    def test_add_flag_from_user_var(self):
        """
        Check that add_flag accepts a variable name from user_var_list
        """
        instr = setup_instr_with_flags()
        diag = BeamDiagnostics(instr)
        diag.add_flag("my_flag2")
        self.assertEqual(diag.flags, ["my_flag2"])

    def test_add_flag_not_string_raises(self):
        """
        Check that add_flag raises ValueError for non-string input
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        with self.assertRaises(ValueError):
            diag.add_flag(123)

    def test_add_flag_not_in_instrument_raises(self):
        """
        Check that add_flag raises ValueError for a variable not declared
        in the instrument
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        with self.assertRaises(ValueError):
            diag.add_flag("nonexistent_var")

    def test_add_flag_max_three(self):
        """
        Check that add_flag enforces a maximum of three flags
        """
        instr = setup_instr_with_flags()
        diag = BeamDiagnostics(instr)
        diag.add_flag("my_flag1")
        diag.add_flag("my_flag2")
        diag.add_flag("two_theta")
        with self.assertRaises(ValueError):
            diag.add_flag("theta")

    def test_clear_flags(self):
        """
        Check that clear_flags empties the flags list
        """
        instr = setup_instr_with_flags()
        diag = BeamDiagnostics(instr)
        diag.add_flag("my_flag1")
        diag.clear_flags()
        self.assertEqual(diag.flags, [])

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_flags(self, mock_stdout):
        """
        Check that show_flags prints each flag with its user index
        """
        instr = setup_instr_with_flags()
        diag = BeamDiagnostics(instr)
        diag.add_flag("my_flag1")
        diag.add_flag("my_flag2")
        diag.show_flags()
        output = mock_stdout.getvalue()
        self.assertIn("user1=my_flag1", output)
        self.assertIn("user2=my_flag2", output)

    def test_add_view(self):
        """
        Check that add_view creates a View with the specified parameters
        and appends it to the views list
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        diag.add_view(axis1="x", axis2="y", bins=50, same_scale=True)
        self.assertEqual(len(diag.views), 1)
        self.assertEqual(diag.views[0].axis1, "x")
        self.assertEqual(diag.views[0].axis2, "y")
        self.assertTrue(diag.views[0].same_scale)

    def test_clear_views(self):
        """
        Check that clear_views removes all views
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        diag.add_view(axis1="x")
        diag.add_view(axis1="t", axis2="l")
        diag.clear_views()
        self.assertEqual(len(diag.views), 0)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_points(self, mock_stdout):
        """
        Check that show_points prints each diagnostics point to stdout
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        diag.add_point(before="first_component")
        diag.show_points()
        output = mock_stdout.getvalue()
        self.assertIn("first_component", output)

    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_show_views(self, mock_stdout):
        """
        Check that show_views prints each view to stdout
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        diag.add_view(axis1="x")
        diag.show_views()
        output = mock_stdout.getvalue()
        self.assertIn("View (x)", output)

    def test_add_monitors_ordered_by_component_sequence(self):
        """
        Check that add_monitors orders the diagnostics points according to
        their position in the instrument component sequence, regardless of
        the order they were added
        """
        instr = setup_instr_with_dummy_path()
        diag = BeamDiagnostics(instr)
        diag.add_point(before="third_component")
        diag.add_point(before="first_component")
        diag.add_point(before="second_component")
        diag.add_monitors()
        point_names = [p.component for p in diag.ordered_point_list]
        self.assertEqual(point_names, ["first_component", "second_component", "third_component"])

    def test_add_monitors_creates_monitor_components(self):
        """
        Check that add_monitors creates Monitor_nD components and sets the
        filename on each diagnostics point
        """
        instr = setup_instr_with_dummy_path()
        diag = BeamDiagnostics(instr)
        diag.add_point(before="first_component")
        diag.add_monitors()
        self.assertEqual(len(diag.ordered_point_list), 1)
        self.assertEqual(diag.ordered_point_list[0].filename, "Diag_before_first_component")

    def test_add_monitors_after_point(self):
        """
        Check that add_monitors creates a monitor with the correct name
        for an after-point
        """
        instr = setup_instr_with_dummy_path()
        diag = BeamDiagnostics(instr)
        diag.add_point(after="first_component")
        diag.add_monitors()
        self.assertEqual(diag.ordered_point_list[0].filename, "Diag_after_first_component")

    def test_repr_with_data(self):
        """
        Check that __repr__ reports data present when the data attribute
        has been set
        """
        instr = setup_populated_instr()
        diag = BeamDiagnostics(instr)
        diag.data = ["dummy"]
        r = repr(diag)
        self.assertIn("Does contain simulated data", r)


class TestCommonRangeLimits(unittest.TestCase):
    """
    Tests for the common_range_limits helper function which computes
    matching log-scale axis limits for intensity and ray count plots
    """

    def test_basic_case(self):
        """
        Check that the function returns two lists of length 2 with valid
        ordered limits for typical data
        """
        I = [1e6, 5e5, 1e5, 1e4]
        N = [1e7, 5e6, 1e6, 1e5]
        I_limits, N_limits = common_range_limits(I, N)
        self.assertIsInstance(I_limits, list)
        self.assertIsInstance(N_limits, list)
        self.assertEqual(len(I_limits), 2)
        self.assertEqual(len(N_limits), 2)
        self.assertTrue(I_limits[0] < I_limits[1])
        self.assertTrue(N_limits[0] < N_limits[1])

    def test_with_zeros(self):
        """
        Check that the function correctly filters out zero values before
        computing log-scale limits
        """
        I = [1e6, 0, 1e4, 0]
        N = [1e7, 0, 1e5, 0]
        I_limits, N_limits = common_range_limits(I, N)
        self.assertTrue(I_limits[0] > 0)
        self.assertTrue(N_limits[0] > 0)

    def test_intensity_larger_range(self):
        """
        Check that both axes end up with the same number of orders of
        magnitude when intensity has the larger range
        """
        I = [1e10, 1e-2]
        N = [1e3, 1e2]
        I_limits, N_limits = common_range_limits(I, N)
        I_range = np.log10(I_limits[1]) - np.log10(I_limits[0])
        N_range = np.log10(N_limits[1]) - np.log10(N_limits[0])
        self.assertAlmostEqual(I_range, N_range, places=0)

    def test_ray_count_larger_range(self):
        """
        Check that both axes end up with the same number of orders of
        magnitude when ray count has the larger range
        """
        I = [1e3, 1e2]
        N = [1e10, 1e-2]
        I_limits, N_limits = common_range_limits(I, N)
        I_range = np.log10(I_limits[1]) - np.log10(I_limits[0])
        N_range = np.log10(N_limits[1]) - np.log10(N_limits[0])
        self.assertAlmostEqual(I_range, N_range, places=0)

    def test_numpy_array_input(self):
        """
        Check that the function accepts numpy arrays as input and still
        returns plain lists
        """
        I = np.array([1e6, 1e5, 1e4])
        N = np.array([1e7, 1e6, 1e5])
        I_limits, N_limits = common_range_limits(I, N)
        self.assertIsInstance(I_limits, list)


class TestEventPlotter(unittest.TestCase):
    """
    Tests for the EventPlotter class which wraps event data and produces
    plots from View specifications
    """

    def test_init(self):
        """
        Check that an EventPlotter stores its name, data reference, and
        flag_info correctly
        """
        data = make_dummy_event_data()
        plotter = EventPlotter("test_name", data, flag_info=["my_var"])
        self.assertEqual(plotter.name, "test_name")
        self.assertIs(plotter.data, data)
        self.assertEqual(plotter.flag_info, ["my_var"])

    def test_scale_weights(self):
        """
        Check that scale_weights multiplies all event weights (p column)
        by the given factor in-place
        """
        data = make_dummy_event_data()
        original_p = data.Events[:, 7].copy()
        plotter = EventPlotter("test", data)
        plotter.scale_weights(2.0)
        np.testing.assert_array_almost_equal(data.Events[:, 7], original_p * 2.0)

    def test_get_view_limits_axis1(self):
        """
        Check that get_view_limits_axis1 returns valid min/max for the
        data column specified by the view's axis1
        """
        data = make_dummy_event_data()
        plotter = EventPlotter("test", data)
        view = View(axis1="x")
        lim_min, lim_max = plotter.get_view_limits_axis1(view)
        self.assertIsInstance(lim_min, float)
        self.assertIsInstance(lim_max, float)
        self.assertLessEqual(lim_min, lim_max)

    def test_get_view_limits_axis2_returns_nan_for_1d(self):
        """
        Check that get_view_limits_axis2 returns (nan, nan) when the view
        has no axis2 defined
        """
        data = make_dummy_event_data()
        plotter = EventPlotter("test", data)
        view = View(axis1="x")
        lim_min, lim_max = plotter.get_view_limits_axis2(view)
        self.assertTrue(np.isnan(lim_min))
        self.assertTrue(np.isnan(lim_max))

    def test_get_view_limits_axis2(self):
        """
        Check that get_view_limits_axis2 returns valid min/max when the
        view has an axis2 defined
        """
        data = make_dummy_event_data()
        plotter = EventPlotter("test", data)
        view = View(axis1="x", axis2="y")
        lim_min, lim_max = plotter.get_view_limits_axis2(view)
        self.assertFalse(np.isnan(lim_min))
        self.assertFalse(np.isnan(lim_max))


class TestPlotOverview(unittest.TestCase):
    """
    Tests for the PlotOverview class which coordinates plotting of multiple
    views across multiple event plotters
    """

    def test_init(self):
        """
        Check that PlotOverview stores the correct number of points and plots
        from its input lists
        """
        data = make_dummy_event_data()
        plotters = [EventPlotter("test1", data), EventPlotter("test2", data)]
        views = [View(axis1="x"), View(axis1="t", axis2="l")]
        overview = PlotOverview(plotters, views)
        self.assertEqual(overview.n_points, 2)
        self.assertEqual(overview.n_plots, 2)

    def test_set_same_scale(self):
        """
        Check that set_same_scale computes global limits for a view with
        same_scale=True
        """
        data = make_dummy_event_data()
        plotters = [EventPlotter("test1", data), EventPlotter("test2", data)]
        view = View(axis1="x", same_scale=True)
        overview = PlotOverview(plotters, [view])
        overview.set_same_scale()
        self.assertIsNotNone(view.axis1_limits)

    def test_set_same_scale_respects_opt_out(self):
        """
        Check that set_same_scale skips views with same_scale=False
        """
        data = make_dummy_event_data()
        plotters = [EventPlotter("test1", data), EventPlotter("test2", data)]
        view = View(axis1="x", same_scale=False)
        overview = PlotOverview(plotters, [view])
        overview.set_same_scale()
        self.assertIsNone(view.axis1_limits)

    def test_set_same_scale_2d(self):
        """
        Check that set_same_scale computes limits for both axes on a 2D view
        """
        data = make_dummy_event_data()
        plotters = [EventPlotter("test1", data), EventPlotter("test2", data)]
        view = View(axis1="x", axis2="y", same_scale=True)
        overview = PlotOverview(plotters, [view])
        overview.set_same_scale()
        self.assertIsNotNone(view.axis1_limits)
        self.assertIsNotNone(view.axis2_limits)


class TestIntensityDiagnostics(unittest.TestCase):
    """
    Tests for the IntensityDiagnostics class which places 0D or 1D
    intensity monitors before each component
    """

    def test_init(self):
        """
        Check that a new IntensityDiagnostics object starts with no data,
        undefined dimensionality, and no monitors
        """
        instr = setup_populated_instr()
        diag = IntensityDiagnostics(instr)
        self.assertIsNone(diag.data)
        self.assertIsNone(diag.data_dim)
        self.assertIsNone(diag.monitors)

    def test_add_monitor(self):
        """
        Check that add_monitor creates a Monitor_nD component with the
        expected naming convention before the given component
        """
        instr = setup_instr_with_dummy_path()
        diag = IntensityDiagnostics(instr)
        comp = diag.instr.get_component("second_component")
        options = '"square boarders intensity"'
        name = diag.add_monitor(before=comp, options=options)
        self.assertEqual(name, "I_before_second_component")

    def test_run_general_limits_validation(self):
        """
        Check that run_general raises TypeError when limits is not a list
        """
        instr = setup_populated_instr()
        diag = IntensityDiagnostics(instr)
        with self.assertRaises(TypeError):
            diag.run_general(variable="x", limits="invalid")

    def test_run_general_limits_wrong_length(self):
        """
        Check that run_general raises TypeError when limits list does not
        have exactly two elements
        """
        instr = setup_populated_instr()
        diag = IntensityDiagnostics(instr)
        with self.assertRaises(TypeError):
            diag.run_general(variable="x", limits=[1.0])


if __name__ == "__main__":
    unittest.main()
