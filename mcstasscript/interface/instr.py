from __future__ import print_function

import os
import shutil
import datetime
import yaml
import subprocess
import copy
import warnings
import re

from IPython.display import IFrame

from libpyvinyl.BaseCalculator import BaseCalculator
from libpyvinyl.Parameters.Collections import CalculatorParameters

from mcstasscript.data.pyvinylData import pyvinylMcStasData, pyvinylMCPLData
from mcstasscript.data.MCPLDataFormat import MCPLDataFormat

from mcstasscript.helper.mcstas_objects import DeclareVariable
from mcstasscript.helper.mcstas_objects import provide_parameter
from mcstasscript.helper.mcstas_objects import write_parameter
from mcstasscript.helper.mcstas_objects import Component

from mcstasscript.helper.component_reader import ComponentReader
from mcstasscript.helper.managed_mcrun import ManagedMcrun
from mcstasscript.helper.formatting import is_legal_filename
from mcstasscript.helper.formatting import bcolors
from mcstasscript.helper.unpickler import CustomMcStasUnpickler, CustomMcXtraceUnpickler
from mcstasscript.helper.exceptions import McStasError
from mcstasscript.helper.beam_dump_database import BeamDumpDatabase
from mcstasscript.helper.check_mccode_version import check_mcstas_major_version
from mcstasscript.helper.check_mccode_version import check_mcxtrace_major_version
from mcstasscript.helper.name_inspector import find_python_variable_name
from mcstasscript.helper.search_statement import SearchStatement, SearchStatementList
from mcstasscript.instrument_diagram.make_diagram import instrument_diagram
from mcstasscript.instrument_diagnostics.intensity_diagnostics import IntensityDiagnostics


