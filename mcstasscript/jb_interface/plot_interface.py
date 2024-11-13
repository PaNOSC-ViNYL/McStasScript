import sys
import os
import threading

from collections import OrderedDict

import ipywidgets as widgets
from ipywidgets import GridBox
from IPython.display import display, clear_output

import matplotlib.pyplot as plt

from mcstasscript.interface.functions import name_search
from mcstasscript.helper.plot_helper import _plot_fig_ax

from mcstasscript.jb_interface.widget_helpers import HiddenPrints


class PlotInterface:
    """
    Class for providing plotting interface given McStasScript data
    """
    def __init__(self, data=None):
        """
        Initialize interface for exploring a dataset with plotting options

        Parameters
        ----------

        data: List of McStasData objects
            Optional to set the data, otherwise use set_data method
        """
        self.data = data

        # Variables related to monitor choice
        self.monitor_dropdown = None
        self.current_monitor = None

        # default plotting
        self.log_mode = None
        self.orders_of_mag = 300 # default value in McStasScript
        self.colormap = "jet"

        # Matplotlib objects
        self.fig = None
        self.ax = None
        self.colorbar_ax = None

    def set_data(self, data):
        """
        Set a new dataset for the interface, and updates the plot

        Parameters
        ----------

        data: List of McStasData objects
            New dataset that will be plotted
        """
        self.data = data
        self.monitor_dropdown.set_data(data)
        self.update_plot()

    def set_current_monitor(self, monitor):
        """
        Selects a new monitor to be plotted
        """
        self.current_monitor = monitor
        self.update_plot()

    def set_log_mode(self, log_mode):
        """
        Sets log mode for plotting, True or False
        """
        self.log_mode = bool(log_mode)
        self.update_plot()

    def set_orders_of_mag(self, orders_of_mag):
        """
        Sets orders_of_mag value for logarithmic plots
        """
        self.orders_of_mag = orders_of_mag
        self.update_plot()

    def set_colormap(self, colormap):
        """
        Choose colormap, has to be available in matplotlib
        """
        self.colormap = colormap
        self.update_plot()

    def new_plot(self):
        """
        Sets up original plot with fig, ax and ax for colorbar
        """
        # fig, ax = plt.subplots(constrained_layout=True, figsize=(6, 4))

        self.fig, (self.ax, self.colorbar_ax) = plt.subplots(ncols=2,
                                                             gridspec_kw={'width_ratios': [6, 1]},
                                                             tight_layout=True)

        self.fig.canvas.toolbar_position = 'bottom'

        plt.show()

        self.update_plot()

    def update_plot(self):
        """
        Updates the plot with current data, monitor and plot options

        Threading lock is used as this method is used in a threading context
        and can easily fail if new data is written while plotting. The lock
        prevents this from happening.
        """
        lock = threading.Lock()

        with lock:
            # Clear plot first
            self.ax.cla()
            #self.ax.xaxis.set_ticks([])
            #self.ax.yaxis.set_ticks([])
            self.colorbar_ax.cla()
            #self.colorbar_ax.xaxis.set_ticks([])
            #self.colorbar_ax.yaxis.set_ticks([])

            # Display message if not data can be plotted
            if self.data is None:
                self.ax.text(0.3, 0.5, "No data available yet")
                self.colorbar_ax.set_axis_off()
                self.ax.xaxis.set_ticks([])
                self.ax.yaxis.set_ticks([])
                return

            if len(self.data) == 0:
                self.ax.text(0.25, 0.5, "Simulation returned no data")
                self.colorbar_ax.set_axis_off()
                self.ax.xaxis.set_ticks([])
                self.ax.yaxis.set_ticks([])
                return

            if self.current_monitor is None:
                self.ax.text(0.3, 0.5, "Select a monitor to plot")
                self.colorbar_ax.set_axis_off()
                self.ax.xaxis.set_ticks([])
                self.ax.yaxis.set_ticks([])
                return

            # Get monitor and establish plot options
            monitor = name_search(self.current_monitor, self.data)
            plot_options = {"show_colorbar": True, "log": self.log_mode, "colormap": self.colormap}
            if self.orders_of_mag != "disabled":
                plot_options["orders_of_mag"] = self.orders_of_mag
            else:
                plot_options["orders_of_mag"] = 300 # Default value in McStasPlotOptions

            #print("Plotting with: ", plot_options)
            monitor.set_plot_options(**plot_options)
            with HiddenPrints():
                _plot_fig_ax(monitor, self.fig, self.ax, colorbar_axes=self.colorbar_ax)

            self.colorbar_ax.set_aspect(20)

            # Show colorbar if something is present, otherwise hide it
            if self.colorbar_ax.lines or self.colorbar_ax.collections:
                self.colorbar_ax.set_axis_on()
            else:
                self.colorbar_ax.set_axis_off()

            self.fig.canvas.draw()

    def show_interface(self):
        """
        Show the plot interface
        """
        # turn off automatic plotting
        plt.ioff()

        # Set up plot area
        output = widgets.Output()

        with output:
            self.new_plot()

        output.layout = widgets.Layout(width="75%")

        # could retrieve default plot options from data if given

        plot_control_list = []  # Keep all control widgets in this list
        plot_control_list.append(widgets.Label(value="Choose monitor"))

        # Set up dropdown list for monitor choice
        self.monitor_dropdown = MonitorDropdown(self.set_current_monitor)
        plot_control_list.append(self.monitor_dropdown.make_widget())

        plot_control_list.append(widgets.Label(value="Plot options"))

        # Set up checkbox for log plotting
        log_checkbox = LogCheckbox(self.log_mode, self.set_log_mode)
        plot_control_list.append(log_checkbox.make_widget())

        # Set up text field for orders of mag input
        log_orders_of_mag = OrdersOfMagField(self.set_orders_of_mag)
        plot_control_list.append(log_orders_of_mag.make_widget())

        # Set up dropdown box for colormap
        colormap_control = ColormapDropdown(self.set_colormap)
        plot_control_list.append(colormap_control.make_widget())

        plot_controls = widgets.VBox(plot_control_list,
                                     layout=widgets.Layout(width="25%"))

        # In case data is already supplied, set it
        if self.data is not None:
            self.set_data(self.data)

        return widgets.HBox([output, plot_controls])


