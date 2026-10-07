import unittest
import unittest.mock
import io
import numpy as np

import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg

from mcstasscript.jb_interface.plot_interface import PlotInterface
from mcstasscript.jb_interface.plot_interface import LogCheckbox
from mcstasscript.jb_interface.plot_interface import ColormapDropdown
from mcstasscript.jb_interface.plot_interface import OrdersOfMagField

from mcstasscript.data.data import McStasMetaData
from mcstasscript.data.data import McStasDataBinned

import ipywidgets as widgets

def set_dummy_MetaDataBinned_1d():
    """
    Sets up simple McStasMetaData object with dimension, 1d case
    """
    meta_data = McStasMetaData()
    meta_data.component_name = "component for 1d"
    meta_data.dimension = 50

    meta_data.limits = [0, 1]
    meta_data.xlabel = ""
    meta_data.ylabel = ""
    meta_data.title = ""
    meta_data.filename = "dummy"

    return meta_data


def set_dummy_McStasDataBinned_1d():
    """
    Sets up simple McStasData object, 1d case
    """
    meta_data = set_dummy_MetaDataBinned_1d()

    intensity = np.arange(20)
    error = 0.5 * np.arange(20)
    ncount = 2 * np.arange(20)
    axis = np.arange(20)*5.0

    return McStasDataBinned(meta_data, intensity, error, ncount, xaxis=axis)


def set_dummy_MetaDataBinned_2d():
    """
    Sets up simple McStasMetaData object with dimensions, 2d case
    """
    meta_data = McStasMetaData()
    meta_data.component_name = "test a component"
    meta_data.dimension = [5, 4]

    meta_data.limits = [0, 1, 0, 1]
    meta_data.xlabel = ""
    meta_data.ylabel = ""
    meta_data.title = ""
    meta_data.filename = "dummy"

    return meta_data


def set_dummy_McStasDataBinned_2d():
    """
    Sets up simple McStasData object, 2d case
    """
    meta_data = set_dummy_MetaDataBinned_2d()

    intensity = np.arange(20).reshape(4, 5)
    error = 0.5 * np.arange(20).reshape(4, 5)
    ncount = 2 * np.arange(20).reshape(4, 5)

    return McStasDataBinned(meta_data, intensity, error, ncount)


def fake_data():
    return [set_dummy_McStasDataBinned_1d(),
            set_dummy_McStasDataBinned_2d(),
            set_dummy_McStasDataBinned_2d()]


class FakeChange:
    def __init__(self, new=None, old=None, name=None):
        self.new = new
        self.old = old
        self.name = name


class TestPlotInterface(unittest.TestCase):
    """
    Test of PlotInterface, mainly the set functions.
    Each set function does run the main update_plot function, ensuring
    this does not throw obvious errors under a mixed set of circumstances.
    The update_plot function is not tested directly.
    """
    def test_initialization_without_data(self):
        """
        Initialize PlotterInterface without arguments
        """

        interface = PlotInterface()
        self.assertEqual(interface.data, None)

    def test_initialization_with_data(self):
        """
        Initialize PlotterInterface with data
        """
        data = fake_data()
        interface = PlotInterface(data)

        self.assertEqual(len(interface.data), 3)
        self.assertEqual(interface.data[0].Intensity[5], 5)
        self.assertEqual(interface.data[1].Intensity[2, 3], 13)

    def test_show_interface_return(self):
        """
        Ensure the show_interface method returns a widget of type HBox
        """
        interface = PlotInterface()
        widget = interface.show_interface()

        self.assertIsInstance(widget, widgets.widgets.widget_box.HBox)

    def test_set_data(self):
        """
        Initialize PlotterInterface without data, add later and ensure
        monitor_dropdown received the data and applied it to widget options.

        Furthermore the widget options should be made unique as there are
        two identical monitors in the fake data.
        """

        interface = PlotInterface()
        self.assertEqual(interface.data, None)

        interface.show_interface() # Needed to set up monitor_dropdown

        interface.set_data(fake_data())
        self.assertEqual(len(interface.data), 3)
        self.assertEqual(interface.data[0].Intensity[5], 5)
        self.assertEqual(interface.data[1].Intensity[2, 3], 13)

        mon_drop = interface.monitor_dropdown
        self.assertEqual(len(mon_drop.data), 3)
        self.assertEqual(mon_drop.data[0].Intensity[5], 5)
        self.assertEqual(mon_drop.data[1].Intensity[2, 3], 13)

        self.assertEqual(mon_drop.widget.options[0], "component for 1d")
        self.assertEqual(mon_drop.widget.options[1], "test a component")

        # The last monitor is identical to the second, so the name is modified
        self.assertEqual(mon_drop.widget.options[2], "test a component_1")

    def test_set_current_monitor(self):
        """
        Check monitor can be set and that error occurs if wrong name given
        """

        interface = PlotInterface(fake_data())
        interface.show_interface()

        interface.set_current_monitor("test a component")
        self.assertEqual(interface.current_monitor, "test a component")

        with self.assertRaises(NameError):
            interface.set_current_monitor("component that doesnt exist")

    def test_set_log_mode(self):
        """
        Check that set_log_mode works, even through widget
        """

        interface = PlotInterface()
        interface.show_interface()

        self.assertFalse(interface.log_mode)
        interface.set_log_mode(True)
        self.assertTrue(interface.log_mode)

        log_checkbox = LogCheckbox(interface.log_mode, interface.set_log_mode)

        fake_change = FakeChange(new=False)

        log_checkbox.update(fake_change)
        self.assertFalse(interface.log_mode)

    def test_set_orders_of_mag(self):
        """
        Check that set orders of mag works, even through widget
        """
        interface = PlotInterface()
        interface.show_interface()

        interface.set_orders_of_mag(37)
        self.assertEqual(interface.orders_of_mag, 37)

        log_orders_of_mag = OrdersOfMagField(interface.set_orders_of_mag)

        fake_change = FakeChange(new=42)

        log_orders_of_mag.update(fake_change)
        self.assertEqual(interface.orders_of_mag, 42)

    def test_set_colormap(self):
        """
        Check that set_colormap works, even through widget
        """
        interface = PlotInterface()
        interface.show_interface()

        interface.set_colormap("hot")
        self.assertEqual(interface.colormap, "hot")

        colormap_dropdown = ColormapDropdown(interface.set_colormap)

        fake_change = FakeChange(new="Purples")
        colormap_dropdown.update_cmap(fake_change)
        self.assertEqual(interface.colormap, "Purples")





