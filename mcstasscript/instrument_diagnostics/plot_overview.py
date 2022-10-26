import numpy as np
import matplotlib.pyplot as plt

from mcstasscript.instrument_diagnostics.event_plotter import EventPlotter

class PlotOverview:
    def __init__(self, event_plotter_list, view_list):
        self.event_plotter_list = event_plotter_list
        self.n_points = len(event_plotter_list)
        self.views = view_list
        self.n_plots = len(view_list)

    def plot_all(self, figsize=None, same_scale=True):

        if same_scale:
            self.set_same_scale()

        if figsize is None:
            # Scale size after number of plots
            figsize = (1 + self.n_plots*3, self.n_points*3)

        fig, axs = plt.subplots(self.n_points, self.n_plots, figsize=figsize)

        # Fix cases where n_points or n_plots is 1 and axs is not a list of lists
        if self.n_plots == 1:
            axs = [axs]
        if self.n_points == 1:
            axs = [axs]

        for plotter, ax_row in zip(self.event_plotter_list, axs):
            major_label_set = False
            for view, ax in zip(self.views, ax_row):
                plotter.plot(view=view, fig=fig, ax=ax)

                if not major_label_set:
                    ylabel = ax.get_ylabel()
                    row_name = plotter.name.replace("_", "\ ")
                    new_label = r"$\bf{" + row_name + "}$" + "\n" + ylabel
                    ax.set_ylabel(new_label)

                major_label_set = True

        fig.tight_layout()

    def set_same_scale(self):
        for view in self.views:

            if not view.same_scale:
                # View controls same scale or not
                continue

            axis1_mins = []
            axis1_maxs = []

            axis2_mins = []
            axis2_maxs = []

            for plotter in self.event_plotter_list:
                lim_min, lim_max = plotter.get_view_limits_axis1(view)
                axis1_mins.append(lim_min)
                axis1_maxs.append(lim_max)

                lim_min, lim_max = plotter.get_view_limits_axis2(view)
                axis2_mins.append(lim_min)
                axis2_maxs.append(lim_max)

            view.set_axis1_limits(np.nanmin(axis1_mins), np.nanmax(axis1_maxs))
            if view.axis2 is not None:
                view.set_axis2_limits(np.nanmin(axis2_mins), np.nanmax(axis2_maxs))