import unittest

from mcstasscript.data.data import McStasPlotOptions


class TestMcStasPlotOptions(unittest.TestCase):
    """
    Various test of McStasPlotOptions class
    """

    def test_McStasPlotOptions_default_log(self):
        """
        Test that newly created McStasMetaData has correct type
        """
        plot_options = McStasPlotOptions()
        self.assertIsInstance(plot_options.log, bool)
        self.assertFalse(plot_options.log)

    def test_McStasPlotOptions_default_orders_of_mag(self):
        """
        Test that newly created McStasMetaData has correct type
        """
        plot_options = McStasPlotOptions()
        self.assertEqual(plot_options.orders_of_mag, 300)

    def test_McStasPlotOptions_default_colormap(self):
        """
        Test that newly created McStasMetaData has correct type
        """
        plot_options = McStasPlotOptions()
        self.assertIs(plot_options.colormap, "jet")

    def test_McStasPlotOptions_set_log(self):
        """
        Test that newly created McStasMetaData has correct type
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
        Test that newly created McStasMetaData has correct type
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(orders_of_mag=5.2)
        self.assertEqual(plot_options.orders_of_mag, 5.2)

    def test_McStasPlotOptions_set_colormap(self):
        """
        Test that newly created McStasMetaData has correct type
        """
        plot_options = McStasPlotOptions()
        plot_options.set_options(colormap="hot")
        self.assertIs(plot_options.colormap, "hot")


if __name__ == '__main__':
    unittest.main()
