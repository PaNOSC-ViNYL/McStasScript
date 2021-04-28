import sys
import os

import ipywidgets as widgets
from IPython.display import display

import matplotlib.pyplot as plt

from mcstasscript.interface.functions import name_search
from mcstasscript.interface import plotter


class HiddenPrints:
    """
    Environment which suppress prints
    """
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout


def parameter_has_default(parameter):
    """
    Checks if ParameterVariable has a default value, returns bool

    Parameters
    ----------

    parameter: ParameterVariable
        The parameter to check for default value
    """
    if parameter.value == "":
        return False
    return True


def get_parameter_default(parameter):
    """
    Returns the default value of a parameter

    Parameters
    ----------

    parameter: ParameterVariable
        The parameter for which the default value is returned
    """
    if parameter.value != "":
        if parameter.type == "string":
            return parameter.value
        elif parameter.type == "double" or parameter.type == "":
            return float(parameter.value)
        elif parameter.type == "int":
            return int(parameter.value)
        else:
            raise RuntimeError("Unknown parameter type '"
                               + parameter.type + "' of par named '"
                               + parameter.name + "'.")
    return None


class SimInterface:
    """
    Class for setting up widget that controls McStasScript instrument and plot
    """
    def __init__(self, instrument):
        """
        Sets up widget where the user can input instrument parameters, run the
        simulation, see plotted results and adjust the plots.

        The parameters of the instrument model are displayed with name, default
        value and comment. Can be adjusted with free text.

        A run button starts a simulation, and basic settings can be adjusted.

        A dropdown menu is available for selecting what monitor to view results
        from, and basic settings related to the plot can be adjusted.

        Show the interface with the show_interface method.

        Parameters
        ----------

        instrument: McStas_instr or McXtrace_instr
            instrument for which a widget should be created
        """

        self.instrument = instrument

        self.fig = None
        self.ax = None

        self.log_mode = False
        self.orders_of_mag = "disabled"

        self.run_button = None

        self.monitor_dropdown = None
        self.current_monitor = None

        self.ncount = "1E6"
        self.mpi = "disabled"
        self.data = None

        self.parameters = {}
        # get default parameters from instrument
        for parameter in self.instrument.parameter_list:
            if parameter_has_default(parameter):
                self.parameters[parameter.name] = get_parameter_default(parameter)

    def make_parameter_widgets(self):
        """
        Creates widgets for parameters using dedicated class ParameterTextbox
        Preliminary check for parameter type disabled as the ParameterVariable
        class does not set type for default case, will be fixed.

        returns widget including all parameters
        """
        parameter_widgets = []
        for parameter in self.instrument.parameter_list:
            if True: #parameter.type != "":
                par_widget = ParameterTextbox(parameter, self.parameters)
            else:
                raise RuntimeError("Unknown parameter type '"
                                   + parameter.type + "' of par named '"
                                   + parameter.name + "'.")

            parameter_widgets.append(par_widget.make_widget())

        return widgets.VBox(parameter_widgets)

    def run_simulation(self, change):
        """
        Performs the simulation with current parameters and settings.

        Changes icon on button to hourglass while simulation is running, then
        returns to calculator icon.

        Has dummy parameter change to allow the method to be used in on_click
        method of the run button.

        Parameters
        ----------

        change: widget change
            Not used
        """
        run_arguments = {"foldername": "interface",
                         "increment_folder_name": True,
                         "parameters": self.parameters,
                         "ncount": int(float(self.ncount))}
        if self.mpi != "disabled":
            run_arguments["mpi"] = self.mpi

        self.run_button.icon = "hourglass"
        print("Running with:", run_arguments)
        with HiddenPrints():
            data = self.instrument.run_full_instrument(**run_arguments)
        self.run_button.icon = "calculator"

        self.data = data
        self.monitor_dropdown.set_data(data)
        self.update_plot()

    def make_run_button(self):
        """
        Creates a run button which perform the simulation
        """
        button = widgets.Button(
            description='Run',
            disabled=False,
            button_style='',  # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Runs the simulation with current parameters',
            icon='calculator'  # (FontAwesome names without the `fa-` prefix)
        )
        button.on_click(self.run_simulation)
        return button

    def make_ncount_field(self):
        """
        Creates field for ncount, links to update_ncount

        The field supports scientific notation
        """
        description_layout = widgets.Layout(width='70px', height='32px',
                                            display="flex",
                                            justify_content="flex-end")
        description = widgets.Label(value="ncount", layout=description_layout)
        textbox = widgets.Text(value=str(self.ncount), layout=widgets.Layout(width='100px', height='32px'))
        textbox.observe(self.update_ncount, "value")

        return widgets.HBox([description, textbox])

    def update_ncount(self, change):
        """
        Updates ncount variable from textbox input

        Only updates when usable input is entered. Supports scientific
        notation in input through conversion to float

        Parameters
        ----------

        change: widget change
            state change of widget
        """
        try:
            self.ncount = int(float(change.new))
        except ValueError:
            pass

    def make_mpi_field(self):
        """
        Creates field for mpi, links to update_mpi
        """
        description_layout = widgets.Layout(width='40px', height='32px',
                                            display="flex",
                                            justify_content="flex-end")
        description = widgets.Label(value="mpi", layout=description_layout)
        textbox = widgets.Text(value=str(self.mpi), layout=widgets.Layout(width='70px', height='32px'))
        textbox.observe(self.update_mpi, "value")

        return widgets.HBox([description, textbox])

    def update_mpi(self, change):
        """
        Updates mpi value when integer or the word 'disabled' is given

        Parameters
        ----------

        change: widget change
            state change of widget
        """
        if change.new == "disabled":
            self.mpi = change.new

        try:
            self.mpi = int(change.new)
        except ValueError:
            pass

    def make_log_options(self):
        """
        Creates widget with options for log options, links to update_log
        and update_orders_of_mag
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
        log_check.observe(self.update_log, "value")

        log_widget = widgets.HBox([description_log, log_check])

        description_layout = widgets.Layout(width='250px', height='32px',
                                            display="flex",
                                            justify_content="flex-start")
        description_orders = widgets.Label(value="Orders of magnitude", layout=description_layout)
        textbox = widgets.Text(value=str(self.orders_of_mag),
                               layout=widgets.Layout(width='70px', height='32px'))
        textbox.observe(self.update_orders_of_mag, "value")

        orders_of_mag_widget = widgets.HBox([description_orders, textbox])

        return widgets.VBox([log_widget, orders_of_mag_widget])

    def update_log(self, change):
        """
        Update log_mode and replot figure

        Parameters
        ----------

        change: widget change
            state change of widget
        """
        self.log_mode = change.new
        self.update_plot()

    def update_orders_of_mag(self, change):
        """
        Update orders_of_mag and replot

        Parameters
        ----------

        change: widget change
            state change of widget
        """
        if change.new == "disabled":
            self.orders_of_mag = change.new
            self.update_plot()
            return

        try:
            self.orders_of_mag = float(change.new)
        except ValueError:
            return

        self.update_plot()

    def select_monitor(self, monitor):
        """
        Selects new monitor to plot and replots figure
        The method is called from MonitorDropdown class

        Parameters
        ----------

        monitor: str
            Monitor name
        """
        self.current_monitor = monitor
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
        """
        Builds and shows widget interface
        """
        output = widgets.Output()

        with output:
            self.new_plot()

        # Make parameter controls
        parameter_widgets = self.make_parameter_widgets()

        # Make simulation controls
        self.run_button = self.make_run_button()
        ncount_field = self.make_ncount_field()
        mpi_field = self.make_mpi_field()

        simulation_widget = widgets.HBox([self.run_button, ncount_field, mpi_field],
                                         layout=widgets.Layout(border="solid"))

        plot_box_monitor_label = widgets.Label(value="Choose monitor")
        self.monitor_dropdown = MonitorDropdown(self.select_monitor)
        monitor_dropdown_widget = self.monitor_dropdown.make_widget()
        plot_box_options_label = widgets.Label(value="Plot options")
        log_options = self.make_log_options()

        plot_controls = widgets.VBox([plot_box_monitor_label, monitor_dropdown_widget,
                                      plot_box_options_label, log_options],
                                     layout=widgets.Layout(width="25%", border="solid"))
        output.layout=widgets.Layout(width="75%")
        plot_widget = widgets.HBox([output, plot_controls])

        return widgets.VBox([parameter_widgets, simulation_widget, plot_widget])


class MonitorDropdown:
    """
    Class for creating monitor dropdown menu
    """
    def __init__(self, update_function):
        """
        Sets up MonitorDropdown menu with given update function

        Parameters
        ----------

        update_function: function
            function called when dropdown menu item selected
        """

        self.update_function = update_function
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
        self.update_function(change.new)


class ParameterTextbox:
    def __init__(self, parameter, parameters):

        self.parameter = parameter
        self.parameters = parameters

        if parameter_has_default(parameter):
            self.default_value = get_parameter_default(parameter)
        else:
            self.default_value = ""

        self.name = parameter.name
        self.comment = parameter.comment

    def make_widget(self):
        label = widgets.Label(value=self.name,
                              layout=widgets.Layout(width='15%', height='32px'))
        textbox = widgets.Text(value=str(self.default_value),
                               layout=widgets.Layout(width='10%', height='32px'))
        comment = widgets.Label(value=self.comment,
                                layout=widgets.Layout(width='75%', height='32px'))

        textbox.observe(self.update, "value")

        return widgets.HBox([label, textbox, comment])

    def update(self, change):
        self.parameters[self.name] = change.new