class ColormapDropdown:
    """
    Class for controlling dropdown menus for colormaps
    """
    def __init__(self, set_colormap):
        """
        Controls colormap dropdown menus with given set_colormap function

        Creates dropdown widget and calls the given set_colormap function
        when the user updates the colormap choice.
        The colormap choice is given as two dropdown menus, one for selecting
        the category of colormap, and the other to select the actual colormap.

        The available colormaps are those supported in matplotlib

        Parameters
        ----------

        set_colormap : function
            Function called with colormap name as argument when changed

        """
        self.set_colormap = set_colormap
        self.colormap_widget = None

        # Default colormaps in matplotlib
        self.cmaps = OrderedDict()
        self.cmaps['Perceptually Uniform Sequential'] = [
            'viridis', 'plasma', 'inferno', 'magma', 'cividis']
        self.cmaps['Sequential'] = [
            'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
            'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
            'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn']
        self.cmaps['Sequential (2)'] = [
            'binary', 'gist_yarg', 'gist_gray', 'gray', 'bone', 'pink',
            'spring', 'summer', 'autumn', 'winter', 'cool', 'Wistia',
            'hot', 'afmhot', 'gist_heat', 'copper']
        self.cmaps['Diverging'] = [
            'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
            'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic']
        self.cmaps['Cyclic'] = ['twilight', 'twilight_shifted', 'hsv']
        self.cmaps['Qualitative'] = ['Pastel1', 'Pastel2', 'Paired', 'Accent',
                                'Dark2', 'Set1', 'Set2', 'Set3',
                                'tab10', 'tab20', 'tab20b', 'tab20c']
        self.cmaps['Miscellaneous'] = [
            'flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
            'gnuplot', 'gnuplot2', 'CMRmap', 'cubehelix', 'brg',
            'gist_rainbow', 'rainbow', 'jet', #'turbo',  # turbo reports errors
            'nipy_spectral', 'gist_ncar']

        self.categories = self.cmaps.keys()

    def make_widget(self):
        """
        Creates the widget and sets appropriate update functions

        The category dropdown will change options for the actual colormap
        dropdown menu through the update_cmap_options method.
        The colormap choice uses the update_cmap method and calls the
        update_function held in attributes.
        """

        header = widgets.Label(value="Colormap category")
        category = widgets.Dropdown(value="Miscellaneous", options=self.categories,
                                    layout=widgets.Layout(width="98%"))
        category.observe(self.update_cmap_options, "value")

        description = widgets.Label(value="Colormap", layout=widgets.Layout(width="39%"))
        default_options = self.cmaps[category.value]
        self.colormap_widget = widgets.Dropdown(value="jet", options=default_options,
                                                layout=widgets.Layout(width="58%"))
        self.colormap_widget.observe(self.update_cmap, "value")

        colormap = widgets.HBox([description, self.colormap_widget])

        return widgets.VBox([header, category, colormap])

    def update_cmap_options(self, change):
        """
        Updates the colormap options in the colormap widget
        """
        self.colormap_widget.options = self.cmaps[change.new]

    def update_cmap(self, change):
        """
        Updates the colormap with the set_colormap function in attributes
        """
        self.set_colormap(change.new)