class McCode_instr(BaseCalculator):
    """
    Main class for writing a McCode instrument using McStasScript

    Initialization of McCode_instr sets the name of the instrument file
    and its methods are used to add all aspects of the instrument file.
    The class also holds methods for writing the finished instrument
    file to disk and to run the simulation. This is meant as a base class
    that McStas_instr and McXtrace_instr inherits from, these have to provide
    some attributes. Inherits from libpyvinyl BaseCalculator in order to
    harmonize input with other simulation engines.

    Required attributes in superclass
    ---------------------------------
    executable : str
        Name of executable, mcrun or mxrun

    particle : str
        Name of probe particle, "neutron" or "x-ray"

    package_name : str
        Name of package, "McStas" or "McXtrace"

    Attributes
    ----------
    name : str
        name of instrument file

    author : str, default "Python Instrument Generator"
        name of user of McStasScript, written to the file

    origin : str, default "ESS DMSC"
        origin of instrument file (affiliation)

    input_path : str, default "."
        directory in which simulation is executed, uses components found there

    output_path : str
        directory in which the data is written

    executable_path : str
        absolute path of mcrun command, or empty if it is in path

    parameters : ParameterContainer
        contains all input parameters to be written to file

    declare_list : list of DeclareVariable instances
        contains all declare parrameters to be written to file

    initialize_section : str
        string containing entire initialize section to be written

    trace_section : str
        string containing trace section (OBSOLETE)

    finally_section : str
        string containing entire finally section to be written

    component_list : list of component instances
        list of components in the instrument

    component_name_list : list of strings
        list of names of the components in the instrument

    component_class_lib : dict
        dict of custom Component classes made at run time

    component_reader : ComponentReader
        ComponentReader instance for reading component files

    package_path : str
        Path to mccode package containing component folders

    run_settings : dict
        Dict of options set with settings

    data : list
        List of McStasData objects produced by last run

    Methods
    -------
    add_parameter(*args, **kwargs)
        Adds input parameter to the define section

    add_declare_var(type, name)
        Add declared variable called name of given type to the declare section

    append_declare(string)
        Appends to the declare section

    append_initialize(string)
        Appends a string to the initialize section, then adds new line

    append_initialize_no_new_line(string)
        Appends a string to the initialize section

    append_finally(string)
        Appends a string to finally section, then adds new line

    append_finally_no_new_line(string)
        Appends a string to finally section

    append_trace(string)
        Obsolete method, add components instead (used in write_c_files)

    append_trace_no_new_line(string)
        Obsolete method, add components instead (used in write_c_files)

    available_components(string)
        Shows available components in given category

    component_help(name)
        Shows help on component of given name

    add_component(instance_name, component_name, **kwargs)
        Add a component to the instrument file

    copy_component(new_component_name, original_component, **kwargs)
        Makes a copy of original_component with new_component_name

    get_component(instance_name)
        Returns component instance with name instance_name

    get_last_component()
        Returns component instance of last component

    set_component_parameter(instance_name, dict)
        Adds parameters as dict to component with instance_name

    set_component_AT(instance_name, AT_data, **kwargs)
        Sets position of component named instance_name

    set_component_ROTATED(instance_name, ROTATED_data, **kwargs)
        Sets rotation of component named instance_name

    set_component_RELATIVE(instane_name, string)
        Sets position and rotation reference for named component

    set_component_WHEN(instance_name, string)
        Sets WHEN condition of named component, is logical c expression

    set_component_GROUP(instance_name, string)
        Sets GROUP name of component named instance_name

    append_component_EXTEND(instance_name, string)
        Appends a line to EXTEND section of named component

    set_component_JUMP(instance_name, string)
        Sets JUMP code for named component

    set_component_SPLIT(instance_name, string)
        Sets SPLIT value for named component

    set_component_c_code_before(instance_name, string)
        Sets c code before the component

    set_component_c_code_after(instance_name, string)
        Sets c code after the component

    set_component_comment(instance_name, string)
        Sets comment to be written before named component

    print_component(instance_name)
        Prints an overview of current state of named component

    print_component_short(instance_name)
        Prints short overview of current state of named component

    show_components()
        Prints overview of postion / rotation of all components

    write_c_files()
        Writes c files for %include in generated_includes folder

    write_full_instrument()
        Writes full instrument file to current directory

    show_instrument()
        Shows instrument using mcdisplay

    set_parameters(dict)
        Inherited from libpyvinyl BaseCalculator

    settings(**kwargs)
        Sets settings for performing simulation

    backengine()
        Performs simulation, saves in data attribute

    run_full_instrument(**kwargs)
        Depricated method for performing the simulation

    interface()
        Shows interface with jupyter notebook widgets

    get_interface_data()
        Returns data set from latest simulation in widget
    """

    def __init__(self, name, parameters=None, author=None,
                 origin=None, ncount=None, mpi="not_set", seed=None,
                 force_compile=None, output_path=None,
                 increment_folder_name=None, custom_flags=None,
                 executable_path=None, executable=None,
                 suppress_output=None, gravity=None, input_path=None,
                 package_path=None, checks=None, NeXus=None,
                 save_comp_pars=None, openacc=None):
        """
        Initialization of McStas Instrument

        Parameters
        ----------
        name : str
            Name of project, instrument file will be name + ".instr"

        keyword arguments:
            parameters : ParameterContainer or CalculatorParameters
                Parameters for this instrument

            author : str
                Name of author, written in instrument file

            origin : str
                Affiliation of author, written in instrument file

            input_path : str
                Work directory, will load components from this folder

            mpi : int
                Number of mpi threads to use in simulation

            output_path : str
                Sets data_folder_name

            increment_folder_name : bool
                Will update output_path if folder already exists, default True

            ncount : int
                Sets ncount

            mpi : int
                Sets thread count

            force_compile : bool
                If True (default) new instrument file is written, otherwise not

            custom_flags : str
                Sets custom_flags passed to mcrun

            executable : str
                Name of the executable

            executable_path : str
                Path to mcrun command, "" if already in path

            suppress_output : bool
                Set to True to surpress output

            gravity : bool
                If True, gravity will be simulated

            save_comp_pars : bool
                If True, McStas run writes all comp pars to disk
        """

        super().__init__(name, input=[],
                         output_keys=[name + "_data"],
                         output_data_types=[pyvinylMcStasData],
                         parameters=parameters)

        # Check required attributes has been set by class that inherits
        if not (hasattr(self, "particle") or
                hasattr(self, "package_name")):
            raise AttributeError("McCode_instr is a base class, use "
                                 + "McStas_instr or McXtrace_instr instead.")

        if not is_legal_filename(self.name + ".instr"):
            raise NameError("The instrument is called: \""
                            + self.name
                            + "\" resulting in an instrument file named: \""
                            + self.name + ".instr"
                            + "\" which is not a legal filename")

        if self.calculator_base_dir == "BaseCalculator":
            # If the base_dir was not set, set default to depend on instrument name
            self.calculator_base_dir = self.name + "_data"

        if author is None:
            self.author = "Python " + self.package_name
            self.author += " Instrument Generator"
        else:
            self.author = str(author)

        if origin is None:
            self.origin = "ESS DMSC"
        else:
            self.origin = str(origin)

        # Attempt to classify given parameters in McStas context
        for parameter in self.parameters.parameters.values():
            if isinstance(parameter.value, (float, int)):
                parameter.type = "double"
            elif isinstance(parameter.value, (str)):
                parameter.type = "string"
            else:
                # They will be typed when the instrument is written
                parameter.type = None

        self._run_settings = {}  # Settings for running simulation

        # Sets max_line_length and adds paths to run_settings
        self._read_calibration()

        # Settings that can't be changed later
        if input_path is not None:
            self.input_path = str(input_path)
            if not os.path.isdir(self.input_path):
                raise RuntimeError("Given input_path does not point to a "
                                   + "folder:\"" + self.input_path + '"')
        else:
            self.input_path = "."
        self._run_settings["run_path"] = self.input_path

        if package_path is not None:
            if not os.path.isdir(str(package_path)):
                raise RuntimeError("The package_path provided to mccode_instr "
                                   + " does not point to a + directory: \""
                                   + str(package_path) + "\"")
            self._run_settings["package_path"] = package_path

        # Settings for run that can be adjusted by user
        provided_run_settings = {"executable": executable,
                                 "checks": True,
                                 "NeXus": False}

        if executable_path is not None:
            provided_run_settings["executable_path"] = str(executable_path)

        if force_compile is not None:
            provided_run_settings["force_compile"] = force_compile
        else:
            provided_run_settings["force_compile"] = True

        if ncount is not None:
            provided_run_settings["ncount"] = ncount

        if mpi != "not_set":
            provided_run_settings["mpi"] = mpi

        if gravity is not None:
            provided_run_settings["gravity"] = gravity

        if seed is not None:
            provided_run_settings["seed"] = str(seed)

        if custom_flags is not None:
            provided_run_settings["custom_flags"] = custom_flags

        if suppress_output is not None:
            provided_run_settings["suppress_output"] = suppress_output

        if checks is not None:
            provided_run_settings["checks"] = checks

        if output_path is not None:
            provided_run_settings["output_path"] = output_path

        if increment_folder_name is not None:
            provided_run_settings["increment_folder_name"] = increment_folder_name

        if NeXus is not None:
            provided_run_settings["NeXus"] = NeXus

        if save_comp_pars is not None:
            provided_run_settings["save_comp_pars"] = save_comp_pars
        else:
            provided_run_settings["save_comp_pars"] = False

        if openacc is not None:
            provided_run_settings["openacc"] = openacc

        # Set run_settings, perform input sanitation
        self.settings(**provided_run_settings)

        # Read info on active McStas components
        package_path = self._run_settings["package_path"]
        run_path = self._run_settings["run_path"]
        self.component_reader = ComponentReader(package_path,
                                                input_path=run_path)

        self.component_class_lib = {}
        self.widget_interface = None

        # Holds major version of underlying package
        self.mccode_version = None

        # Avoid initializing if loading from dump
        if not hasattr(self, "declare_list"):
            self.declare_list = []
            self.user_var_list = []
            self.dependency_statement = ""
            self.search_statement_list = SearchStatementList()
            self.initialize_section = ("// Start of initialize for generated "
                                       + name + "\n")
            self.trace_section = ("// Start of trace section for generated "
                                  + name + "\n")
            self.finally_section = ("// Start of finally for generated "
                                    + name + "\n")

            # Handle components
            self.component_list = []  # List of components (have to be ordered)

            # Run subset settings
            self.run_from_ref = None
            self.run_to_ref = None
            self.run_to_comment = ""
            self.run_to_name = None
            self.run_from_component_parameters = None
            self.run_to_component_parameters = None

            # DumpDatabase
            self.dump_database = BeamDumpDatabase(self.name, self.input_path)

    @property
    def output_path(self) -> str:
        return self.base_dir

    @output_path.setter
    def output_path(self, value: str) -> None:
        self.calculator_base_dir = value

    def init_parameters(self):
        """
        Create empty ParameterContainer for new instrument
        """
        self.parameters = CalculatorParameters()

    def _read_calibration(self):
        """
        Placeholder method that should be overwritten by classes
        that inherit from McCode_instr.
        """
        pass

    def reset_run_points(self):
        """
        Reset run_from and run_to points to the full instrument
        """
        self.run_from_ref = None
        self.run_to_ref = None

    def show_run_subset(self):
        """
        Shows current subset of instrument selected with run_from and run_to methods
        """
        if self.run_from_ref is None and self.run_to_ref is None:
            print("No run_from or run_to point set.")
            return

        if self.run_from_ref is None:
            print("Running from start of the instrument", end="")
        else:
            print(f"Running from component named '{self.run_from_ref}'", end="")

        if self.run_to_ref is None:
            print(" to the end of the instrument.")
        else:
            print(f" to component named '{self.run_to_ref}'.")

    def run_to(self, component_ref, run_name="Run", comment=None, **kwargs):
        """
        Set limit for instrument, only run to given component, save MCPL there

        The method accepts keywords for the MCPL output component allowing to
        store for example userflags or setting the filename directly.

        component_ref : str / component object
            Name of component where the instrument simulation should end

        run_name : str
            Name associated with the generated beam dump

        comment : str
            Comment asscoiated with the generated beam dump
        """
        if isinstance(component_ref, Component):
            component_ref = component_ref.name

        # Check references are valid
        self.subset_check(start_ref=self.run_from_ref, end_ref=component_ref)

        self.run_to_ref = component_ref
        self.run_to_name = run_name

        if comment is not None:
            self.run_to_comment = str(comment)
        else:
            self.run_to_comment = ""

        if component_ref is not None:
            mcpl_par_name = "run_to_mcpl"

            if mcpl_par_name not in self.parameters.parameters:
                # Need to add parameter to instrument for mcpl filename
                self.add_parameter("string", mcpl_par_name)

            if "filename" not in kwargs:
                # Generate a reasonable filename
                auto_name = '"' + self.name + "_" + component_ref + ".mcpl" + '"'
                self.set_parameters({mcpl_par_name: auto_name})
            else:
                # Set the instrument parameter to the given filename
                self.set_parameters({mcpl_par_name: kwargs["filename"]})

            # Set the mcpl component parameter to the filename instrument parameter
            kwargs["filename"] = mcpl_par_name

            # Check the given keywords arguments are legal for the MCPL output component
            dummy_MCPL = self._create_component_instance("MCPL_output", "MCPL_output")
            try:
                dummy_MCPL.set_parameters(kwargs)
            except:
                # Provide information on what stage caused the problem
                print("Problems detected with input arguments for MCPL output component")
                # Show the exception for the failure to set parameters on the component
                dummy_MCPL.set_parameters(kwargs)

            # Store parameters for the MCPL output component
            self.run_to_component_parameters = kwargs

    def run_from(self, component_ref, run_name=None, tag=None, **kwargs):
        """
        Set limit for instrument, only run from given component, load MCPL ot start

        The method accepts keywords for the MCPL input component allowing to
        set for example the smear for direction / energy / position and
        repeat count.

        component_ref : str / component object
            Name of component where the instrument simulation should start

        run_name : str
            Run name of dump to use as starting point of simulation

        tag : integer
            Tag of the desired dump (only allowed if run_name is given)
        """

        if isinstance(component_ref, Component):
            component_ref = component_ref.name

        # Check references are valid
        self.subset_check(start_ref=component_ref, end_ref=self.run_to_ref)

        self.run_from_ref = component_ref

        if component_ref is not None:
            mcpl_par_name = "run_from_mcpl"

            if mcpl_par_name not in self.parameters.parameters:
                # Need to add parameter to instrument for mcpl filename
                self.add_parameter("string", mcpl_par_name)

            if "filename" not in kwargs:
                # Find newest dump from database
                newest_dump = self.dump_database.newest_at_point(component_ref, run=run_name)
                auto_name = '"' + newest_dump.data["data_path"] + '"'
                self.set_parameters({mcpl_par_name: auto_name})
            else:
                self.set_parameters({mcpl_par_name: kwargs["filename"]})

            if run_name is not None and tag is not None:
                dump = self.dump_database.get_dump(component_ref, run_name, tag)

                dump_filename = '"' + dump.data["data_path"] + '"'
                self.set_parameters({mcpl_par_name: dump_filename})

            kwargs["filename"] = mcpl_par_name

            # Ensure the kwargs are allowed
            dummy_MCPL = self._create_component_instance("MCPL_input", "MCPL_input")
            try:
                dummy_MCPL.set_parameters(kwargs)
            except:
                print("Problems detected with input arguments for MCPL input component")
                dummy_MCPL.set_parameters(kwargs)

            self.run_from_component_parameters = kwargs

    def show_dumps(self):
        component_names = [x.name for x in self.component_list]
        self.dump_database.show_in_order(component_names)

    def show_dump(self, point, run_name=None, tag=None):
        if isinstance(point, Component):
            point = point.name

        self.dump_database.get_dump(point, run_name, tag).print_all()

    def subset_check(self, start_ref, end_ref):
        """
        Checks that when the instrument is broken into subsets, it is still valid

        start_ref : str
            Name of starting component

        end_ref : str
            Name of end component
        """

        start_i, end_i = self.get_component_subset_index_range(start_ref, end_ref)
        if start_i > end_i:
            raise McStasError("Running from '" + start_ref + "' to '" + end_ref
                              + "' not possible as '" + end_ref + "' is before '"
                              + start_ref + "' in the component sequence.")
        if start_i == end_i:
            raise McStasError("Running from and to the same component is not supported "
                              + "here both run_from and run_to are set to "
                              + "'" + start_ref + "'.")

        # Check current subset of instrument is self contained
        is_self_contained = True
        try:
            self.check_for_relative_errors(start_ref=start_ref, end_ref=end_ref)
        except McStasError:
            is_self_contained = False

        if not is_self_contained:
            print("When using a subset of the instrument, component references "
                  "must be only internal as these sections are split into separate "
                  "files. When seeing only the specified subset of the instrument, "
                  "this reference can not be resolved.")
            self.check_for_relative_errors(start_ref=start_ref, end_ref=end_ref)

        if end_ref is None:
            # If there is no end_ref, there are no parts after to check
            return

        # Check the part after is self consistent
        is_self_contained = True
        try:
            self.check_for_relative_errors(start_ref=end_ref, allow_absolute=False)
        except McStasError:
            is_self_contained = False

        if not is_self_contained:
            print("When using a subset of the instrument, component references "
                  "must be only internal as these sections are split into separate "
                  "files. When seeing only the specified subset of the instrument, "
                  "this reference can not be resolved. \n"
                  "In this case the remaining instrument would fail.")
            self.check_for_relative_errors(start_ref=end_ref, allow_absolute=False)

    def add_parameter(self, *args, **kwargs):
        """
        Method for adding input parameter to instrument

        Type does not need to be specified, McStas considers that a floating
        point value with the type 'double'. Uses libpyvinyl Parameter object.

        Examples
        --------
        Creates a parameter with name wavelength and associated comment
        add_parameter("wavelength", comment="wavelength in [AA]")

        Creates a parameter with name A3 and default value
        add_parameter("A3", value=30, comment="A3 angle in [deg]")

        Creates a parameter with type string and name sample_name
        add_parameter("string", "sample_name")

        Parameters
        ----------

        (optional) parameter type : str
            type of input parameter, double, int, string

        parameter name : str
            name of parameter

        keyword arguments
            value : float, int or str
                Default value of parameter

            unit : str
                Unit to be displayed

            comment : str
                Comment displayed next to declaration of parameter

            options : list or value
                list or value of allowed values for this parameter
        """
        names = [x.name for x in self.declare_list
                 if isinstance(x, DeclareVariable)]
        names += [x.name for x in self.user_var_list
                  if isinstance(x, DeclareVariable)]
        names += [x.name for x in self.parameters.parameters.values()]

        par = provide_parameter(*args, **kwargs)

        if par.name in names:
            raise NameError(f"A parameter or variable with name '{par.name}'"
                            f" already exists!")

        self.parameters.add(par)

        return par

    def show_parameters(self, line_length=None):
        """
        Method for displaying current instrument parameters

        line_limit : int
            Maximum line length for terminal output
        """

        if len(self.parameters.parameters) == 0:
            print("No instrument parameters available")
            return

        if line_length is None:
            line_length = self.line_limit

        # Find longest fields
        types = []
        names = []
        values = []
        comments = []
        for parameter in self.parameters.parameters.values():
            types.append(str(parameter.type))
            names.append(str(parameter.name))
            values.append(str(parameter.value))
            if parameter.comment is None:
                comments.append("")
            else:
                comments.append(str(parameter.comment))

        longest_type = len(max(types, key=len))
        longest_name = len(max(names, key=len))
        longest_value = len(max(values, key=len))
        # In addition to the data 11 characters are added before the comment
        comment_start_point = longest_type + longest_name + longest_value + 11
        longest_comment = len(max(comments, key=len))
        length_for_comment = line_length - comment_start_point

        # Print to console
        for parameter in self.parameters.parameters.values():
            print(str(parameter.type).ljust(longest_type), end=' ')
            print(str(parameter.name).ljust(longest_name), end=' ')
            if parameter.value is None:
                print("  ", end=' ')
                print(" ".ljust(longest_value + 1), end=' ')
            else:
                print(" =", end=' ')
                print(str(parameter.value).ljust(longest_value + 1), end=' ')

            if parameter.comment is None:
                c_comment = ""
            else:
                c_comment = "// " + str(parameter.comment)

            if (length_for_comment < 5
                    or length_for_comment > len(c_comment)):
                print(c_comment)
            else:
                # Split comment into several lines
                comment = c_comment
                words = comment.split(" ")
                words_left = len(words)
                last_index = 0
                current_index = 0
                comment = ""
                iterations = 0
                max_iterations = 50
                while words_left > 0:
                    iterations += 1
                    if iterations > max_iterations:
                        #  Something went long, print on one line
                        break

                    line_left = length_for_comment

                    while line_left > 0:
                        if current_index >= len(words):
                            current_index = len(words) + 1
                            break
                        line_left -= len(str(words[current_index])) + 1
                        current_index += 1

                    current_index -= 1
                    for word in words[last_index:current_index]:
                        comment += word + " "
                    words_left = len(words) - current_index
                    if words_left > 0:
                        comment += "\n" + " " * comment_start_point
                        last_index = current_index

                if not iterations == max_iterations + 1:
                    print(comment)
                else:
                    print(c_comment.ljust(longest_comment))

    def show_variables(self):
        """
        Shows declared variables in instrument
        """

        all_variables = [x for x in self.declare_list + self.user_var_list
                         if isinstance(x, DeclareVariable)]

        type_heading = "type"
        variable_types = [x.type for x in all_variables]
        variable_types.append(type_heading)
        max_type_length = len(max(variable_types, key=len))

        name_heading = "variable name"
        variable_names = [x.name for x in all_variables]
        variable_names.append(name_heading)
        max_name_length = len(max(variable_names, key=len))

        vector_heading = "array length"
        variable_vector = [str(x.vector) for x in all_variables]
        variable_vector.append(vector_heading)
        max_vector_length = len(max(variable_vector, key=len))

        value_heading = "value"
        variable_values = [str(x.value) for x in all_variables]
        variable_values.append(value_heading)
        max_value_length = len(max(variable_values, key=len))

        padding = 2
        header = ""
        header += type_heading.ljust(max_type_length + padding)
        header += name_heading.ljust(max_name_length + padding)
        header += vector_heading.ljust(max_vector_length + padding)
        header += value_heading.ljust(max_value_length + padding)
        header += "\n"
        header += "-"*(max_type_length + max_name_length + max_value_length
                       + max_vector_length + 3*padding)
        header += "\n"

        string = "DECLARE VARIABLES \n"
        string += header

        if len(self.user_var_list) > 0:
            first_user_var = self.user_var_list[0]
        else:
            first_user_var = None

        for variable in all_variables:
            if variable is first_user_var:
                string += "\n"
                string += "USER VARIABLES (per neutron, only use in EXTEND)\n"
                string += header

            string += str(variable.type).ljust(max_type_length + padding)
            string += str(variable.name).ljust(max_name_length + padding)

            if variable.vector != 0:
                vector_string = str(variable.vector)
            else:
                vector_string = ""
            string += vector_string.ljust(max_vector_length + padding)

            if variable.value != "":
                value_string = str(variable.value)
            else:
                value_string = ""
            string += value_string.ljust(max_value_length + padding)
            string += "\n"

        print(string)

    def add_declare_var(self, *args, **kwargs):
        """
        Method for adding declared variable to instrument

        Parameters
        ----------

        parameter type : str
            type of input parameter

        parameter name : str
            name of parameter

        keyword arguments
            array : int
                default 0 for scalar, if specified length of array

            value : any
                Initial value of parameter, can be list of length vector

            comment : str
                Comment displayed next to declaration of parameter

        """

        # DeclareVariable class documented independently
        declare_par = DeclareVariable(*args, **kwargs)

        names = [x.name for x in self.declare_list
                 if isinstance(x, DeclareVariable)]
        names += [x.name for x in self.user_var_list
                  if isinstance(x, DeclareVariable)]
        names += [x.name for x in self.parameters.parameters.values()]

        if declare_par.name in names:
            raise NameError("Variable with name '" + declare_par.name
                            + "' already present in instrument!")
        
        self.declare_list.append(declare_par)
        return declare_par

    def append_declare(self, string):
        """
        Method for appending code to the declare section directly

        This method is not meant for declaring simple variables which
        should be done using add_declare_var. This method can be used
        to declare functions, structures and unions directly.

        Parameters
        ----------
        string : str
            code to be added to declare section
        """

        self.declare_list.append(string)

    def add_user_var(self, *args, **kwargs):
        """
        Method for adding user variable to instrument

        Parameters
        ----------

        parameter type : str
            type of input parameter

        parameter name : str
            name of parameter

        keyword arguments
            array : int
                default 0 for scalar, if specified length of array

            comment : str
                Comment displayed next to declaration of parameter

        """

        if "value" in kwargs:
            raise ValueError("Value not allowed for UserVars.")

        # DeclareVariable class documented independently
        user_par = DeclareVariable(*args, **kwargs)

        names = [x.name for x in self.declare_list
                 if isinstance(x, DeclareVariable)]
        names += [x.name for x in self.user_var_list
                  if isinstance(x, DeclareVariable)]
        names += [x.name for x in self.parameters.parameters.values()]

        if user_par.name in names:
            raise NameError("Variable with name '" + user_par.name
                            + "' already present in instrument!")

        self.user_var_list.append(user_par)
        return user_par

    def move_user_vars_to_declare(self):
        """
        Moves all uservars to declare for compatibility with McStas 2.X
        """

        for var in self.user_var_list:
            self.declare_list.append(var)

        self.user_var_list = []

    def append_initialize(self, string):
        """
        Method for appending code to the initialize section

        The initialize section consists of c code and will be compiled,
        thus any syntax errors will crash the simulation. Code is added
        on a new line for each call to this method.

        Parameters
        ----------
        string : str
            code to be added to initialize section
        """

        self.initialize_section = self.initialize_section + string + "\n"

    def append_initialize_no_new_line(self, string):
        """
        Method for appending code to the initialize section, no new line

        The initialize section consists of c code and will be compiled,
        thus any syntax errors will crash the simulation. Code is added
        to the current line.

        Parameters
        ----------
        string : str
            code to be added to initialize section
        """

        self.initialize_section = self.initialize_section + string

    def append_finally(self, string):
        """
        Method for appending code to the finally section of instrument

        The finally section consists of c code and will be compiled,
        thus any syntax errors will crash the simulation. Code is added
        on a new line for each call to this method.

        Parameters
        ----------
        string : str
            code to be added to finally section

        """

        self.finally_section = self.finally_section + string + "\n"

    def append_finally_no_new_line(self, string):
        """
        Method for appending code to the finally section of instrument

        The finally section consists of c code and will be compiled,
        thus any syntax errors will crash the simulation. Code is added
        to the current line.

        Parameters
        ----------
        string : str
            code to be added to finally section
        """

        self.finally_section = self.finally_section + string

    """
    # Handle trace string differently when components also exists
    #  A) Could have trace string as a component attribute and set
    #     it before / after
    #  B) Could have trace string as a McStas_instr attribute and
    #     still attach placement to components
    #  C) Could have trace string as a different object and place it
    #     in component_list, but have a write function named as the
    #     component write function?
    """

    def append_trace(self, string):
        """
        Appends code to trace section, only used in write_c_files

        The most common way to add code to the trace section is to add
        components using the seperate methods for this.  This method is
        kept as is still used for writing to c files used in legacy
        code.  Each call creates a new line.

        Parameters
        ----------
        string : str
            code to be added to trace
        """

        self.trace_section = self.trace_section + string + "\n"

    def append_trace_no_new_line(self, string):
        """
        Appends code to trace section, only used in write_c_files

        The most common way to add code to the trace section is to add
        components using the seperate methods for this.  This method is
        kept as is still used for writing to c files used in legacy
        code.  No new line is made with this call.

        Parameters
        ----------
        string : str
            code to be added to trace
        """

        self.trace_section = self.trace_section + string

    def available_components(self, *args):
        """
        Helper method that shows available components to the user

        If called without any arguments it will display the available
        component categories. If a category is given as a string in
        the first input, components in that category are printed.

        Parameters
        ----------
        first argument (optional): str
            Category that matches one of the McStas component folders

        """
        if len(args) == 0:
            print("Here are the available component categories:")
            self.component_reader.show_categories()
            print("Call available_components(category_name) to display")

        else:
            category = args[0]
            print("Here are all components in the "
                  + category
                  + " category.")
            this_reader = self.component_reader
            line_lim = self.line_limit
            this_reader.show_components_in_category(category,
                                                    line_length=line_lim)

    def component_help(self, name, **kwargs):
        """
        Method for showing parameters for a component before adding it
        to the instrument

        keyword arguments
            line_length : int
                Maximum line length in output to terminal
        """

        dummy_instance = self._create_component_instance("dummy", name)
        dummy_instance.show_parameters(**kwargs)

    def _create_component_instance(self, name, component_name, **kwargs):
        """
        Dynamically creates a class for the requested component type

        Created classes kept in dictionary, if the same component type
        is requested again, the class in the dictionary is used.  The
        method returns an instance of the created class that was
        initialized with the parameters passed to this function.
        """

        if component_name not in self.component_class_lib:
            comp_info = self.component_reader.read_name(component_name)

            input_dict = {key: None for key in comp_info.parameter_names}
            input_dict["parameter_names"] = comp_info.parameter_names
            input_dict["parameter_defaults"] = comp_info.parameter_defaults
            input_dict["parameter_types"] = comp_info.parameter_types
            input_dict["parameter_units"] = comp_info.parameter_units
            input_dict["parameter_comments"] = comp_info.parameter_comments
            input_dict["category"] = comp_info.category
            input_dict["line_limit"] = self.line_limit

            dynamic_component_class = type(component_name, (Component,),
                                           input_dict)

            # add this class to globals to allow for pickling
            globals()[component_name] = dynamic_component_class

            self.component_class_lib[component_name] = dynamic_component_class

        return self.component_class_lib[component_name](name, component_name,
                                                        **kwargs)

    def add_component(self, name, component_name=None, *, before=None,
                      after=None, AT=None, AT_RELATIVE=None, ROTATED=None,
                      ROTATED_RELATIVE=None, RELATIVE=None, WHEN=None,
                      EXTEND=None, GROUP=None, JUMP=None, SPLIT=None,
                      comment=None, c_code_before=None, c_code_after=None):
        """
        Method for adding a new Component instance to the instrument

        Creates a new Component instance in the instrument.  This
        requires a unique instance name of the component to be used for
        future reference and the name of the McStas component to be
        used.  The component is placed at the end of the instrument file
        unless otherwise specified with the after and before keywords.
        The Component may be initialized using other keyword arguments,
        but all attributes can be set with approrpiate methods.

        Parameters
        ----------
        name : str
            Unique name of component instance

        component_name : str
            Name of McStas component to create instance of

        Keyword arguments:
            after : str
                Place this component after component with given name

            before : str
                Place this component before component with given name

            AT : List of 3 floats
                Sets AT_data, position relative to reference

            AT_RELATIVE : str
                Sets reference component for postion

            ROTATED : List of 3 floats
                Sets ROTATED_data, rotation relative to reference

            ROTATED_RELATIVE : str
                Sets reference component for rotation

            RELATIVE : str
                Sets reference component for both position and rotation

            WHEN : str
                Sets when condition which must be a logical c expression

            EXTEND : str
                Initialize the extend section with a line of c code

            GROUP : str
                Name of the group this component should belong to

            JUMP : str
                Set code for McStas JUMP statement

            comment : str
                Comment that will be displayed before the component
        """

        if component_name is None:
            # Try to interpret name as the name of a McStas component
            #  and the python variable name as the given name to this
            #  instance of the McStas component.
            if name in self.component_reader.component_path:
                # Name is an available McStas component!
                component_name = name

                # Find name through call
                text = ("When adding a component without giving both "
                        "name and type it is necessary to assign the "
                        "component object a python variable name that "
                        "can be used for the McStas component.")
                name = find_python_variable_name(error_text=text, n_levels=2)
            else:
                raise NameError("As no name is given, the input is interpreted"
                                " as a component name, yet no component of"
                                " type " + str(name) + " is found in McStas"
                                " installation or work directory.")

        if name in [x.name for x in self.component_list]:
            raise NameError(("Component name \"" + str(name)
                             + "\" used twice, " + self.package_name
                             + " does not allow this."
                             + " Rename or remove one instance of this"
                             + " name."))

        # Condense keyword input relating to component to a dict
        component_input = {"AT": AT, "AT_RELATIVE": AT_RELATIVE,
                           "ROTATED": ROTATED,
                           "ROTATED_RELATIVE": ROTATED_RELATIVE,
                           "RELATIVE": RELATIVE, "WHEN": WHEN,
                           "EXTEND": EXTEND, "GROUP": GROUP, "JUMP": JUMP,
                           "SPLIT": SPLIT, "comment": comment,
                           "c_code_before": c_code_before,
                           "c_code_after": c_code_after}

        new_component = self._create_component_instance(name, component_name,
                                                        **component_input)

        self._insert_component(new_component, before=before, after=after)
        return new_component

    def copy_component(self, name, original_component=None, *, before=None,
                       after=None, AT=None, AT_RELATIVE=None, ROTATED=None,
                       ROTATED_RELATIVE=None, RELATIVE=None, WHEN=None,
                       EXTEND=None, GROUP=None, JUMP=None, SPLIT=None,
                       comment=None, c_code_before=None, c_code_after=None):
        """
        Method for adding a copy of a Component instance to the instrument

        Creates a copy of Component instance in the instrument.  This
        requires a unique instance name of the component to be used for
        future reference and the name of the McStas component to be
        used.  The component is placed at the end of the instrument file
        unless otherwise specified with the after and before keywords.
        The component may be initialized using other keyword arguments,
        but all attributes can be set with approrpiate methods.

        Parameters
        ----------
        name : str
            Unique name of component instance

        original_component : str
            Name of component instance to create copy of

        Keyword arguments:
            after : str
                Place this component after component with given name

            before : str
                Place this component before component with given name

            AT : List of 3 floats
                Sets AT_data, position relative to reference

            AT_RELATIVE : str
                Sets reference component for postion

            ROTATED : List of 3 floats
                Sets ROTATED_data, rotation relative to reference

            ROTATED_RELATIVE : str
                Sets reference component for rotation

            RELATIVE : str
                Sets reference component for both position and rotation

            WHEN : str
                Sets when condition which must be a logical c expression

            EXTEND : str
                Initialize the extend section with a line of c code

            GROUP : str
                Name of the group this component should belong to

            JUMP : str
                Set code for McStas JUMP statement

            comment : str
                Comment that will be displayed before the component
        """

        if original_component is None:
            # Try to interpret name as the name of a McStas component
            #  to be copied and the python variable name as the given
            #  name to the new instance of the McStas component.
            if isinstance(name, Component):
                name = original_component.name

            component_names = [x.name for x in self.component_list]
            if name in component_names:
                # name is an existing component name
                original_component = name

                # Find new name through call
                text = ("When making a component copy without providing both "
                        "name of the new instance and name of the original "
                        "component it is necessary to assign the new "
                        "component object to a python variable name that can "
                        "be used for the new McStas component object.")
                name = find_python_variable_name(error_text=text, n_levels=2)
            else:
                raise NameError("As no name is given, the input is interpreted"
                                " as a component name, yet no component named"
                                + str(name) + " is found in the McStas "
                                "instrument.")

        if isinstance(original_component, Component):
            original_component = original_component.name

        # Condense keyword input relating to component to a dict
        component_input = {"AT": AT, "AT_RELATIVE": AT_RELATIVE,
                           "ROTATED": ROTATED,
                           "ROTATED_RELATIVE": ROTATED_RELATIVE,
                           "RELATIVE": RELATIVE, "WHEN": WHEN,
                           "EXTEND": EXTEND, "GROUP": GROUP, "JUMP": JUMP,
                           "SPLIT": SPLIT, "comment": comment,
                           "c_code_before": c_code_before,
                           "c_code_after": c_code_after}

        """
        If the name starts with COPY, use unique naming as described in the
        McStas manual.
        """
        component_names = [x.name for x in self.component_list]

        if name.startswith("COPY("):
            target_name = name.split("(", 1)[1]
            target_name = target_name.split(")", 1)[0]
            instance_name = target_name

            label = 0
            instance_name = target_name + "_" + str(label)
            while instance_name in component_names:
                instance_name = target_name + "_" + str(label)
                label += 1

        if name in component_names:
            raise NameError(("Component name \"" + str(name)
                             + "\" used twice, " + self.package_name
                             + " does not allow this."
                             + " Rename or remove one instance of this"
                             + " name."))

        if original_component not in component_names:
            raise NameError("Component name \"" + str(original_component)
                            + "\" was not found in the " + self.package_name
                            + " instrument. and thus can not be copied.")
        else:
            component_to_copy = self.get_component(original_component)

        new_component = copy.deepcopy(component_to_copy)
        new_component.name = name  # Set new name, duplicate names not allowed

        self._insert_component(new_component, before=before, after=after)

        # Run set_keyword_input for keyword arguments to take effect
        new_component.set_keyword_input(**component_input)

        return new_component

    def remove_component(self, name):
        """
        Removes component with given name from instrument
        """

        # Check for errors before
        errors_before = self.has_errors()

        if isinstance(name, Component):
            name = name.name

        component_names = [x.name for x in self.component_list]
        index_to_remove = component_names.index(name)
        self.component_list.pop(index_to_remove)

        # Check for errors after removing
        errors_after = self.has_errors()

        if not errors_before and errors_after:
            print("Removing the component '" + name + "' introduced errors in "
                  "the instrument, run check_for_errors() for more "
                  "information.")

    def move_component(self, name, before=None, after=None):
        """
        Moves component with given name to before or after
        """
        if isinstance(name, Component):
            name = name.name

        if before is None and after is None:
            raise RuntimeError("Must specify 'before' or 'after' when moving "
                               "a component.")

        # Check for errors before
        errors_before = self.has_errors()

        if isinstance(name, Component):
            name = name.name

        component_names = [x.name for x in self.component_list]
        index_to_remove = component_names.index(name)
        moved_component = self.component_list.pop(index_to_remove)
        self._insert_component(moved_component, before=before, after=after)

        # Check for errors after moving
        errors_after = self.has_errors()

        if not errors_before and errors_after:
            print("Moving the component '" + name + "' introduced errors in "
                  "the instrument, run check_for_errors() for more "
                  "information.")

    def _insert_component(self, component, before=None, after=None):
        """
        Inserts component into sequence of components held by instrument

        Internal method to handle placement of a new component in the
        list of components held by this instrument.

        name : str
            Instance name of component

        component : Component object
            Component object to be inserted

        before : str or Component object
            Reference to component to place this one before

        after : str or Component object
            Reference to coponent to place this one after
        """

        if before is not None and after is not None:
            raise RuntimeError("Only specify either 'before' or 'after'.")

        if before is None and after is None:
            # If after and before keywords absent, place component at the end
            self.component_list.append(component)
            return

        if after is not None:
            index_addition = 1
            reference = after
            description = "after"
        if before is not None:
            index_addition = 0
            reference = before
            description = "before"

        if isinstance(reference, Component):
            reference = reference.name

        component_names = [x.name for x in self.component_list]
        if reference not in component_names:
            raise NameError("Trying to add a component " + description
                            + " a component named '" + str(after)
                            + "', but a component with that name was"
                            + " not found.")

        new_index = component_names.index(reference) + index_addition
        self.component_list.insert(new_index, component)

    def get_component(self, name):
        """
        Get the component instance of component with specified name

        This method is used to get direct access to any component
        instance in the instrument.  The component instance can be
        manipulated in much the same way, but it is not necessary to
        specify the name in each call.

        Parameters
        ----------
        name : str
            Unique name of component whose instance should be returned
        """

        component_names = [x.name for x in self.component_list]
        if name in component_names:
            index = component_names.index(name)
            return self.component_list[index]
        else:
            raise NameError(("No component was found with name \""
                             + str(name) + "\"!"))

    def get_last_component(self):
        """
        Get the component instance of last component in the instrument

        This method is used to get direct access to any component
        instance in the instrument.  The component instance can be
        manipulated in much the same way, but it is not necessary to
        specify the name in each call.
        """

        return self.component_list[-1]

    def print_component(self, name):
        """
        Method for printing summary of contents in named component

        Parameters
        ----------
        name : str
            Unique name of component to print
        """

        component = self.get_component(name)
        component.print_long()

    def print_component_short(self, name):
        """
        Method for printing summary of contents in named component

        Parameters
        ----------
        name : str
            Unique name of component to print
        """
        component = self.get_component(name)
        component.print_short()

    def print_components(self, line_length=None):
        """
        Obsolete method, use show_components instead

        Method for printing overview of all components in instrument

        Provides overview of component names, what McStas component is
        used for each and their position and rotation in space.

        keyword arguments:
        line_length : int
            Maximum line length in console
        """
        warnings.warn("Print components is changing name to show_components for consistency.")
        self.show_components(line_length)

    def show_components(self, line_length=None):
        """
        Method for printing overview of all components in instrument

        Provides overview of component names, what McStas component is
        used for each and their position and rotation in space.

        keyword arguments:
        line_length : int
            Maximum line length in console
        """
        if len(self.component_list) == 0:
            print("No components added to instrument object yet.")
            return

        printed_components = self.make_component_subset()

        if len(printed_components) == 0:
            print("No components in subset.")
            return

        if self.run_from_ref is not None:
            print("Showing subset of instrument after cut at '"
                  + self.run_from_ref
                  + "' component.")

        if line_length is None:
            line_limit = self.line_limit
        else:
            if not isinstance(line_length, int):
                raise ValueError("Show components now shows components in"
                                 " instrument instead of help. For help,"
                                 " use available_components instead. \n"
                                 "The argument for show_components is"
                                 " line_length and has to be an integer.")
            line_limit = line_length

        component_names = [x.name for x in printed_components]
        longest_name = len(max(component_names, key=len))

        # todo Investigate how this could have been done in a better way
        # Find longest field for each type of data printed
        component_type_list = []
        at_xyz_list = []
        at_relative_list = []
        rotated_xyz_list = []
        rotated_relative_list = []
        for component in printed_components:
            component_type_list.append(component.component_name)
            at_xyz_list.append(str(component.AT_data[0])
                               + str(component.AT_data[1])
                               + str(component.AT_data[2]))
            at_relative_list.append(component.AT_relative)
            rotated_xyz_list.append(str(component.ROTATED_data[0])
                                    + str(component.ROTATED_data[1])
                                    + str(component.ROTATED_data[2]))
            rotated_relative_list.append(component.ROTATED_relative)

        longest_component_name = len(max(component_type_list, key=len))
        longest_at_xyz_name = len(max(at_xyz_list, key=len))
        longest_at_relative_name = len(max(at_relative_list, key=len))
        longest_rotated_xyz_name = len(max(rotated_xyz_list, key=len))
        longest_rotated_relative_name = len(max(rotated_relative_list,
                                                key=len))

        # Padding settings, 0,0,6,0,6 is minimum values
        name_pad = 0
        comp_name_pad = 0
        AT_pad = 6  # requires (, , ) in addition to data length
        RELATIVE_pad = 0
        ROTATED_pad = 6  # requires (, , ) in addition to data length
        ROTATED_characters = 7  # ROTATED is 7 characters
        AT_characters = 2  # AT is 2 characters
        SPACING_between_strings = 7  # combining 8 strings, 7 spaces

        # Check if longest line length exceeded
        longest_line_length = (longest_name + name_pad
                               + longest_component_name + comp_name_pad
                               + longest_at_xyz_name + AT_pad
                               + longest_at_relative_name + RELATIVE_pad
                               + longest_rotated_xyz_name + ROTATED_pad
                               + longest_rotated_relative_name
                               + ROTATED_characters
                               + AT_characters
                               + SPACING_between_strings)

        def coordinates_to_string(data):
            return ("("
                    + str(data[0]) + ", "
                    + str(data[1]) + ", "
                    + str(data[2]) + ")")

        n_lines = 1
        """
        If calculated line length is above the limit loaded from the
        configuration file, attempt to split the output over an
        additional line. This is hardcoded up to 3 lines.
        """

        if longest_line_length > line_limit:
            n_lines = 2
            longest_at_xyz_name = max([longest_at_xyz_name,
                                       longest_rotated_xyz_name])
            longest_rotated_xyz_name = longest_at_xyz_name
            RELATIVE_pad = 0

            SPACING_between_strings = 4  # combining 5 strings, 4 spaces

            longest_line_length_at = (longest_name
                                      + comp_name_pad
                                      + longest_component_name
                                      + comp_name_pad
                                      + longest_at_xyz_name
                                      + AT_pad
                                      + longest_at_relative_name
                                      + ROTATED_characters
                                      + SPACING_between_strings)
            longest_line_length_rotated = (longest_name
                                           + comp_name_pad
                                           + longest_component_name
                                           + comp_name_pad
                                           + longest_rotated_xyz_name
                                           + ROTATED_pad
                                           + longest_rotated_relative_name
                                           + ROTATED_characters
                                           + SPACING_between_strings)

            if (longest_line_length_at > line_limit
                    or longest_line_length_rotated > line_limit):
                n_lines = 3

        if n_lines == 1:
            for component in printed_components:
                p_name = str(component.name)
                p_name = p_name.ljust(longest_name + name_pad)

                p_comp_name = str(component.component_name)
                p_comp_name = p_comp_name.ljust(longest_component_name
                                                + comp_name_pad)

                p_AT = coordinates_to_string(component.AT_data)
                p_AT = p_AT.ljust(longest_at_xyz_name + AT_pad)

                p_AT_RELATIVE = str(component.AT_relative)
                p_AT_RELATIVE = p_AT_RELATIVE.ljust(longest_at_relative_name
                                                    + RELATIVE_pad)

                p_ROTATED = coordinates_to_string(component.ROTATED_data)
                p_ROTATED = p_ROTATED.ljust(longest_rotated_xyz_name
                                            + ROTATED_pad)

                p_ROTATED_RELATIVE = str(component.ROTATED_relative)

                if component.ROTATED_specified:
                    print(p_name, p_comp_name,
                          "AT", p_AT, p_AT_RELATIVE,
                          "ROTATED", p_ROTATED, p_ROTATED_RELATIVE)
                else:
                    print(p_name, p_comp_name, "AT", p_AT, p_AT_RELATIVE)

        elif n_lines == 2:
            for component in printed_components:
                p_name = str(component.name)
                p_name = p_name.ljust(longest_name + name_pad)

                p_comp_name = str(component.component_name)
                p_comp_name = p_comp_name.ljust(longest_component_name
                                                + comp_name_pad)

                p_AT = coordinates_to_string(component.AT_data)
                p_AT = p_AT.ljust(longest_at_xyz_name + AT_pad)

                p_AT_RELATIVE = str(component.AT_relative)
                p_AT_RELATIVE = p_AT_RELATIVE.ljust(longest_at_relative_name
                                                    + RELATIVE_pad)

                p_ROTATED_align = " "*(longest_name
                                       + comp_name_pad
                                       + longest_component_name
                                       + comp_name_pad)

                p_ROTATED = coordinates_to_string(component.ROTATED_data)
                p_ROTATED = p_ROTATED.ljust(longest_rotated_xyz_name
                                            + ROTATED_pad)

                p_ROTATED_RELATIVE = str(component.ROTATED_relative)

                if component.ROTATED_specified:
                    print(p_name, p_comp_name,
                          "AT     ", p_AT, p_AT_RELATIVE, "\n",
                          p_ROTATED_align, "ROTATED",
                          p_ROTATED, p_ROTATED_RELATIVE)
                else:
                    print(p_name, p_comp_name,
                          "AT     ", p_AT, p_AT_RELATIVE)

        elif n_lines == 3:
            for component in printed_components:
                p_name = bcolors.BOLD + str(component.name) + bcolors.ENDC

                p_comp_name = (bcolors.BOLD
                               + str(component.component_name)
                               + bcolors.ENDC)

                p_AT = coordinates_to_string(component.AT_data)

                p_AT_RELATIVE = str(component.AT_relative)

                p_ROTATED = coordinates_to_string(component.ROTATED_data)

                p_ROTATED_RELATIVE = str(component.ROTATED_relative)

                if component.ROTATED_specified:
                    print(p_name + " ", p_comp_name, "\n",
                          " AT     ", p_AT, p_AT_RELATIVE, "\n",
                          " ROTATED", p_ROTATED, p_ROTATED_RELATIVE)
                else:
                    print(p_name + " ", p_comp_name, "\n",
                          " AT     ", p_AT, p_AT_RELATIVE)

        if self.run_to_ref is not None:
            print("Showing subset of instrument until cut at '"
                  + self.run_to_ref
                  + "' component.")

    def write_c_files(self):
        """
        Obsolete method for writing instrument parts to c files

        It is possible to use this function to write c files to a folder
        called generated_includes that can then be included in the
        different sections of a McStas instrument. Component objects are
        NOT written to these files, but rather the contents of the
        trace_section that can be set using the append_trace method.
        """
        path = os.getcwd()
        path = os.path.join(path, "generated_includes")
        if not os.path.isdir(path):
            try:
                os.mkdir(path)
            except OSError:
                print("Creation of the directory %s failed" % path)

        file_path = os.path.join(".", "generated_includes",
                                 self.name + "_declare.c")
        with open(file_path, "w") as fo:
            fo.write("// declare section for %s \n" % self.name)

        file_path = os.path.join(".", "generated_includes",
                                 self.name + "_declare.c")
        with open(file_path, "a") as fo:
            for dec_line in self.declare_list:
                if isinstance(dec_line, str):
                    # append declare section parts written here
                    fo.write(dec_line)
                else:
                    dec_line.write_line(fo)
                fo.write("\n")
            fo.close()

            file_path = os.path.join(".", "generated_includes",
                                     self.name + "_initialize.c")
            fo = open(file_path, "w")
            fo.write(self.initialize_section)
            fo.close()

            file_path = os.path.join(".", "generated_includes",
                                     self.name + "_trace.c")
            fo = open(file_path, "w")
            fo.write(self.trace_section)
            fo.close()

            file_path = os.path.join(".", "generated_includes",
                                     self.name + "_component_trace.c")
            fo = open(file_path, "w")
            for component in self.component_list:
                component.write_component(fo)

    def has_errors(self):
        """
        Method that returns true if errors are found in instrument
        """

        has_errors = True
        try:
            self.check_for_errors()
            has_errors = False
        except:
            pass

        return has_errors

    def check_for_errors(self):
        """
        Methods that checks for common McStas errors

        Currently checks for:
        RELATIVE for AT and ROTATED reference a component that have not yet
        been defined.

        Using variables in components that have not been defined.
        """

        # Check RELATIVE exists
        self.check_for_relative_errors()

        # Check variables used have been declared
        parameters = [x.name for x in self.parameters]
        variables = [x.name for x in self.declare_list
                     if isinstance(x, DeclareVariable)]
        pars_and_vars = parameters + variables

        # Check component parameters
        for component in self.component_list:
            component.check_parameters(pars_and_vars)

    def check_for_relative_errors(self, start_ref=None, end_ref=None, allow_absolute=True):
        """
        Method for checking if RELATIVE locations does not contain unknown references

        Using the start_ref and end_ref keyword arguments, a subset of the
        instrument can be checked for internal consistency.
        """

        if start_ref is None and end_ref is None:
            component_list = self.make_component_subset()
        elif start_ref == self.run_from_ref and end_ref == self.run_to_ref:
            component_list = self.make_component_subset()
        else:
            start_i, end_i = self.get_component_subset_index_range(start_ref, end_ref)
            component_list = self.component_list[start_i:end_i]

        seen_instrument_names = []
        for component in component_list:
            seen_instrument_names.append(component.name)

            if component.name == start_ref:
                # Avoid checking first component when start_ref != 0
                continue

            references = []
            if component.AT_reference not in (None, "PREVIOUS"):
                references.append(component.AT_reference)

            if not allow_absolute:
                if component.AT_relative == "ABSOLUTE":
                    raise McStasError("Component '" + component.name
                                      + "' was set relative to ABSOLUTE"
                                      + " which is not allowed after an"
                                      + " instrument split.")

            if ( component.ROTATED_specified and
                   component.ROTATED_reference not in (None, "PREVIOUS")):
                references.append(component.ROTATED_reference)

            if not allow_absolute:
                if component.ROTATED_relative == "ABSOLUTE" and component.ROTATED_specified:
                    raise McStasError("Component '" + component.name
                                      + "' was set relative to ABSOLUTE"
                                      + " which is not allowed after an"
                                      + " instrument split.")

            for ref in references:
                if ref not in seen_instrument_names:
                    raise McStasError("Component '" + str(component.name) +
                                      "' referenced unknown component"
                                      " named '" + str(ref) + "'.\n"
                                      "This check can be skipped with"
                                      " settings(checks=False)")


    def read_instrument_file(self):
        """
        Reads current instrument file if it exists, otherwise creates one first
        """

        instrument_path = os.path.join(self.input_path, self.name + ".instr")
        if not os.path.exists(instrument_path):
            self.write_full_instrument()
            if not os.path.exists(instrument_path):
                raise RuntimeError("Failing to write instrument file.")

        with open(instrument_path, "r") as fo:
            return fo.read()

    def show_instrument_file(self, line_numbers=False):
        """
        Displays the current instrument file

        Parameters
        ----------
        line_numbers : bool
            Select whether line numbers should be displayed
        """

        instrument_code = self.read_instrument_file()

        if not line_numbers:
            print(instrument_code)
            return
        else:
            lines = instrument_code.split("\n")
            number_of_lines = len(lines)
            line_space = len(str(number_of_lines))
            for index, line in enumerate(lines):
                line_number = str(index + 1).ljust(line_space) + " | "
                full_line = line_number + line
                print(full_line.replace("\n", ""))

    def write_full_instrument(self):
        """
        Method for writing full instrument file to disk

        This method writes the instrument described by the instrument
        objects to disk with the name specified in the initialization of
        the object.
        """

        # Catch common errors before writing the instrument
        if self._run_settings["checks"]:
            self.check_for_errors()

        # Create file identifier
        fo = open(os.path.join(self.input_path, self.name + ".instr"), "w")

        # Write quick doc start
        fo.write("/" + 80*"*" + "\n")
        fo.write("* \n")
        fo.write("* McStas, neutron ray-tracing package\n")
        fo.write("*         Copyright (C) 1997-2008, All rights reserved\n")
        fo.write("*         Risoe National Laboratory, Roskilde, Denmark\n")
        fo.write("*         Institut Laue Langevin, Grenoble, France\n")
        fo.write("* \n")
        fo.write("* This file was written by McStasScript, which is a \n")
        fo.write("* python based McStas instrument generator written by \n")
        fo.write("* Mads Bertelsen in 2019 while employed at the \n")
        fo.write("* European Spallation Source Data Management and \n")
        fo.write("* Software Centre\n")
        fo.write("* \n")
        fo.write("* Instrument %s\n" % self.name)
        fo.write("* \n")
        fo.write("* %Identification\n")  # Could allow the user to insert this
        fo.write("* Written by: %s\n" % self.author)
        t_format = "%H:%M:%S on %B %d, %Y"
        fo.write("* Date: %s\n" % datetime.datetime.now().strftime(t_format))
        fo.write("* Origin: %s\n" % self.origin)
        fo.write("* %INSTRUMENT_SITE: Generated_instruments\n")
        fo.write("* \n")
        fo.write("* \n")
        fo.write("* %Parameters\n")
        # Add description of parameters here
        fo.write("* \n")
        fo.write("* %End \n")
        fo.write("*"*80 + "/\n")
        fo.write("\n")
        fo.write("DEFINE INSTRUMENT %s (" % self.name)
        fo.write("\n")
        # Insert parameters
        parameter_list = list(self.parameters)
        end_chars = [", "]*len(parameter_list)
        if len(end_chars) >= 1:
            end_chars[-1] = " "
        for variable, end_char in zip(parameter_list, end_chars):
            write_parameter(fo, variable, end_char)
        fo.write(")\n")
        if self.dependency_statement != "":
            fo.write("DEPENDENCY " + str(self.dependency_statement) + "\n")
        fo.write("\n")

        # Write declare
        fo.write("DECLARE \n%{\n")
        for dec_line in self.declare_list:
            if isinstance(dec_line, str):
                # append declare section parts written here
                fo.write(dec_line)
            else:
                dec_line.write_line(fo)
            fo.write("\n")
        fo.write("%}\n\n")

        # Write uservars
        if len(self.user_var_list) > 0:
            fo.write("USERVARS \n%{\n")
            for user_var in self.user_var_list:
                user_var.value = ""  # Ensure no value
                user_var.write_line(fo)
                fo.write("\n")
            fo.write("%}\n\n")

        # Write initialize
        fo.write("INITIALIZE \n%{\n")
        fo.write(self.initialize_section)
        # Alternatively hide everything in include
        """
        fo.write("%include "generated_includes/"
                  + self.name + "_initialize.c")
        """

        save_parameter_code = ""
        for component in self.make_component_subset():
            if component.save_parameters or self._run_settings["save_comp_pars"]:
                save_parameter_code += component.make_write_string()

        if save_parameter_code != "":
            fo.write('MPI_MASTER(\n')
            fo.write('FILE *file = fopen("component_parameters.txt", "w");\n')
            fo.write('if (file) {\n')
            fo.write(save_parameter_code)
            fo.write('} else {\n')
            fo.write('  perror("fopen");\n')
            fo.write('}\n')
            fo.write(')\n')

        fo.write("%}\n\n")

        # Write trace
        fo.write("TRACE \n")

        # Write all components, the first should get the instrument search list
        search_object = copy.deepcopy(self.search_statement_list)
        for component in self.make_component_subset():
            component.write_component(fo, instrument_search=search_object)
            search_object = None  # Remove for remaining components

        # Write finally
        fo.write("FINALLY \n%{\n")
        fo.write(self.finally_section)
        # Alternatively hide everything in include
        fo.write("%}\n")

        # End instrument file
        fo.write("\nEND\n")

        fo.close()

    def get_component_subset_index_range(self, start_ref=None, end_ref=None):
        """
        Provides start and end index for components in run_from to run_to range

        Optionally start_ref and end_ref can be given manually which would
        overwrite the internal run_from and run_to references.
        """

        if start_ref is None:
            start_ref = self.run_from_ref

        if end_ref is None:
            end_ref = self.run_to_ref

        # Starting with component named run_from_ref, ending with run_to_ref
        component_names = [x.name for x in self.component_list]
        start_index = 0
        end_index = len(self.component_list)
        if start_ref is not None:
            start_index = component_names.index(start_ref)

        if end_ref is not None:
            end_index = component_names.index(end_ref)

        return start_index, end_index

    def make_component_subset(self):
        """
        Uses run_from and run_to specifications to extract subset of components

        Adds MCPL component at start and/or end as needed, and adjusts the
        surrounding components as necessary.
        """

        if self.run_from_ref is None and self.run_to_ref is None:
            # Simple case, just return full component list
            return self.component_list

        start_index, end_index = self.get_component_subset_index_range()

        # Create a copy of the used component instances
        if start_index == end_index:
            component_subset = [copy.deepcopy(self.component_list[start_index])]
        else:
            component_subset = copy.deepcopy(self.component_list[start_index:end_index])

        if self.run_from_ref is not None:
            # Add MCPL input component
            MCPL_in = self._create_component_instance("MCPL_" + self.run_from_ref, "MCPL_input")
            MCPL_in.set_comment("Automatically inserted to split instrument into parts")
            if self.run_from_component_parameters is not None:
                MCPL_in.set_parameters(**self.run_from_component_parameters)

            # Ensure first component reset to MCPL position
            first_component = component_subset[0]

            # Since a copy of the component is used, we can alter some properties safely
            first_component.set_AT([0, 0, 0], "ABSOLUTE")
            if first_component.ROTATED_specified:
                first_component.set_ROTATED([0, 0, 0], "ABSOLUTE")

            component_subset = [MCPL_in] + component_subset

        if self.run_to_ref is not None:
            # MCPL component will replace the component after the last included
            replaced_component = self.component_list[end_index]

            # Add MCPL output component
            MCPL_out = self._create_component_instance("MCPL_" + self.run_to_ref, "MCPL_output")
            MCPL_out.set_comment("Automatically inserted to split instrument into parts")
            if self.run_to_component_parameters is not None:
                MCPL_out.set_parameters(**self.run_to_component_parameters)
            MCPL_out.set_AT(replaced_component.AT_data, RELATIVE=replaced_component.AT_reference)
            if replaced_component.ROTATED_specified:
                MCPL_out.set_ROTATED(replaced_component.ROTATED_data, RELATIVE=replaced_component.ROTATED_reference)

            component_subset += [MCPL_out]

        return component_subset

    def set_dependency(self, string):
        """
        Sets the DEPENDENCY line of instruments, expanding its system search

        The dependency line can be used to tell McStas to search for files in
        additional locations. Double quotes are added.

        Parameters
        ----------
            string : str
                The dependency string
        """

        # Disable by giving an empty string
        if len(string) == 0:
            self.dependency_statement = ""
            return

        if string[0] != '"' and string[-1] != '"':
            string = '"' + string + '"'

        self.dependency_statement = string

    def add_search(self, statement, SHELL=False, help_name=""):
        """
        Adds a search statement to the instrument

        The dependency line can be used to tell McStas to search for files in
        additional locations. Double quotes are added.

        Parameters
        ----------
            statement : str
                The search statement

            SHELL : bool (default False)
                if True, shell keyword is added

            help_name : str
                Name used in help messages regarding the component search
        """

        self.search_statement_list.add_statement(SearchStatement(statement, SHELL=SHELL))
        self.component_reader.load_components_from_folder(statement, name=help_name)

    def clear_search(self):
        """
        Clears the instrument of all search statements
        """

        self.search_statement_list.clear()

        # Reset component_reader
        self.component_class_lib = {}
        package_path = self._run_settings["package_path"]
        run_path = self._run_settings["run_path"]
        self.component_reader = ComponentReader(package_path,
                                                input_path=run_path)

    def show_search(self):
        """
        Shows all search statements on instrument level
        """

        print(self.search_statement_list)

    def settings(self, ncount=None, mpi="not_set", seed=None,
                 force_compile=None, output_path=None,
                 increment_folder_name=None, custom_flags=None,
                 executable=None, executable_path=None,
                 suppress_output=None, gravity=None, checks=None,
                 openacc=None, NeXus=None, save_comp_pars=False):
        """
        Sets settings for McStas run performed with backengine

        Some options are mandatory, for example output_path, which can not
        already exist, if it does data will be read from this folder. If the
        mcrun command is not in the PATH of the system, the absolute path can
        be given with the executable_path keyword argument. This path could
        also already have been set at initialization of the instrument object.

        Parameters
        ----------
        Keyword arguments
            output_path : str
                Sets data_folder_name
            increment_folder_name : bool
                Will update output_path if folder already exists, default True
            ncount : int
                Sets ncount
            mpi : int
                Sets thread count
            force_compile : bool
                If True (default) new instrument file is written, otherwise not
            custom_flags : str
                Sets custom_flags passed to mcrun
            executable : str
                Name of the executable
            executable_path : str
                Path to mcrun command, "" if already in path
            suppress_output : bool
                Set to True to suppress output
            gravity : bool
                If True, gravity will be simulated
            openacc : bool
                If True, adds --openacc to mcrun call
            NeXus : bool
                If True, adds --format=NeXus to mcrun call
            save_comp_pars : bool
                If True, McStas run writes all comp pars to disk
        """

        settings = {}
        if executable_path is not None:
            if not os.path.isdir(str(executable_path)):
                raise RuntimeError("The executable_path provided in "
                                   + "settings does not point to a"
                                   + "directory: \""
                                   + str(executable_path) + "\"")
            settings["executable_path"] = executable_path

        if executable is not None:
            # check provided executable can be converted to string
            str(executable)
            settings["executable"] = executable

        if force_compile is not None:
            if not isinstance(force_compile, bool):
                raise TypeError("force_compile must be a bool.")
            settings["force_compile"] = force_compile

        if increment_folder_name is not None:
            if not isinstance(increment_folder_name, bool):
                raise TypeError("increment_folder_name must be a bool.")
            settings["increment_folder_name"] = increment_folder_name

        if ncount is not None:
            if not isinstance(ncount, (float, int)):
                raise TypeError("ncount must be a number.")
            settings["ncount"] = ncount

        if mpi != "not_set":  # None is a legal value for mpi
            if not isinstance(mpi, (type(None), int)):
                raise TypeError("mpi must be an integer or None.")
            settings["mpi"] = mpi

        if gravity is not None:
            settings["gravity"] = bool(gravity)

        if custom_flags is not None:
            str(custom_flags)  # Check a string is given
            settings["custom_flags"] = custom_flags

        if seed is not None:
            settings["seed"] = seed

        if suppress_output is not None:
            settings["suppress_output"] = suppress_output

        if checks is not None:
            settings["checks"] = checks

        if output_path is not None:
            self.output_path = output_path

        if openacc is not None:
            settings["openacc"] = bool(openacc)

        if NeXus is not None:
            settings["NeXus"] = bool(NeXus)

        if save_comp_pars is not None:
            settings["save_comp_pars"] = bool(save_comp_pars)

        self._run_settings.update(settings)

    def settings_string(self):
        """
        Returns a string describing settings stored in this instrument object
        """

        variable_space = 20
        description = "Instrument settings:\n"

        if "ncount" in self._run_settings:
            value = self._run_settings["ncount"]
            description += "  ncount:".ljust(variable_space)
            description += "{:.2e}".format(value) + "\n"

        if "mpi" in self._run_settings:
            value = self._run_settings["mpi"]
            if value is not None:
                description += "  mpi:".ljust(variable_space)
                description += str(int(value)) + "\n"

        if "gravity" in self._run_settings:
            value = self._run_settings["gravity"]
            description += "  gravity:".ljust(variable_space)
            description += str(value) + "\n"

        if "seed" in self._run_settings:
            value = self._run_settings["seed"]
            description += "  seed:".ljust(variable_space)
            description += str(int(value)) + "\n"

        description += "  output_path:".ljust(variable_space)
        description += str(self.output_path) + "\n"

        if "increment_folder_name" in self._run_settings:
            value = self._run_settings["increment_folder_name"]
            description += "  increment_folder_name:".ljust(variable_space)
            description += str(value) + "\n"

        if "run_path" in self._run_settings:
            value = self._run_settings["run_path"]
            description += "  run_path:".ljust(variable_space)
            description += str(value) + "\n"

        if "package_path" in self._run_settings:
            value = self._run_settings["package_path"]
            description += "  package_path:".ljust(variable_space)
            description += str(value) + "\n"

        if "executable_path" in self._run_settings:
            value = self._run_settings["executable_path"]
            description += "  executable_path:".ljust(variable_space)
            description += str(value) + "\n"

        if "executable" in self._run_settings:
            value = self._run_settings["executable"]
            description += "  executable:".ljust(variable_space)
            description += str(value) + "\n"

        if "force_compile" in self._run_settings:
            value = self._run_settings["force_compile"]
            description += "  force_compile:".ljust(variable_space)
            description += str(value) + "\n"

        if "NeXus" in self._run_settings:
            value = self._run_settings["NeXus"]
            description += "  NeXus:".ljust(variable_space)
            description += str(value) + "\n"

        if "openacc" in self._run_settings:
            value = self._run_settings["openacc"]
            description += "  openacc:".ljust(variable_space)
            description += str(value) + "\n"

        if "save_comp_pars" in self._run_settings:
            value = self._run_settings["save_comp_pars"]
            description += "  save_comp_pars:".ljust(variable_space)
            description += str(value) + "\n"

        return description.strip()

    def show_settings(self):
        """
        Prints settings stored in this instrument object
        """
        print(self.settings_string())

    def backengine(self):
        """
        Runs instrument with McStas / McXtrace, saves data in data attribute

        This method will write the instrument to disk and then run it using
        the mcrun command of the system. Settings are set using settings
        method.
        """

        self.__add_input_to_mcpl()

        instrument_path = os.path.join(self.input_path, self.name + ".instr")
        if not os.path.exists(instrument_path) or self._run_settings["force_compile"]:
            self.write_full_instrument()

        parameters = {}
        for parameter in self.parameters:
            if parameter.value is None:
                raise RuntimeError("Parameter value not set for parameter: '" + parameter.name
                                   + "' set with set_parameters.")

            parameters[parameter.name] = parameter.value

        options = self._run_settings
        options["parameters"] = parameters
        options["output_path"] = self.output_path

        # Set up the simulation
        simulation = ManagedMcrun(self.name + ".instr", **options)

        # Run the simulation and return data
        simulation.run_simulation()

        # Load data and store in __data
        #data = simulation.load_results()
        #self._set_data(data)
        
        ## look for MCPL_output components and the defined filenames
        self.__add_mcpl_to_output(simulation)

        # simulation results from .dat files loaded as dict
        data = simulation.load_results()
        data_dict = {"data": data}
        # adding to the libpyvinyl output datacollection with key = sim_data_key
        sim_data_key = self.output_keys[0]
        output_data = self.output[sim_data_key] 
        output_data.set_dict(data_dict)

        if self.run_to_ref is not None:
            filename = self.parameters.parameters["run_to_mcpl"].value

            # Check for mcpl files and load those to database
            db = self.dump_database
            out = db.load_data(expected_filename=filename,
                               data_folder_path=simulation.data_folder_name,
                               parameters=self.parameters.parameters,
                               dump_point=self.run_to_ref,
                               run_name=self.run_to_name,
                               comment=self.run_to_comment)

            if out is None:
                print("Expected MCPL file was not loaded!")

        if "data" not in self.output[sim_data_key].get_data():
            print("\n\nNo data returned.")
            return None
        else:
            return self.output[sim_data_key].get_data()["data"]

    def __add_input_to_mcpl(self):
        try:
            mcpl_file = self.input["mcpl"].filename
            for comp in self.component_list:
                if comp.component_name == "MCPL_input":
                    comp.filename = '"' + mcpl_file + '"'
                    break
        except:
            return

    def __add_mcpl_to_output(self, managed_mcrun):
        MCPL_extension = MCPLDataFormat.format_register()["ext"]
        num_mcpl_files = 0
        for comp in self.component_list[::-1]: # starting from the last one!
            if comp.component_name == "MCPL_output":
                num_mcpl_files = num_mcpl_files+1

                absfilepath = os.path.join(managed_mcrun.data_folder_name,
                                           comp.filename.strip('"').strip("'")
                                           +MCPL_extension)
                if os.path.exists(absfilepath+".gz"):
                    absfilepath+=".gz"
                if os.path.exists(absfilepath) is False:
                    raise RuntimeError(f"MCPL file: {absfilepath} nor {absfilepath}.gz not found")
                mcpl_file =  pyvinylMCPLData.from_file(absfilepath)
                if num_mcpl_files>1:
                    mcpl_file.key = mcpl_file+str(num_mcpl_files)
                self.output.add_data(mcpl_file)
                self.output_keys.append(mcpl_file.key)
        
    def run_full_instrument(self, **kwargs):
        """
        Runs McStas instrument described by this class, returns list of
        McStasData

        This method will write the instrument to disk and then run it
        using the mcrun command of the system. Options are set using
        keyword arguments.  Some options are mandatory, for example
        output_path, which can not already exist, if it does data will
        be read from this folder.  If the mcrun command is not in the
        path of the system, the absolute path can be given with the
        executable_path keyword argument.  This path could also already
        have been set at initialization of the instrument object.

        Parameters
        ----------
        Keyword arguments
            output_path : str
                Sets data_folder_name
            ncount : int
                Sets ncount
            mpi : int
                Sets thread count
            parameters : dict
                Sets parameters
            custom_flags : str
                Sets custom_flags passed to mcrun
            force_compile : bool
                If True (default) new instrument file is written, otherwise not
            executable_path : str
                Path to mcrun command, "" if already in path
        """
        warnings.warn(
            "run_full_instrument will be removed in future version of McStasScript. \n"
            + "Instead supply parameters with set_parameters, set settings with "
            + "settings and use backengine() to run. See examples in package. "
            + "Documentation now at https://mads-bertelsen.github.io")

        if "foldername" in kwargs:
            kwargs["output_path"] = kwargs["foldername"]
            del kwargs["foldername"]

        if "parameters" in kwargs:
            self.set_parameters(kwargs["parameters"])
            del kwargs["parameters"]

        self.settings(**kwargs)

        return self.backengine()

    def show_instrument(self, format="webgl", width=800, height=450, new_tab=False):
        """
        Uses mcdisplay to show the instrument in web browser

        If this method is performed from a jupyter notebook and use the webgl
        format the interface will be shown in the notebook using an IFrame.

        Keyword arguments
        -----------------
            format : str
                'webgl' or 'window' format for display
            width : int
                width of IFrame if used in notebook
            height : int
                height of IFrame if used in notebook
            new_tab : bool
                Open webgl in new browser tab
        """

        parameters = {}
        for parameter in self.parameters:
            if parameter.value is None:
                raise RuntimeError("Unspecified parameter: '" + parameter.name
                                   + "' set with set_parameters.")

            parameters[parameter.name] = parameter.value

        # add parameters to command
        parameter_string = ""
        for key, val in parameters.items():
            parameter_string = (parameter_string + " "
                                + str(key)  # parameter name
                                + "="
                                + str(val))  # parameter value

        if self.package_name == "McXtrace":
            executable = "mxdisplay"
        else:
            executable = "mcdisplay"

        if format == "webgl":
            executable = executable+"-webgl"
        elif format == "window":
            executable = executable+"-pyqtgraph"

        # Platform dependent, check both package_path and bin
        executable_path = self._run_settings["executable_path"]
        bin_path = os.path.join(executable_path, executable)

        if not os.path.isfile(bin_path):
            # Take bin in package path into account
            package_path = self._run_settings["package_path"]
            bin_path = os.path.join(package_path, "bin", executable)

        dir_name_original = self.name + "_mcdisplay"
        dir_name = dir_name_original
        index = 0
        while os.path.exists(os.path.join(self.input_path, dir_name)):
            dir_name = dir_name_original + "_" + str(index)
            index += 1

        dir_control = "--dirname " + dir_name + " "

        self.write_full_instrument()

        instr_path = os.path.join(self.input_path, self.name + ".instr")
        instr_path = os.path.abspath(instr_path)

        try:
            shell = get_ipython().__class__.__name__
            is_notebook = shell == "ZMQInteractiveShell"
        except:
            is_notebook = False

        options = ""
        if is_notebook and executable == "mcdisplay-webgl" and not new_tab:
            options += "--nobrowse "

        full_command = ('"' + bin_path + '" '
                        + dir_control
                        + options
                        + instr_path
                        + " " + parameter_string)

        process = subprocess.run(full_command, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 universal_newlines=True,
                                 cwd=self.input_path)

        if not is_notebook or executable != "mcdisplay-webgl":
            print(process.stderr)
            print(process.stdout)
            return

        html_path = os.path.join(self.input_path, dir_name, "index.html")
        if not os.path.exists(html_path):
            print(process.stderr)
            print(process.stdout)
            print("")
            print("mcdisplay run failed.")
            return

        # Create IFrame in ipython that shows instrument

        return IFrame(src=html_path, width=width, height=height)

    def show_diagram(self, analysis=False, variable=None, limits=None):
        """
        Shows diagram of component connections in insrument

        Shows a diagram with all components as text fields and arrows between
        them showing the AT RELATIVE and ROTATED RELATIVE connections. Spatial
        connections are shown in blue, and rotational in red. ROTATED
        connections are only shown when they are specified. To see the intensity
        and number of rays over the course of the instrument, use analysis=True.

        parameters:
        analysis : bool
            If True, a plot of intensity and ncount over the instrument is included
        """

        if self.has_errors() and self._run_settings["checks"]:
            print("The instrument has some error, this diagram is still "
                  "shown as it may help find the bug.")

        if variable is not None:
            analysis = True

        instrument_diagram(self, analysis=analysis, variable=variable, limits=limits)

        if self._run_settings["checks"]:
            self.check_for_errors()

    def show_analysis(self, variable=None):
        beam_diag = IntensityDiagnostics(self)
        beam_diag.run_general(variable=variable)
        beam_diag.plot()

    def saveH5(self, filename: str, openpmd: bool = True):
        """
        Not relevant, but required from BaseCalculator, will be removed
        """
        pass


