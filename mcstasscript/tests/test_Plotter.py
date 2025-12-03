import unittest
import unittest.mock

import matplotlib
matplotlib.use('Agg')

import numpy as np
import matplotlib.pyplot as plt

from mcstasscript.data.data import McStasDataBinned
from mcstasscript.data.data import McStasMetaData
from mcstasscript.interface.plotter import _find_min_max_I
from mcstasscript.interface.plotter import _handle_kwargs
from mcstasscript.interface.plotter import _plot_fig_ax
from mcstasscript.interface.plotter import make_plot, make_sub_plot, make_animation


def get_dummy_MetaDataBinned_1d():
    meta_data = McStasMetaData()
    meta_data.component_name = "component for 1d"
    meta_data.dimension = 50
    meta_data.limits = [0.1, 1.1]
    meta_data.title = "test"
    meta_data.xlabel = "test x"
    meta_data.ylabel = "test y"

    return meta_data


def get_dummy_McStasDataBinned_1d():
    meta_data = get_dummy_MetaDataBinned_1d()

    intensity = np.arange(20) + 5
    error = 0.5 * np.arange(20)
    ncount = 2 * np.arange(20)
    axis = np.arange(20)*5.0

    return McStasDataBinned(meta_data, intensity, error, ncount, xaxis=axis)


def get_dummy_MetaDataBinned_2d():
    meta_data = McStasMetaData()
    meta_data.component_name = "test a component"
    meta_data.dimension = [5, 4]
    meta_data.limits = [0.1, 1.1, 2.0, 4.0]
    meta_data.title = "test"
    meta_data.xlabel = "test x"
    meta_data.ylabel = "test y"

    return meta_data


def get_dummy_McStasDataBinned_2d():
    meta_data = get_dummy_MetaDataBinned_2d()

    intensity = np.arange(20).reshape(4, 5) + 5
    error = 0.5 * np.arange(20).reshape(4, 5)
    ncount = 2 * np.arange(20).reshape(4, 5)

    return McStasDataBinned(meta_data, intensity, error, ncount)


