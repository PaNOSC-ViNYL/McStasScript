import sys
import os
import numpy as np
import threading
import copy

import ipywidgets as widgets
from IPython.display import display

import matplotlib.pyplot as plt

from mcstasscript.interface.functions import name_search
from mcstasscript.interface import plotter
from mcstasscript.jb_interface import plot_interface
from mcstasscript.jb_interface.widget_helpers import HiddenPrints
from mcstasscript.jb_interface.widget_helpers import parameter_has_default
from mcstasscript.jb_interface.widget_helpers import get_parameter_default


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

        self.plot_interface = None

        self.run_button = None
        self.live_widget = None
        self.progress_bar = None
        self.sim_steps = 5

        self.ncount = "1E6"
        self.mpi = "disabled"
        self.last_mpi_on = None

        self.thread_data = None
        self.thread = None
        self.run_arguments = None

        self.parameters = {}
        # get default parameters from instrument
        for parameter in self.instrument.parameters:
            if parameter_has_default(parameter):
                self.parameters[parameter.name] = get_parameter_default(parameter)

    def make_parameter_widgets(self):
        """
        Creates widgets for parameters using dedicated class ParameterWidget

        returns widget including all parameters
        """
        parameter_widgets = []
        for parameter in self.instrument.parameters:
            par_widget = ParameterWidget(parameter, self.parameters)
            parameter_widgets.append(par_widget.make_widget())

        return widgets.VBox(parameter_widgets)

    def run_simulation_thread(self, change):
        """
        Runs simulation as thread, allowing user to update plots simultaneously

        The use of this method has caused crashes, temporarily circumvented by
        calling run_simulation_live on button instead. Now plots can now be
        updated while a simulation is running.

        Parameters
        ----------

        change: widget change
            Not used
        """

        thread = threading.Thread(target=self.run_simulation_live, args=[1])
        thread.start()

    def run_simulation_live(self, change):
        """
        Performs the simulation with current parameters and settings.

        When live mode is used, updates plot as more data is added.

        Changes icon on button to hourglass while simulation is running, then
        returns to calculator icon.
        """

        lock = threading.Lock()

        if self.live_widget.value:
            sim_parts = self.sim_steps
            #self.plot_interface.set_data(None)
        else:
            sim_parts = 1

        part_ncount = int(float(self.ncount)/sim_parts)

        run_arguments = {"output_path": "interface_" + self.instrument.name,
                         "increment_folder_name": True,
                         #"parameters": self.parameters,
                         "ncount": part_ncount}
        if self.mpi != "disabled":
            run_arguments["mpi"] = self.mpi
            mpi_on = True
        else:
            mpi_on = False

        # McStas does not recognize if the instrument was compiled with or without mpi
        # Ensure it is compiled when switching to and from mpi
        # This also ensures the instrument is compiled at the first run
        if mpi_on == self.last_mpi_on:
            run_arguments["force_compile"] = False
        else:
            run_arguments["force_compile"] = True

        self.last_mpi_on = mpi_on

        self.run_button.icon = "hourglass"
        #print("Running with:", run_arguments)

        if self.live_widget.value:
            self.progress_bar.layout.visibility = 'visible'
        else:
            self.progress_bar.layout.visibility = 'hidden'

        self.progress_bar.value = 0
        plot_data = None
        for index in range(sim_parts):
            self.instrument.settings(**run_arguments)
            self.instrument.set_parameters(self.parameters)
            try:
                with HiddenPrints():
                    self.instrument.backengine()
            except NameError:
                print("McStas run failed.")
                data = []

            with lock:
                self.progress_bar.value = index + 1
                data = self.instrument.output.get_data()["data"]

                if data is not None:
                    if plot_data is None:
                        plot_data = data
                    else:
                        add_data(plot_data, data)

                    sent_data = copy.deepcopy(plot_data)
                    # This happens in a thread, maybe it should be in Main?
                    self.plot_interface.set_data(sent_data)

        self.run_button.icon = "calculator"

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
        #button.on_click(self.run_simulation_thread)
        button.on_click(self.run_simulation_live)

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
        textbox = widgets.Text(value=str(self.ncount), layout=widgets.Layout(width='100px', height='36px'))
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
        textbox = widgets.Text(value=str(self.mpi), layout=widgets.Layout(width='70px', height='36px'))
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

    def make_live_checkmark(self):
        """
        Makes widget for choosing live simulations on / off
        """
        widget = widgets.Checkbox(value=False, description="Live results")
        widget.layout.visibility = "hidden"

        return widget

    def make_progress_bar(self):
        """
        Makes a progress bar for live simulations
        """
        widget = widgets.IntProgress(value=0, min=0, max=self.sim_steps,
                                     description="Sim progress",
                                     orientation="horizontal")

        return widget

    def get_data(self):
        """
        Returns last data set from this interface
        """
        if self.plot_interface is None:
            print("No widget interface initialized, use show_interface method.")
            return []

        if self.plot_interface.data is None:
            print("No run has been performed with the interface widget yet")
            return []

        return self.plot_interface.data

    def show_interface(self):
        """
        Builds and shows widget interface
        """

        # Make parameter controls
        parameter_widgets = self.make_parameter_widgets()

        # Make simulation controls
        self.live_widget = self.make_live_checkmark()
        self.progress_bar = self.make_progress_bar()
        self.progress_bar.layout.visibility = "hidden"
        self.run_button = self.make_run_button()
        ncount_field = self.make_ncount_field()
        mpi_field = self.make_mpi_field()

        simulation_widget = widgets.HBox([self.run_button, ncount_field, mpi_field,
                                          self.live_widget, self.progress_bar])
                                         #layout=widgets.Layout(border="solid"))

        self.plot_interface = plot_interface.PlotInterface()
        plot_widget = self.plot_interface.show_interface()

        return widgets.VBox([parameter_widgets, simulation_widget, plot_widget])