class McStas_instr(McCode_instr):
    """
    Main class for writing a McStas instrument using McStasScript

    Initialization of McStas_instr sets the name of the instrument file
    and its methods are used to add all aspects of the instrument file.
    The class also holds methods for writing the finished instrument
    file to disk and to run the simulation.

    Attributes
    ----------
    name : str
        name of instrument file

    author : str, default "Python Instrument Generator"
        name of user of McStasScript, written to the file

    origin : str, default "ESS DMSC"
        origin of instrument file (affiliation)

    input_path : str, default "."
        directory in which simulation is executed, uses components found there

    output_path : str
        directory in which the data is written

    executable_path : str
        absolute path of mcrun command, or empty if it is in path

    parameters : ParameterContainer
        contains all input parameters to be written to file

    declare_list : list of DeclareVariable instances
        contains all declare parrameters to be written to file

    initialize_section : str
        string containing entire initialize section to be written

    trace_section : str
        string containing trace section (OBSOLETE)

    finally_section : str
        string containing entire finally section to be written

    component_list : list of component instances
        list of components in the instrument

    component_class_lib : dict
        dict of custom Component classes made at run time

    component_reader : ComponentReader
        ComponentReader instance for reading component files

    package_path : str
        Path to mccode package containing component folders

    run_settings : dict
        Dict of options set with settings

    data : list
        List of McStasData objects produced by last run

    Methods
    -------
    add_parameter(*args, **kwargs)
        Adds input parameter to the define section

    add_declare_var(type, name)
        Add declared variable called name of given type to the declare section

    append_declare(string)
        Appends to the declare section

    append_initialize(string)
        Appends a string to the initialize section, then adds new line

    append_initialize_no_new_line(string)
        Appends a string to the initialize section

    append_finally(string)
        Appends a string to finally section, then adds new line

    append_finally_no_new_line(string)
        Appends a string to finally section

    append_trace(string)
        Obsolete method, add components instead (used in write_c_files)

    append_trace_no_new_line(string)
        Obsolete method, add components instead (used in write_c_files)

    available_components(string)
        Shows available components in given category

    component_help(name)
        Shows help on component of given name

    add_component(instance_name, component_name, **kwargs)
        Add a component to the instrument file

    copy_component(new_component_name, original_component, **kwargs)
        Makes a copy of original_component with new_component_name

    get_component(instance_name)
        Returns component instance with name instance_name

    get_last_component()
        Returns component instance of last component

    print_component(instance_name)
        Prints an overview of current state of named component

    print_component_short(instance_name)
        Prints short overview of current state of named component

    show_components()
        Prints overview of postion / rotation of all components

    write_c_files()
        Writes c files for %include in generated_includes folder

    write_full_instrument()
        Writes full instrument file to current directory

    show_instrument()
        Shows instrument using mcdisplay

    set_parameters(dict)
        Inherited from libpyvinyl BaseCalculator

    settings(**kwargs)
        Sets settings for performing simulation

    backengine()
        Performs simulation, saves in data attribute

    run_full_instrument(**kwargs)
        Deprecated method for performing the simulation

    interface()
        Shows interface with jupyter notebook widgets

    get_interface_data()
        Returns data set from latest simulation in widget
    """
    def __init__(self, name, **kwargs):
        """
        Initialization of McStas Instrument

        Parameters
        ----------
        name : str
            Name of project, instrument file will be name + ".instr"

        keyword arguments:
            parameters : ParameterContainer or CalculatorParameters
                Parameters for this instrument

            dumpfile: str
                File path to dump file to be loaded

            author : str
                Name of author, written in instrument file

            origin : str
                Affiliation of author, written in instrument file

            executable_path : str
                Absolute path of mcrun or empty if already in path

            input_path : str
                Work directory, will load components from this folder
        """
        self.particle = "neutron"
        self.package_name = "McStas"
        executable = "mcrun"

        super().__init__(name, executable=executable, **kwargs)

        try:
            self.mccode_version = check_mcstas_major_version(self._run_settings["executable_path"])
        except:
            self.mccode_version = "Unknown"

    def _read_calibration(self):
        this_dir = os.path.dirname(os.path.abspath(__file__))
        configuration_file_name = os.path.join(this_dir, "..",
                                               "configuration.yaml")
        if not os.path.isfile(configuration_file_name):
            raise NameError("Could not find configuration file!")
        with open(configuration_file_name, 'r') as ymlfile:
            config = yaml.safe_load(ymlfile)

        if type(config) is dict:
            self.line_limit = config["other"]["characters_per_line"]

        if "MCSTAS" in os.environ: # We are in a McStas environment, use that
            self._run_settings["executable_path"] = os.path.dirname(shutil.which("mcrun"))
            self._run_settings["package_path"] = os.environ["MCSTAS"]
        elif type(config) is dict:
            self._run_settings["executable_path"] = config["paths"]["mcrun_path"]
            self._run_settings["package_path"] = config["paths"]["mcstas_path"]
        else:
            # This happens in unit tests that mocks open
            self._run_settings["executable_path"] = ""
            self._run_settings["package_path"] = ""
            self.line_limit = 180

    @classmethod
    def from_dump(cls, dumpfile: str):
        """Load a dill dump from a dumpfile.

        Overwrites a libpyvinyl method to load McStas components

        :param dumpfile: The file name of the dumpfile.
        :type dumpfile: str
        :return: The calculator object restored from the dumpfile.
        :rtype: CalcualtorClass
        """

        with open(dumpfile, "rb") as fhandle:
            try:
                # Loads necessary component classes from unpackers installation
                tmp = CustomMcStasUnpickler(fhandle).load()
            except:
                raise IOError("Cannot load calculator from {}.".format(dumpfile))

            if not isinstance(tmp, cls):
                raise TypeError(f"The object in the file {dumpfile} is not a {cls}")

        return tmp


