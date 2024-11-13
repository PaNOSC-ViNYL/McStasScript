import numpy as np
import matplotlib.pyplot as plt

from mcstasscript.helper.plot_helper import _plot_fig_ax

class EventPlotter:
    """
    Plots event data onto given views
    """
    def __init__(self, name, data, flag_info=None):
        """
        EventPlotter stores name and data, can produce plots given views

        Parameters:

        name : str
            Name of dataset

        data : McStasEventData
            Data object with event data

        flag_info : list of str
            List of flag names in order U1 U2 U3
        """
        self.name = name
        self.data = data
        self.flag_info = flag_info

    def scale_weights(self, factor):
        """
        Scales all weights in contained McStasEventData object

        Parameters:

        factor : float
            Scale factor to be applied
        """
        index = self.data.find_variable_index("p", flag_info=self.flag_info)
        self.data.Events[:, index] *= factor

    def add_view_limits(self, view):
        """
        Sets limits of View object from what is applicable to this data

        Parameters:
        view : View
            View for which limits should be set
        """
        data = self.data.get_data_column(view.axis1, flag_info=self.flag_info)
        view.set_axis1_limits(np.min(data), np.max(data))

        if view.axis2 is not None:
            data = self.data.get_data_column(view.axis1, flag_info=self.flag_info)
            view.set_axis1_limits(np.min(data), np.max(data))

    def get_view_limits_axis1(self, view):
        """
        Finds limits for axis1 of given view with the contained data

        Parameters:
        view : View
            View for which limits should be retrieved
        """
        data = self.data.get_data_column(view.axis1, flag_info=self.flag_info)
        return np.min(data), np.max(data)

    def get_view_limits_axis2(self, view):
        """
        Finds limits for axis1 of given view with the contained data

        Parameters:
        view : View
            View for which limits should be retrieved
        """
        if view.axis2 is None:
            return np.NaN, np.NaN
        data = self.data.get_data_column(view.axis2, flag_info=self.flag_info)
        return np.min(data), np.max(data)

    def plot(self, view, fig, ax):
        """
        Plots binned data generated from contained data on axis from view

        A view can also contain additional plot options which will be passed
        to the standard plotting tools.

        view : View
            View defining onto which axis and what bins EventData should be binned

        fig : Matplotlib fig
            Figure object for figure

        ax : Matplotlib ax
            Axes object for figure
        """

        if view.axis2 is None:
            data = self.data.make_1d(axis1=view.axis1, n_bins=view.bins, flag_info=self.flag_info)
            data.set_title("")
            if view.axis1_limits is not None:
                data.set_plot_options(left_lim=view.axis1_limits[0], right_lim=view.axis1_limits[1])
            data.set_plot_options(**view.plot_options)

        else:
            data = self.data.make_2d(axis1=view.axis1, axis2=view.axis2, n_bins=view.bins, flag_info=self.flag_info)
            data.set_plot_options(show_colorbar=False)
            data.set_title("")
            if view.axis1_limits is not None and view.axis2_limits is not None:
                data.set_plot_options(left_lim=view.axis1_limits[0], right_lim=view.axis1_limits[1],
                                      bottom_lim=view.axis2_limits[0], top_lim=view.axis2_limits[1])
            data.set_plot_options(**view.plot_options)

        _plot_fig_ax(data, fig, ax)

        x_lims = ax.get_xlim()
        y_lims = ax.get_ylim()

        if view.axis1_values is not None:
            for value in view.axis1_values:
                ax.plot([value, value], y_lims, "k")

            ax.set_xlim(x_lims)
            ax.set_ylim(y_lims)

        if view.axis2_values is not None:
            for value in view.axis2_values:
                ax.plot(x_lims, [value, value], "k")

            ax.set_xlim(x_lims)
            ax.set_ylim(y_lims)

