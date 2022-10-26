import numpy as np
import matplotlib.pyplot as plt

from mcstasscript.helper.plot_helper import _plot_fig_ax

class EventPlotter:
    def __init__(self, name, data):
        self.name = name
        self.data = data

    def scale_weights(self, factor):
        index = self.data.find_variable_index("p")
        self.data.Events[:, index] *= factor

    def add_view_limits(self, view):
        data = self.data.get_data_column(view.axis1)
        view.set_axis1_limits(np.min(data), np.max(data))

        if view.axis2 is not None:
            data = self.data.get_data_column(view.axis1)
            view.set_axis1_limits(np.min(data), np.max(data))

    def get_view_limits_axis1(self, view):
        data = self.data.get_data_column(view.axis1)
        return np.min(data), np.max(data)

    def get_view_limits_axis2(self, view):
        if view.axis2 is None:
            return np.NaN, np.NaN
        data = self.data.get_data_column(view.axis2)
        return np.min(data), np.max(data)

    def plot(self, view, fig, ax):

        if view.axis2 is None:
            data = self.data.make_1d(axis1=view.axis1, n_bins=view.bins)
            data.set_title("")
            if view.axis1_limits is not None:
                data.set_plot_options(left_lim=view.axis1_limits[0], right_lim=view.axis1_limits[1])
            data.set_plot_options(**view.plot_options)

        else:
            data = self.data.make_2d(axis1=view.axis1, axis2=view.axis2, n_bins=view.bins)
            data.set_plot_options(show_colorbar=False)
            data.set_title("")
            if view.axis1_limits is not None and view.axis2_limits is not None:
                data.set_plot_options(left_lim=view.axis1_limits[0], right_lim=view.axis1_limits[1],
                                      bottom_lim=view.axis2_limits[0], top_lim=view.axis2_limits[1])
            data.set_plot_options(**view.plot_options)

        _plot_fig_ax(data, fig, ax)