class McXtrace_instr(McCode_instr):
    """
    Main class for writing a McXtrace instrument using McStasScript

    Initialization of McXtrace_instr sets the name of the instrument file
    and its methods are used to add all aspects of the instrument file.
    The class also holds methods for writing the finished instrument
    file to disk and to run the simulation.

    Attributes
    ----------
    name : str
        name of instrument file

    author : str, default "Python Instrument Generator"
        name of user of McStasScript, written to the file

    origin : str, default "ESS DMSC"
        origin of instrument file (affiliation)

    input_path : str, default "."
        directory in which simulation is executed, uses components found there

    output_path : str
        directory in which the data is written

    executable_path : str
        absolute path of mcrun command, or empty if it is in path

    parameters : ParameterContainer
        contains all input parameters to be written to file

    declare_list : list of DeclareVariable instances
        contains all declare parrameters to be written to file

    initialize_section : str
        string containing entire initialize section to be written

    trace_section : str
        string containing trace section (OBSOLETE)

    finally_section : str
        string containing entire finally section to be written

    component_list : list of component instances
        list of components in the instrument

    component_class_lib : dict
        dict of custom Component classes made at run time

    component_reader : ComponentReader
        ComponentReader instance for reading component files

    package_path : str
        Path to mccode package containing component folders

    run_settings : dict
        Dict of options set with settings

    data : list
        List of McStasData objects produced by last run

    Methods
    -------
    add_parameter(*args, **kwargs)
        Adds input parameter to the define section

    add_declare_var(type, name)
        Add declared variable called name of given type to the declare section

    append_declare(string)
        Appends to the declare section

    append_initialize(string)
        Appends a string to the initialize section, then adds new line

    append_initialize_no_new_line(string)
        Appends a string to the initialize section

    append_finally(string)
        Appends a string to finally section, then adds new line

    append_finally_no_new_line(string)
        Appends a string to finally section

    append_trace(string)
        Obsolete method, add components instead (used in write_c_files)

    append_trace_no_new_line(string)
        Obsolete method, add components instead (used in write_c_files)

    available_components(string)
        Shows available components in given category

    component_help(name)
        Shows help on component of given name

    add_component(instance_name, component_name, **kwargs)
        Add a component to the instrument file

    copy_component(new_component_name, original_component, **kwargs)
        Makes a copy of original_component with new_component_name

    get_component(instance_name)
        Returns component instance with name instance_name

    get_last_component()
        Returns component instance of last component

    print_component(instance_name)
        Prints an overview of current state of named component

    print_component_short(instance_name)
        Prints short overview of current state of named component

    show_components()
        Prints overview of postion / rotation of all components

    write_c_files()
        Writes c files for %include in generated_includes folder

    write_full_instrument()
        Writes full instrument file to current directory

    show_instrument()
        Shows instrument using mcdisplay

    set_parameters(dict)
        Inherited from libpyvinyl BaseCalculator

    settings(**kwargs)
        Sets settings for performing simulation

    backengine()
        Performs simulation, saves in data attribute

    run_full_instrument(**kwargs)
        Deprecated method for performing the simulation

    interface()
        Shows interface with jupyter notebook widgets

    get_interface_data()
        Returns data set from latest simulation in widget
    """
    def __init__(self, name, **kwargs):
        """
        Initialization of McXtrace Instrument

        Parameters
        ----------
        name : str
            Name of project, instrument file will be name + ".instr"

        keyword arguments:
            parameters : ParameterContainer or CalculatorParameters
                Parameters for this instrument

            dumpfile: str
                File path to dump file to be loaded

            author : str
                Name of author, written in instrument file

            origin : str
                Affiliation of author, written in instrument file

            executable_path : str
                Absolute path of mcrun or empty if already in path

            input_path : str
                Work directory, will load components from this folder
        """
        self.particle = "x-ray"
        self.package_name = "McXtrace"
        executable = "mxrun"

        super().__init__(name, executable=executable, **kwargs)

        try:
            self.mccode_version = check_mcxtrace_major_version(self._run_settings["executable_path"])
        except:
            self.mccode_version = "Unknown"

    def _read_calibration(self):
        this_dir = os.path.dirname(os.path.abspath(__file__))
        configuration_file_name = os.path.join(this_dir, "..",
                                               "configuration.yaml")
        if not os.path.isfile(configuration_file_name):
            raise NameError("Could not find configuration file!")
        with open(configuration_file_name, 'r') as ymlfile:
            config = yaml.safe_load(ymlfile)

        if type(config) is dict:
            self.line_limit = config["other"]["characters_per_line"]

        if "MCXTRACE" in os.environ: # We are in a McXtrace environment, use that
            self._run_settings["executable_path"] = os.path.dirname(shutil.which("mxrun"))
            self._run_settings["package_path"] = os.environ["MCXTRACE"]
        elif type(config) is dict:
            self._run_settings["executable_path"] = config["paths"]["mxrun_path"]
            self._run_settings["package_path"] = config["paths"]["mcxtrace_path"]
        else:
            # This happens in unit tests that mocks open
            self._run_settings["executable_path"] = ""
            self._run_settings["package_path"] = ""
            self.line_limit = 180

    @classmethod
    def from_dump(cls, dumpfile: str):
        """Load a dill dump from a dumpfile.

        Overwrites a libpyvinyl method to load McStas components

        :param dumpfile: The file name of the dumpfile.
        :type dumpfile: str
        :return: The calculator object restored from the dumpfile.
        :rtype: CalcualtorClass
        """

        with open(dumpfile, "rb") as fhandle:
            try:
                # Loads necessary component classes from unpackers installation
                tmp = CustomMcXtraceUnpickler(fhandle).load()
            except:
                raise IOError("Cannot load calculator from {}.".format(dumpfile))

            if not isinstance(tmp, cls):
                raise TypeError(f"The object in the file {dumpfile} is not a {cls}")

        return tmp