class MonitorDropdown:
    """
    Class for creating monitor dropdown menu
    """
    def __init__(self, set_current_monitor):
        """
        Sets up MonitorDropdown menu with given update function

        Parameters
        ----------

        update_plot: function
            function called to update plot
        """

        self.set_current_monitor = set_current_monitor
        self.last_monitor = None
        self.data = None
        self.widget = None

    def set_data(self, data):
        """
        Updates the menu options given new data

        Parameters
        ----------

        data: McStasData list
            Data returned by McStasScript simulation
        """

        lock = threading.Lock()
        with lock:

            self.data = data

            if data is None:
                self.widget.options = []
                return

            monitor_names = []
            for data in self.data:

                # Ensure data names are unique
                original_name = data.name
                index = 1
                while data.name in monitor_names:
                    data.name = original_name + "_" + str(index)
                    index += 1

                monitor_names.append(data.name)

            self.widget.options = monitor_names

            # Go to the last set monitor if possible
            if self.last_monitor is not None:
                if self.last_monitor in self.widget.options:
                    self.set_current_monitor(self.last_monitor)

    def make_widget(self):
        """
        Builds the widget for the dropdown menu and links to update method

        """
        self.widget = widgets.Dropdown(layout=widgets.Layout(width="98%"))

        self.widget.observe(self.update, "value")

        return self.widget

    def update(self, change):
        """
        Calls update_function when dropdown menu is used

        Parameters
        ----------

        change: widget change
            state change of widget
        """
        # can do input sanitation here
        lock = threading.Lock()
        with lock:
            self.set_current_monitor(change.new)
            if change.new is not None:
                self.last_monitor = change.new


class LogCheckbox:
    """
    Class for widget with log mode checkbox
    """
    def __init__(self, log_mode, set_log_mode):
        """
        Sets up checkbox with log mode, takes initial mode and update function

        Parameters
        ----------

        log_mode : bool
            Initial state of log checkbox

        set_log_mode : function
            Function which will be called with new log_mode
        """
        self.log_mode = log_mode
        self.set_log_mode = set_log_mode

    def make_widget(self):
        """
        Creates the actual checkbox widget along with descriptive text
        """
        description_layout = widgets.Layout(width='250px', height='32px',
                                            display="flex",
                                            justify_content="flex-start")
        description_log = widgets.Label(value="Log plot", layout=description_layout)

        log_check = widgets.Checkbox(
            value=self.log_mode,
            description='',
            disabled=False,
            indent=False,
            layout=widgets.Layout(width='70px', height='32px')
        )
        log_check.observe(self.update, "value")

        return widgets.HBox([description_log, log_check])

    def update(self, change):
        """
        Calls given update function with new log_mode

        Parameters
        ----------

        change : change object
            Change object from widget interaction
        """
        self.set_log_mode(change.new)


class OrdersOfMagField:
    """
    Class for handling orders_of_mag widget
    """
    def __init__(self, set_orders_of_mag):
        """
        Widget for entering orders_of_mag used in log plotting

        Orders_of_mag parameter controls how many orders of magnitude are
        plotted when showing log scale, counting from the highest value and
        down. The object needs an update function orders_of_mag.
        The widget text field starts with the text "disabled" which
        corresponds to the default value of 300 orders of magnitude.

        Parameters
        ----------

        set_orders_of_mag : function
            Function for updating orders_of_mag value
        """
        self.set_orders_of_mag = set_orders_of_mag

    def make_widget(self):
        """
        Creates actual widget with descriptive text
        """
        description_layout = widgets.Layout(width='250px', height='32px',
                                            display="flex",
                                            justify_content="flex-start")
        description_orders = widgets.Label(value="Orders of magnitude", layout=description_layout)
        textbox = widgets.Text(value=str("disabled"),
                               layout=widgets.Layout(width='70px', height='32px'))
        textbox.observe(self.update, "value")

        return widgets.HBox([description_orders, textbox])

    def update(self, change):
        """
        Update orders_of_mag and replot

        Parameters
        ----------

        change: widget change
            state change of widget
        """
        if change.new == "disabled":
            self.set_orders_of_mag(change.new)
            return

        try:
            float(change.new)
        except ValueError:
            return

        self.set_orders_of_mag(float(change.new))