class ParameterWidget:
    """
    Widget for parameter object from McStasScript instrument
    """
    def __init__(self, parameter, parameters):
        """
        Describes a widget for a parameter object given all parameters

        When no options are given in ParameterVariable object, the widget will
        be a textfield where the user can input the value. If the options
        attribute is used, the widget will be a dropdown menu with available
        options. The make_widget method returns the widget, and the update
        function is called whenever the user interacts with the widget.

        The widget shows parameter name, the interactive widget and a comment

        Parameters
        ----------

        parameter: McStasScript ParameterVariable object
            The parameter this widget should represent

        parameters: dict of McStasScript ParameterVariable objects
            Dict with all parameter objects of the instrument
        """

        self.parameter = parameter
        self.parameters = parameters

        if parameter_has_default(parameter):
            self.default_value = get_parameter_default(parameter)
        else:
            self.default_value = None

        self.name = parameter.name
        self.comment = parameter.comment

    def make_widget(self):
        """
        Returns widget with parameter name, interactive widget and comment
        """
        label = widgets.Label(value=self.name,
                              layout=widgets.Layout(width='15%', height='32px'))
        if len(self.parameter.get_options()) > 0:
            par_widget = widgets.Dropdown(options=self.parameter.get_options(),
                                          layout=widgets.Layout(width='10%', height='32px'))
            if self.default_value is not None:
                if self.default_value in self.parameter.get_options():
                    par_widget.value = self.default_value

                if isinstance(self.default_value, str):

                    if self.default_value.strip("'") in self.parameter.get_options():
                        par_widget.value = self.default_value.strip("'")
                    elif self.default_value.strip('"') in self.parameter.get_options():
                        par_widget.value = self.default_value.strip('"')

                if par_widget.value is None:
                    print(self.parameter.get_options())
                    raise KeyError("default value not found in options for parameter: "
                                   + str(self.parameter.name))

        else:
            par_widget = widgets.Text(value=str(self.default_value),
                                      layout=widgets.Layout(width='10%', height='32px'))
        comment = widgets.Label(value=self.comment,
                                layout=widgets.Layout(width='75%', height='32px'))

        par_widget.observe(self.update, "value")

        return widgets.HBox([label, par_widget, comment])

    def update(self, change):
        """
        Update function called whenever the user updates the widget

        When strings parameters are used, this function adds the necessary
        quotation marks if none are provided.
        """
        new_value = change.new
        if self.parameter.type == "string":
            if type(new_value) is str:
                if not (new_value[0] == '"' or new_value[0] == "'"):
                    new_value = '"' + new_value + '"'
        else:

            try:
                new_value = float(new_value)
            except:
                return

        self.parameters[self.name] = new_value


def add_data(initial, new_data):
    """
    Method for adding new data to a data set

    Updates Intensity, Error and Ncount

    Updates all data except metadata info
    """

    for monitor in initial:
        ref_ncount = float(monitor.metadata.info["Ncount"])

        new_monitor = name_search(monitor.name, new_data)
        new_ncount = float(new_monitor.metadata.info["Ncount"])

        total_ncount = ref_ncount + new_ncount

        scale_old = ref_ncount / total_ncount
        scale_new = new_ncount / total_ncount

        monitor.Intensity = scale_old*monitor.Intensity + scale_new*new_monitor.Intensity
        monitor.Error = np.sqrt(scale_old**2*monitor.Error**2+scale_new**2*new_monitor.Error**2)
        monitor.Ncount = monitor.Ncount + new_monitor.Ncount

        monitor.metadata.info["Ncount"] = total_ncount
