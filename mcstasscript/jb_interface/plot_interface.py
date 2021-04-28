import sys
import os

import ipywidgets as widgets
from IPython.display import display

import matplotlib.pyplot as plt

from mcstasscript.interface.functions import name_search
from mcstasscript.interface import plotter

from mcstasscript.jb_interface.widget_helpers import HiddenPrints


class PlotInterface:
    def __init__(self, data=None):
        self.data = data

        self.monitor_dropdown = None
        self.current_monitor = None

        self.log_mode = None
        self.orders_of_mag = 300 # default value in McStasScript

        self.fig = None
        self.ax = None

    def set_data(self, data):
        self.data = data
        self.monitor_dropdown.set_data(data)

    def set_current_monitor(self, monitor):
        self.current_monitor = monitor
        self.update_plot()

    def set_log_mode(self, log_mode):
        self.log_mode = log_mode
        self.update_plot()

    def set_orders_of_mag(self, orders_of_mag):
        self.orders_of_mag = orders_of_mag
        self.update_plot()

    def new_plot(self):
        """
        Sets up original plot with fig and ax
        """
        # fig, ax = plt.subplots(constrained_layout=True, figsize=(6, 4))
        self.fig, self.ax = plt.subplots()

        self.fig.canvas.toolbar_position = 'bottom'
        self.ax.grid(True)

        self.update_plot()

    def update_plot(self):
        """
        Updates the plot with current data, monitor and plot options
        """

        self.ax.cla()

        if self.data is None:
            self.ax.text(0.4, 0.5, "No data available")
            return

        print("current monitor in update_plot:", self.current_monitor)
        monitor = name_search(self.current_monitor, self.data)
        plot_options = {"show_colorbar": False, "log": self.log_mode}
        if self.orders_of_mag != "disabled":
            plot_options["orders_of_mag"] = self.orders_of_mag
        else:
            plot_options["orders_of_mag"] = 300 # Default value in McStasPlotOptions

        print("Plotting with: ", plot_options)
        monitor.set_plot_options(**plot_options)
        with HiddenPrints():
            plotter._plot_fig_ax(monitor, self.fig, self.ax)

        plt.tight_layout()

    def show_interface(self):
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

        plot_controls = widgets.VBox(plot_control_list,
                                     layout=widgets.Layout(width="25%", border="solid"))

        if self.data is not None:
            self.set_data(self.data)

        return widgets.HBox([output, plot_controls])


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
        self.data = data

        monitor_names = []
        for data in self.data:
            monitor_names.append(data.name)

        self.widget.options = monitor_names

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
        self.set_current_monitor(change.new)


class LogCheckbox:
    def __init__(self, log_mode, set_log_mode):
        self.log_mode = log_mode
        self.set_log_mode = set_log_mode

    def make_widget(self):
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
        self.set_log_mode(change.new)


class OrdersOfMagField:
    def __init__(self, set_orders_of_mag):
        self.set_orders_of_mag = set_orders_of_mag

    def make_widget(self):
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