class TestPlotterHelpers(unittest.TestCase):
    """
    Tests of plotter help functions
    """

    def test_find_min_max_I_simple_1D_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set
        """

        dummy_data = get_dummy_McStasDataBinned_1d()
        found_min, found_max = _find_min_max_I(dummy_data)

        # np.arange(20) + 5: min = 5, max = 5+19 = 24
        self.assertEqual(found_min, 5)
        self.assertEqual(found_max, 19 + 5)

    def test_find_min_max_I_cut_max_1D_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here cut_max is used to limit the maximum plotted.
        """

        dummy_data = get_dummy_McStasDataBinned_1d()
        dummy_data.set_plot_options(cut_max=0.8)
        found_min, found_max = _find_min_max_I(dummy_data)

        # np.arange(20) + 5: min = 5, max = 5+19 = 24
        self.assertEqual(found_min, 5)
        self.assertEqual(found_max, (19 + 5)*0.8)

    def test_find_min_max_I_cut_min_1D_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here cut_min is used to limit the minimum plotted.
        """

        dummy_data = get_dummy_McStasDataBinned_1d()
        dummy_data.set_plot_options(cut_min=0.2)
        found_min, found_max = _find_min_max_I(dummy_data)

        # np.arange(20) + 5: min = 5, max = 5+19 = 24
        self.assertEqual(found_min, 5 + (24-5)*0.2)
        self.assertEqual(found_max, 19 + 5)

    def test_find_min_max_I_log_with_zero_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here a bin contains zero intensity and log mode is enabled,
        since log(0) is not allowed, this data point should be
        ignored.
        """

        dummy_data = get_dummy_McStasDataBinned_1d()
        dummy_data.Intensity[5] = 0
        dummy_data.set_plot_options(log=True)
        found_min, found_max = _find_min_max_I(dummy_data)

        # np.arange(20) + 5: min = 5, max = 5+19 = 24
        self.assertAlmostEqual(found_min, 5)
        self.assertAlmostEqual(found_max, 19 + 5)

    def test_find_min_max_I_log_cut_max_1D_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here cut_max is used to limit the maximum plotted while
        log mode is enabled.
        """

        dummy_data = get_dummy_McStasDataBinned_1d()
        dummy_data.set_plot_options(cut_max=0.8, log=True)
        found_min, found_max = _find_min_max_I(dummy_data)

        # np.arange(20) + 5: min = 5, max = 5+19 = 24
        self.assertAlmostEqual(found_min, 5)
        self.assertAlmostEqual(found_max, (19 + 5)*0.8)

    def test_find_min_max_I_log_cut_min_1D_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here cut_min is used to limit the minimum plotted while
        log mode is enabled.
        """

        dummy_data = get_dummy_McStasDataBinned_1d()
        dummy_data.set_plot_options(cut_min=0.2, log=True)
        found_min, found_max = _find_min_max_I(dummy_data)

        # np.arange(20) + 5: min = 5, max = 5+19 = 24
        self.assertAlmostEqual(found_min, 5 + (24-5)*0.2)
        self.assertAlmostEqual(found_max, 19 + 5)

    def test_find_min_max_I_log_orders_of_mag_1D_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here orders_of_mag is used to limit the minimum plotted
        while log mode is enabled.
        """

        dummy_data = get_dummy_McStasDataBinned_1d()
        dummy_data.Intensity[5] = 10**6
        dummy_data.set_plot_options(log=True, orders_of_mag=3)
        found_min, found_max = _find_min_max_I(dummy_data)

        self.assertAlmostEqual(found_min, 10**3)
        self.assertAlmostEqual(found_max, 10**6)

    def test_find_min_max_I_log_orders_of_mag_1D_with_zero_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here orders_of_mag is used to limit the minimum plotted
        while log mode is enabled. A bin in the data contains
        zero intensity, which should be ignored.
        """

        dummy_data = get_dummy_McStasDataBinned_1d()
        dummy_data.Intensity[5] = 10**6
        dummy_data.Intensity[6] = 0
        dummy_data.set_plot_options(log=True, orders_of_mag=3)
        found_min, found_max = _find_min_max_I(dummy_data)

        self.assertAlmostEqual(found_min, 10**3)
        self.assertAlmostEqual(found_max, 10**6)

    def test_find_min_max_I_simple_2D_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set
        """

        dummy_data = get_dummy_McStasDataBinned_2d()
        found_min, found_max = _find_min_max_I(dummy_data)

        # np.arange(20) + 5: min = 5, max = 5+19 = 24
        self.assertEqual(found_min, 5)
        self.assertEqual(found_max, 19 + 5)

    def test_find_min_max_I_cut_max_2D_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here cut_max is used to limit the maximum plotted.
        """

        dummy_data = get_dummy_McStasDataBinned_2d()
        dummy_data.set_plot_options(cut_max=0.8)
        found_min, found_max = _find_min_max_I(dummy_data)

        # np.arange(20) + 5: min = 5, max = 5+19 = 24
        self.assertEqual(found_min, 5)
        self.assertEqual(found_max, (19 + 5)*0.8)

    def test_find_min_max_I_cut_min_2D_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here cut_min is used to limit the minimum plotted.
        """

        dummy_data = get_dummy_McStasDataBinned_2d()
        dummy_data.set_plot_options(cut_min=0.2)
        found_min, found_max = _find_min_max_I(dummy_data)

        # np.arange(20) + 5: min = 5, max = 5+19 = 24
        self.assertEqual(found_min, 5 + (24-5)*0.2)
        self.assertEqual(found_max, 19 + 5)

    def test_find_min_max_I_log_with_zero_2D_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here a bin contains zero intensity and log mode is enabled,
        since log(0) is not allowed, this data point should be
        ignored.
        """

        dummy_data = get_dummy_McStasDataBinned_2d()
        dummy_data.Intensity[2, 2] = 0
        dummy_data.set_plot_options(log=True)
        found_min, found_max = _find_min_max_I(dummy_data)

        # np.arange(20) + 5: min = 5, max = 5+19 = 24
        self.assertAlmostEqual(found_min, 5)
        self.assertAlmostEqual(found_max, 19 + 5)

    def test_find_min_max_I_log_cut_max_2D_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here cut_max is used to limit the maximum plotted while
        log mode is enabled.
        """

        dummy_data = get_dummy_McStasDataBinned_2d()
        dummy_data.set_plot_options(cut_max=0.8, log=True)
        found_min, found_max = _find_min_max_I(dummy_data)

        # np.arange(20) + 5: min = 5, max = 5+19 = 24
        self.assertAlmostEqual(found_min, 5)
        self.assertAlmostEqual(found_max, (19 + 5)*0.8)

    def test_find_min_max_I_log_cut_min_2D_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here cut_min is used to limit the minimum plotted while
        log mode is enabled.
        """

        dummy_data = get_dummy_McStasDataBinned_2d()
        dummy_data.set_plot_options(cut_min=0.2, log=True)
        found_min, found_max = _find_min_max_I(dummy_data)

        # np.arange(20) + 5: min = 5, max = 5+19 = 24
        self.assertAlmostEqual(found_min, 5 + (24-5)*0.2)
        self.assertAlmostEqual(found_max, 19 + 5)

    def test_find_min_max_I_log_orders_of_mag_2D_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here orders_of_mag is used to limit the minimum plotted
        while log mode is enabled.
        """

        dummy_data = get_dummy_McStasDataBinned_2d()
        dummy_data.Intensity[2, 2] = 10**6
        dummy_data.set_plot_options(log=True, orders_of_mag=3)
        found_min, found_max = _find_min_max_I(dummy_data)

        self.assertAlmostEqual(found_min, 10**3)
        self.assertAlmostEqual(found_max, 10**6)

    def test_find_min_max_I_log_orders_of_mag_2D_with_zero_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here orders_of_mag is used to limit the minimum plotted
        while log mode is enabled. A bin in the data contains
        zero intensity, which should be ignored.
        """

        dummy_data = get_dummy_McStasDataBinned_2d()
        dummy_data.Intensity[2, 2] = 10**6
        dummy_data.Intensity[2, 3] = 0
        dummy_data.set_plot_options(log=True, orders_of_mag=3)
        found_min, found_max = _find_min_max_I(dummy_data)

        self.assertAlmostEqual(found_min, 10**3)
        self.assertAlmostEqual(found_max, 10**6)

    def test_find_min_max_I_fail_case(self):
        """
        test _find_min_max_I for a 1D case, it finds the minimum
        and maximum value to plot for a given McStasData set.
        Here orders_of_mag is used to limit the minimum plotted
        while log mode is enabled. A bin in the data contains
        zero intensity, which should be ignored.
        """

        dummy_data = get_dummy_McStasDataBinned_2d()
        dummy_data.Intensity = np.zeros((5, 5))
        dummy_data.set_plot_options(log=True, orders_of_mag=3)
        found_min, found_max = _find_min_max_I(dummy_data)

        self.assertEqual(found_min, 0)
        self.assertEqual(found_max, 0)

    def test_handle_kwargs_log(self):
        """
        Tests handle_kwargs with log option

        Keyword args can be set for all by normal use, or individual
        data sets by using a list. Both are checked here.
        """
        dummy_data1 = get_dummy_McStasDataBinned_2d()
        dummy_data2 = get_dummy_McStasDataBinned_2d()
        self.assertEqual(dummy_data1.plot_options.log, False)
        self.assertEqual(dummy_data2.plot_options.log, False)

        data_list = [dummy_data1, dummy_data2]
        _handle_kwargs(data_list, log=True)
        self.assertEqual(dummy_data1.plot_options.log, True)
        self.assertEqual(dummy_data2.plot_options.log, True)

        _handle_kwargs(data_list, log=[False, True])
        self.assertEqual(dummy_data1.plot_options.log, False)
        self.assertEqual(dummy_data2.plot_options.log, True)

    def test_handle_kwargs_oders_of_mag(self):
        """
        Tests handle_kwargs with orders_of_mag option

        Keyword args can be set for all by normal use, or individual
        data sets by using a list. Both are checked here.
        """
        dummy_data1 = get_dummy_McStasDataBinned_2d()
        dummy_data2 = get_dummy_McStasDataBinned_2d()
        self.assertEqual(dummy_data1.plot_options.orders_of_mag, 300)
        self.assertEqual(dummy_data2.plot_options.orders_of_mag, 300)

        data_list = [dummy_data1, dummy_data2]
        _handle_kwargs(data_list, orders_of_mag=12)
        self.assertEqual(dummy_data1.plot_options.orders_of_mag, 12)
        self.assertEqual(dummy_data2.plot_options.orders_of_mag, 12)

        _handle_kwargs(data_list, orders_of_mag=[50, 10])
        self.assertEqual(dummy_data1.plot_options.orders_of_mag, 50)
        self.assertEqual(dummy_data2.plot_options.orders_of_mag, 10)

    def test_handle_kwargs_all_simple(self):
        """
        Tests handle_kwargs with all simple options option

        Keyword args can be set for all by normal use, or individual
        data sets by using a list. Both are checked here.
        """

        known_plot = ["log", "orders_of_mag",
                      "cut_min", "cut_max",
                      "colormap", "show_colorbar",
                      "x_axis_multiplier",
                      "y_axis_multiplier"]

        kwargs_to_attr = {"x_axis_multiplier": "x_limit_multiplier",
                          "y_axis_multiplier": "y_limit_multiplier"}

        defaults = {"log": False, "orders_of_mag": 300,
                    "cut_min": 0, "cut_max": 1,
                    "colormap": "jet", "show_colorbar": True,
                    "x_limit_multiplier": 1, "y_limit_multiplier": 1}

        test_value = {"log": True, "orders_of_mag": 15,
                      "cut_min": 0.25, "cut_max": 0.8,
                      "colormap": "hot", "show_colorbar": False,
                      "x_limit_multiplier": 2.8, "y_limit_multiplier": 0.8}

        for option in known_plot:

            if option in kwargs_to_attr:
                kw_option = kwargs_to_attr[option]
            else:
                kw_option = option

            default_value = defaults[kw_option]

            dummy_data1 = get_dummy_McStasDataBinned_2d()
            data1_value = dummy_data1.plot_options.__getattribute__(kw_option)
            self.assertEqual(data1_value, default_value)

            dummy_data2 = get_dummy_McStasDataBinned_2d()
            data2_value = dummy_data2.plot_options.__getattribute__(kw_option)
            self.assertEqual(data2_value, default_value)

            data_list = [dummy_data1, dummy_data2]

            set_value = test_value[kw_option]
            given_option = {option: set_value}
            _handle_kwargs(data_list, **given_option)

            data1_value = dummy_data1.plot_options.__getattribute__(kw_option)
            self.assertEqual(data1_value, set_value)

            data2_value = dummy_data2.plot_options.__getattribute__(kw_option)
            self.assertEqual(data2_value, set_value)

            given_option = {option: [set_value, default_value]}
            _handle_kwargs(data_list, **given_option)

            data_1_value = dummy_data1.plot_options.__getattribute__(kw_option)
            self.assertEqual(data_1_value, set_value)
            data_2_value = dummy_data2.plot_options.__getattribute__(kw_option)
            self.assertEqual(data_2_value, default_value)

    def test_handle_kwargs_left_lim(self):
        """
        Tests handle_kwargs with left_lim option

        Keyword args can be set for all by normal use, or individual
        data sets by using a list. Both are checked here.
        """
        dummy_data1 = get_dummy_McStasDataBinned_2d()
        dummy_data2 = get_dummy_McStasDataBinned_2d()
        self.assertEqual(dummy_data1.plot_options.custom_xlim_left, False)
        self.assertEqual(dummy_data2.plot_options.custom_xlim_left, False)

        data_list = [dummy_data1, dummy_data2]
        _handle_kwargs(data_list, left_lim=0.08)
        self.assertEqual(dummy_data1.plot_options.left_lim, 0.08)
        self.assertEqual(dummy_data2.plot_options.left_lim, 0.08)
        self.assertEqual(dummy_data1.plot_options.custom_xlim_left, True)
        self.assertEqual(dummy_data2.plot_options.custom_xlim_left, True)

        _handle_kwargs(data_list, left_lim=[0.08, 1.08])
        self.assertEqual(dummy_data1.plot_options.left_lim, 0.08)
        self.assertEqual(dummy_data2.plot_options.left_lim, 1.08)
        self.assertEqual(dummy_data1.plot_options.custom_xlim_left, True)
        self.assertEqual(dummy_data2.plot_options.custom_xlim_left, True)

    def test_handle_kwargs_right_lim(self):
        """
        Tests handle_kwargs with right_lim option

        Keyword args can be set for all by normal use, or individual
        data sets by using a list. Both are checked here.
        """
        dummy_data1 = get_dummy_McStasDataBinned_2d()
        dummy_data2 = get_dummy_McStasDataBinned_2d()
        self.assertEqual(dummy_data1.plot_options.custom_xlim_right, False)
        self.assertEqual(dummy_data2.plot_options.custom_xlim_right, False)

        data_list = [dummy_data1, dummy_data2]
        _handle_kwargs(data_list, right_lim=0.08)
        self.assertEqual(dummy_data1.plot_options.right_lim, 0.08)
        self.assertEqual(dummy_data2.plot_options.right_lim, 0.08)
        self.assertEqual(dummy_data1.plot_options.custom_xlim_right, True)
        self.assertEqual(dummy_data2.plot_options.custom_xlim_right, True)

        _handle_kwargs(data_list, right_lim=[0.08, 1.08])
        self.assertEqual(dummy_data1.plot_options.right_lim, 0.08)
        self.assertEqual(dummy_data2.plot_options.right_lim, 1.08)
        self.assertEqual(dummy_data1.plot_options.custom_xlim_right, True)
        self.assertEqual(dummy_data2.plot_options.custom_xlim_right, True)

    def test_handle_kwargs_top_lim(self):
        """
        Tests handle_kwargs with top_lim option

        Keyword args can be set for all by normal use, or individual
        data sets by using a list. Both are checked here.
        """
        dummy_data1 = get_dummy_McStasDataBinned_2d()
        dummy_data2 = get_dummy_McStasDataBinned_2d()
        self.assertEqual(dummy_data1.plot_options.custom_ylim_top, False)
        self.assertEqual(dummy_data2.plot_options.custom_ylim_top, False)

        data_list = [dummy_data1, dummy_data2]
        _handle_kwargs(data_list, top_lim=0.08)
        self.assertEqual(dummy_data1.plot_options.top_lim, 0.08)
        self.assertEqual(dummy_data2.plot_options.top_lim, 0.08)
        self.assertEqual(dummy_data1.plot_options.custom_ylim_top, True)
        self.assertEqual(dummy_data2.plot_options.custom_ylim_top, True)

        _handle_kwargs(data_list, top_lim=[0.08, 1.08])
        self.assertEqual(dummy_data1.plot_options.top_lim, 0.08)
        self.assertEqual(dummy_data2.plot_options.top_lim, 1.08)
        self.assertEqual(dummy_data1.plot_options.custom_ylim_top, True)
        self.assertEqual(dummy_data2.plot_options.custom_ylim_top, True)

    def test_handle_kwargs_bottom_lim(self):
        """
        Tests handle_kwargs with bottom_lim option

        Keyword args can be set for all by normal use, or individual
        data sets by using a list. Both are checked here.
        """
        dummy_data1 = get_dummy_McStasDataBinned_2d()
        dummy_data2 = get_dummy_McStasDataBinned_2d()
        self.assertEqual(dummy_data1.plot_options.custom_ylim_bottom, False)
        self.assertEqual(dummy_data2.plot_options.custom_ylim_bottom, False)

        data_list = [dummy_data1, dummy_data2]
        _handle_kwargs(data_list, bottom_lim=0.08)
        self.assertEqual(dummy_data1.plot_options.bottom_lim, 0.08)
        self.assertEqual(dummy_data2.plot_options.bottom_lim, 0.08)
        self.assertEqual(dummy_data1.plot_options.custom_ylim_bottom, True)
        self.assertEqual(dummy_data2.plot_options.custom_ylim_bottom, True)

        _handle_kwargs(data_list, bottom_lim=[0.08, 1.08])
        self.assertEqual(dummy_data1.plot_options.bottom_lim, 0.08)
        self.assertEqual(dummy_data2.plot_options.bottom_lim, 1.08)
        self.assertEqual(dummy_data1.plot_options.custom_ylim_bottom, True)
        self.assertEqual(dummy_data2.plot_options.custom_ylim_bottom, True)

    @unittest.mock.patch("matplotlib.pyplot.subplots")
    def test_handle_kwargs_figsize_default(self, mock_subplots):
        """
        Tests handle_kwargs delivers default figsize
        """

        # Ensures subplots returns a tuple with two objects
        mock_fig = unittest.mock.MagicMock()
        mock_ax = unittest.mock.MagicMock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        # Actual test
        dummy_data = get_dummy_McStasDataBinned_2d()
        make_plot(dummy_data)
        mock_subplots.assert_called_with(figsize=(13, 7), tight_layout=True)

    @unittest.mock.patch("matplotlib.pyplot.subplots")
    def test_handle_kwargs_figsize_tuple(self, mock_subplots):
        """
        Tests handle_kwargs with figsize keyword argument, here
        using tuple as input
        """

        # Ensures subplots returns a tuple with two objects
        mock_fig = unittest.mock.MagicMock()
        mock_ax = unittest.mock.MagicMock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        # Actual test
        dummy_data = get_dummy_McStasDataBinned_2d()
        make_plot(dummy_data, figsize=(5, 9))
        mock_subplots.assert_called_with(figsize=(5, 9), tight_layout=True)

    @unittest.mock.patch("matplotlib.pyplot.subplots")
    def test_handle_kwargs_figsize_list(self, mock_subplots):
        """
        Tests handle_kwargs with figsize keyword argument, here
        using tuple as input
        """

        # Ensures subplots returns a tuple with two objects
        mock_fig = unittest.mock.MagicMock()
        mock_ax = unittest.mock.MagicMock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        # Actual test
        dummy_data = get_dummy_McStasDataBinned_2d()
        make_plot(dummy_data, figsize=[5, 9])
        mock_subplots.assert_called_with(figsize=(5, 9), tight_layout=True)

    def test_handle_kwargs_single_element_to_list(self):
        """
        Test handle_kwargs will grab a single McStasData element
        and turn it into a list.
        """

        dummy_data = get_dummy_McStasDataBinned_2d()
        self.assertFalse(isinstance(dummy_data, list))
        data_list = _handle_kwargs(dummy_data)
        self.assertTrue(isinstance(data_list, list))

    def test_plot_function_1D_normal(self):
        """
        Run the plot function with 1D data set without showing the
        result.

        """
        dummy_data = get_dummy_McStasDataBinned_1d()

        fig, ax0 = plt.subplots()
        _plot_fig_ax(dummy_data, fig, ax0)

    def test_plot_function_1D_log(self):
        """
        Run the plot function with 1D data set without showing the
        result. Here with logarithmic y axis.

        """
        dummy_data = get_dummy_McStasDataBinned_1d()

        fig, ax0 = plt.subplots()
        _plot_fig_ax(dummy_data, fig, ax0, log=True)

    def test_plot_function_2D_normal(self):
        """
        Run the plot function with 2D data set without showing the
        result.

        """
        dummy_data = get_dummy_McStasDataBinned_2d()

        fig, ax0 = plt.subplots()
        _plot_fig_ax(dummy_data, fig, ax0)

    def test_plot_function_2D_log(self):
        """
        Run the plot function with 2D data set without showing the
        result. Here the intensity coloraxis is logarithmic.

        """
        dummy_data = get_dummy_McStasDataBinned_2d()

        fig, ax0 = plt.subplots()
        _plot_fig_ax(dummy_data, fig, ax0, log=True)
