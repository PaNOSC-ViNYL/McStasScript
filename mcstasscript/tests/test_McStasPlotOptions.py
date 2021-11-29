import unittest

from mcstasscript.data.data import McStasPlotOptions


class TestMcStasPlotOptions(unittest.TestCase):
    """
    Various test of McStasPlotOptions class
    """

    def test_McStasPlotOptions_default_log(self):
        """
        Test that newly created McStasPlotOptions log attribute
        has correct type and default value
        """
        plot_options = McStasPlotOptions()
        self.assertIsInstance(plot_options.log, bool)
        self.assertFalse(plot_options.log)

    def test_McStasPlotOptions_default_orders_of_mag(self):
        """
        Test that newly created McStasPlotOptions orders_of_mag
        has the correct default value
        """
        plot_options = McStasPlotOptions()
        self.assertEqual(plot_options.orders_of_mag, 300)

    def test_McStasPlotOptions_default_colormap(self):
        """
        Test that newly created McStasPlotOptions colormap has
        the correct default value
        """
        plot_options = McStasPlotOptions()
        self.assertIs(plot_options.colormap, "jet")

    def test_McStasPlotOptions_default_show_colorbar(self):
        """
        Test that newly created McStasPlotOptions has correct
        default value for show_colorbar
        """
        plot_options = McStasPlotOptions()
        self.assertIs(plot_options.show_colorbar, True)

    def test_McStasPlotOptions_default_cut_max(self):
        """
        Test that newly created McStasPlotOptions has correct
        default value for cut_max
        """
        plot_options = McStasPlotOptions()
        self.assertIs(plot_options.cut_max, 1)

    def test_McStasPlotOptions_default_cut_min(self):
        """
        Test that newly created McStasPlotOptions has correct
        default value for cut_min
        """
        plot_options = McStasPlotOptions()
        self.assertIs(plot_options.cut_min, 0)

    def test_McStasPlotOptions_default_x_axis_multiplier(self):
        """
        Test that newly created McStasPlotOptions has correct
        default value for x_axis_multiplier
        """
        plot_options = McStasPlotOptions()
        self.assertIs(plot_options.x_limit_multiplier, 1)

    def test_McStasPlotOptions_default_y_axis_multiplier(self):
        """
        Test that newly created McStasPlotOptions has correct
        default value for y_axis_multiplier
        """
        plot_options = McStasPlotOptions()
        self.assertIs(plot_options.y_limit_multiplier, 1)

    def test_McStasPlotOptions_default_top_lim(self):
        """
        Test that newly created McStasPlotOptions has correct
        default value for top_lim
        """
        plot_options = McStasPlotOptions()
        self.assertIs(plot_options.custom_ylim_top, False)

    def test_McStasPlotOptions_default_bottom_lim(self):
        """
        Test that newly created McStasPlotOptions has correct
        default value for left_lim
        """
        plot_options = McStasPlotOptions()
        self.assertIs(plot_options.custom_ylim_bottom, False)

    def test_McStasPlotOptions_default_left_lim(self):
        """
        Test that newly created McStasPlotOptions has correct
        default value for left_lim
        """
        plot_options = McStasPlotOptions()
        self.assertIs(plot_options.custom_xlim_left, False)

    def test_McStasPlotOptions_default_right_lim(self):
        """
        Test that newly created McStasPlotOptions has correct
        default value for right_lim
        """
        plot_options = McStasPlotOptions()
        self.assertIs(plot_options.custom_xlim_right, False)

    def test_McStasPlotOptions_set_log(self):
        """
        Test that set_options works on log parameter which
        can be set both with an integer and a bool.
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(log=True)
        self.assertIsInstance(plot_options.log, bool)
        self.assertTrue(plot_options.log)

        plot_options.set_options(log=0)
        self.assertIsInstance(plot_options.log, bool)
        self.assertFalse(plot_options.log)

        plot_options.set_options(log=1)
        self.assertIsInstance(plot_options.log, bool)
        self.assertTrue(plot_options.log)

    def test_McStasPlotOptions_set_orders_of_mag(self):
        """
        Check that set_options works with orders_of_mag keyword
        argument
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(orders_of_mag=5.2)
        self.assertEqual(plot_options.orders_of_mag, 5.2)

    def test_McStasPlotOptions_set_colormap(self):
        """
        Check that set_options work with colormap keyword argument
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(colormap="hot")
        self.assertIs(plot_options.colormap, "hot")

    def test_McStasPlotOptions_set_show_colorbar(self):
        """
        Check that set_options work with show_colormap keyword
        argument
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(show_colorbar=False)
        self.assertIs(plot_options.show_colorbar, False)

    def test_McStasPlotOptions_set_cut_max(self):
        """
        Check that set_options work with cut_max keyword
        argument
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(cut_max=0.8)
        self.assertIs(plot_options.cut_max, 0.8)

    def test_McStasPlotOptions_set_cut_min(self):
        """
        Check that set_options work with cut_min keyword
        argument
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(cut_min=0.2)
        self.assertIs(plot_options.cut_min, 0.2)

    def test_McStasPlotOptions_set_x_axis_multiplier(self):
        """
        Check that set_options work with x_axis_multiplier
        keyword argument
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(x_axis_multiplier=2.8)
        self.assertIs(plot_options.x_limit_multiplier, 2.8)

    def test_McStasPlotOptions_set_y_axis_multiplier(self):
        """
        Check that set_options work with y_axis_multiplier
        keyword argument
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(y_axis_multiplier=0.1)
        self.assertIs(plot_options.y_limit_multiplier, 0.1)

    def test_McStasPlotOptions_set_top_lim(self):
        """
        Check that set_options work with top_lim keyword argument
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(top_lim=128.9)
        self.assertIs(plot_options.custom_ylim_top, True)
        self.assertIs(plot_options.top_lim, 128.9)

    def test_McStasPlotOptions_set_bottom_lim(self):
        """
        Check that set_options work with bottom_lim keyword
        argument
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(bottom_lim=120.9)
        self.assertIs(plot_options.custom_ylim_bottom, True)
        self.assertIs(plot_options.bottom_lim, 120.9)

    def test_McStasPlotOptions_set_left_lim(self):
        """
        Check that set_options work with left_lim keyword argument
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(left_lim=9.2)
        self.assertIs(plot_options.custom_xlim_left, True)
        self.assertIs(plot_options.left_lim, 9.2)

    def test_McStasPlotOptions_set_right_lim(self):
        """
        Check that set_options work with right_lim keyword argument
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(right_lim=1.4)
        self.assertIs(plot_options.custom_xlim_right, True)
        self.assertIs(plot_options.right_lim, 1.4)


if __name__ == '__main__':
    unittest.main()
