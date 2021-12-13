from __future__ import print_function

import os
import datetime
import yaml
import subprocess
import copy
import warnings

from libpyvinyl.BaseCalculator import BaseCalculator
from libpyvinyl.Parameters.Collections import CalculatorParameters

from mcstasscript.helper.mcstas_objects import DeclareVariable
from mcstasscript.helper.mcstas_objects import ParameterVariable
from mcstasscript.helper.mcstas_objects import Component
from mcstasscript.helper.mcstas_objects import ParameterContainer
from mcstasscript.helper.component_reader import ComponentReader
from mcstasscript.helper.managed_mcrun import ManagedMcrun
from mcstasscript.helper.formatting import is_legal_filename
from mcstasscript.helper.formatting import bcolors
from mcstasscript.jb_interface.simulation_interface import SimInterface


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

    show_components(string)
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

    print_components()
        Prints overview of postion / rotation of all components

    write_c_files()
        Writes c files for %include in generated_includes folder

    write_full_instrument()
        Writes full instrument file to current directory

    show_instrument()
        Shows instrument using mcdisplay

    run_full_instrument(**kwargs)
        Writes instrument files and runs simulation.
        Returns list of McStasData

    interface()
        Shows interface with jupyter notebook widgets

    get_interface_data()
        Returns data set from latest simulation in widget
    """

    def __init__(self, name, parameters=None, dumpfile=None, **kwargs):
        """
        Initialization of McStas Instrument

        Parameters
        ----------
        name : str
            Name of project, instrument file will be name + ".instr"

        keyword arguments:
            author : str
                Name of author, written in instrument file

            origin : str
                Affiliation of author, written in instrument file

            executable_path : str
                Absolute path of mcrun or empty if already in path

            input_path : str
                Work directory, will load components from this folder
        """

        super().__init__(name, parameters, dumpfile, **kwargs)

        # If no parameters given, initialize parameter container
        if self.parameters is None:
            self.parameters = ParameterContainer()
        else:
            if not isinstance(self.parameters, ParameterContainer):
                # Need to convert McStasScript parameters
                if isinstance(self.parameters, CalculatorParameters):
                    mcstasscript_parameters = ParameterContainer()
                    mcstasscript_parameters.import_parameters(self.parameters)
                    self.parameters = mcstasscript_parameters

                else:
                    raise RuntimeError("Given parameters object not"
                                       + " recognized.")

        # Check required attributes has been set by class that inherits
        if not (hasattr(self, "particle") or
                hasattr(self, "executable") or
                hasattr(self, "package_name")):
            raise AttributeError("McCode_instr is a base class, use "
                                 + "McStas_intr or McXtrace_instr instead.")

        if not is_legal_filename(self.name + ".instr"):
            raise NameError("The instrument is called: \""
                            + self.name
                            + "\" resulting in an instrument file named: \""
                            + self.name + ".instr"
                            + "\" which is not a legal filename")

        if "author" in kwargs:
            self.author = str(kwargs["author"])
        else:
            self.author = "Python " + self.package_name
            self.author += " Instrument Generator"

        if "origin" in kwargs:
            self.origin = str(kwargs["origin"])
        else:
            self.origin = "ESS DMSC"

        if "input_path" in kwargs:
            self.input_path = str(kwargs["input_path"])
            if not os.path.isdir(self.input_path):
                raise RuntimeError("Given input_path does not point to a "
                                   + "folder:\"" + self.input_path + '"')
        else:
            self.input_path = "."

        self._read_calibration()

        if "executable_path" in kwargs:
            self.executable_path = str(kwargs["executable_path"])
            if not os.path.isdir(self.executable_path):
                raise RuntimeError("Given executable_path does not point to "
                                   + "a folder:\"" + self.executable_path
                                   + '"')

        if "package_path" in kwargs:
            self.package_path = str(kwargs["package_path"])
            if not os.path.isdir(self.package_path):
                raise RuntimeError("Given package_path does not point to "
                                   + "a folder:\"" + self.package_path + '"')

        elif self.package_path == "":
            raise NameError("At this stage of development "
                            + "McStasScript need the absolute path "
                            + "for the " + self.package_name
                            + " installation as keyword named "
                            + "package_path or in configuration.yaml")

        # Read info on active McStas components
        self.component_reader = ComponentReader(self.package_path,
                                                input_path=self.input_path)

        self.component_class_lib = {}
        self.widget_interface = None

        # Ensure output_path field exist
        if not hasattr(self, "output_path"):
            self.output_path = None

        # Avoid initializing if loading from dump
        if not hasattr(self, "current_run_options"):
            self.current_run_options = None

            self.declare_list = []
            self.initialize_section = ("// Start of initialize for generated "
                                       + name + "\n")
            self.trace_section = ("// Start of trace section for generated "
                                  + name + "\n")
            self.finally_section = ("// Start of finally for generated "
                                    + name + "\n")
            # Handle components
            self.component_list = []  # List of components (have to be ordered)
            self.component_name_list = []  # List of component names

    def _read_calibration(self):
        """
        Place holder method that should be overwritten by classes
        that inherit from McCode_instr.
        """
        pass

    def add_parameter(self, *args, **kwargs):
        """
        Method for adding input parameter to instrument

        Type does not need to be specified, McStas considers that a floating
        point value with the type double.

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
            value : any
                Default value of parameter

            comment : str
                Comment displayed next to declaration of parameter
        """
        # ParameterVariable class documented independently
        par = ParameterVariable(*args, ** kwargs)
        self.parameters.add(par)
        return par

    def show_parameters(self, **kwargs):
        """
        Method for displaying current instrument parameters

        keyword arguments
            line_length : int
                Maximum line length for terminal output
        """
        if "line_length" in kwargs:
            line_limit = kwargs["line_length"]
        else:
            line_limit = self.line_limit

        self.parameters.show_parameters(line_limit)

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
    #  A) Coul d have trace string as a component attribute and set
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

    def show_components(self, *args):
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
            print("Call show_components(category_name) to display")

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

            input_dict = {}
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

    def add_component(self, name, component_name, **kwargs):
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

        if name in self.component_name_list:
            raise NameError(("Component name \"" + str(name)
                             + "\" used twice, " + self.package_name
                             + " does not allow this."
                             + " Rename or remove one instance of this"
                             + " name."))

        # Insert component after component with this name
        if "after" in kwargs:
            if kwargs["after"] not in self.component_name_list:
                raise NameError(("Trying to add a component after a component"
                                 + " named \"" + str(kwargs["after"])
                                 + "\", but a component with that name was"
                                 + " not found."))

            new_index = self.component_name_list.index(kwargs["after"])

            new_component = self._create_component_instance(name,
                                                            component_name,
                                                            **kwargs)
            self.component_list.insert(new_index + 1, new_component)

            self.component_name_list.insert(new_index+1, name)

        # Insert component after component with this name
        elif "before" in kwargs:
            if kwargs["before"] not in self.component_name_list:
                raise NameError(("Trying to add a component before a "
                                 + "component named \""
                                 + str(kwargs["before"])
                                 + "\", but a component with that "
                                 + "name was not found."))

            new_index = self.component_name_list.index(kwargs["before"])

            new_component = self._create_component_instance(name,
                                                            component_name,
                                                            **kwargs)
            self.component_list.insert(new_index, new_component)

            self.component_name_list.insert(new_index, name)

        # If after or before keywords absent, place component at the end
        else:
            new_component = self._create_component_instance(name,
                                                            component_name,
                                                            **kwargs)
            self.component_list.append(new_component)
            self.component_name_list.append(name)

        return new_component

    def copy_component(self, name, original_component, **kwargs):
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
        if isinstance(original_component, Component):
            original_component = original_component.name
        """
        If the name starts with COPY, use unique naming as described in the
        McStas manual.
        """
        if name.startswith("COPY("):
            target_name = name.split("(", 1)[1]
            target_name = target_name.split(")", 1)[0]
            instance_name = target_name

            label = 0
            instance_name = target_name + "_" + str(label)
            while instance_name in self.component_name_list:
                instance_name = target_name + "_" + str(label)
                label += 1

        if name in self.component_name_list:
            raise NameError(("Component name \"" + str(name)
                             + "\" used twice, " + self.package_name
                             + " does not allow this."
                             + " Rename or remove one instance of this"
                             + " name."))

        if original_component not in self.component_name_list:
            raise NameError("Component name \"" + str(original_component)
                            + "\" was not found in the " + self.package_name
                            + " instrument. and thus can not be copied.")
        else:
            component_to_copy = self.get_component(original_component)

        # Insert component after component with this name
        if "after" in kwargs:
            if kwargs["after"] not in self.component_name_list:
                raise NameError("Trying to add a component after a component"
                                + " named \"" + str(kwargs["after"])
                                + "\", but a component with that name was"
                                + " not found.")

            new_index = self.component_name_list.index(kwargs["after"])

            new_component = copy.deepcopy(component_to_copy)
            new_component.name = name
            self.component_list.insert(new_index+1, new_component)

            self.component_name_list.insert(new_index+1, name)

        # Insert component after component with this name
        elif "before" in kwargs:
            if kwargs["before"] not in self.component_name_list:
                raise NameError(("Trying to add a component before a "
                                 + "component named \""
                                 + str(kwargs["before"])
                                 + "\", but a component with that "
                                 + "name was not found."))

            new_index = self.component_name_list.index(kwargs["before"])

            new_component = copy.deepcopy(component_to_copy)
            new_component.name = name
            self.component_list.insert(new_index, new_component)

            self.component_name_list.insert(new_index, name)

        # If after or before keywords absent, place component at the end
        else:
            new_component = copy.deepcopy(component_to_copy)
            new_component.name = name
            self.component_list.append(new_component)
            self.component_name_list.append(name)

        # Set the new name of the instance
        new_component.name = name
        # Run set_keyword_input again for keyword arguments to take effect
        new_component.set_keyword_input(**kwargs)

        return new_component

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

        if name in self.component_name_list:
            index = self.component_name_list.index(name)
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

    def set_component_parameter(self, name, input_dict):
        """
        Add parameters and their values as dictionary to component

        This method is the primary way of specifying parameters in a
        component.  Parameters are added to a dictionary specifying
        parameter name and value pairs.

        Parameters
        ----------
        name : str
            Unique name of component to modify

        input_dict : dict
            Set of new parameter name and value pairs to add
        """

        component = self.get_component(name)
        component.set_parameters(input_dict)

    def set_component_AT(self, name, at_list, **kwargs):
        """
        Method for setting position of component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        at_list : List of 3 floats
            Position of component relative to reference component

        keyword arguments:
            RELATIVE : str
                Sets reference component for position
        """

        component = self.get_component(name)
        component.set_AT(at_list, **kwargs)

    def set_component_ROTATED(self, name, rotated_list, **kwargs):
        """
        Method for setting rotiation of component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        rotated_list : List of 3 floats
            Rotation of component relative to reference component

        keyword arguments:
            RELATIVE : str
                Sets reference component for rotation
        """

        component = self.get_component(name)
        component.set_ROTATED(rotated_list, **kwargs)

    def set_component_RELATIVE(self, name, relative):
        """
        Method for setting reference of component position and rotation

        Parameters
        ----------
        name : str
            Unique name of component to modify

        relative : str
            Reference component for position and rotation
        """

        component = self.get_component(name)
        component.set_RELATIVE(relative)

    def set_component_WHEN(self, name, WHEN):
        """
        Method for setting WHEN c expression to named component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        WHEN : str
            Sets WHEN c expression for named McStas component
        """
        component = self.get_component(name)
        component.set_WHEN(WHEN)

    def append_component_EXTEND(self, name, EXTEND):
        """
        Method for adding line of c to EXTEND section of named component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        EXTEND : str
            Line of c code added to EXTEND section of named component
        """

        component = self.get_component(name)
        component.append_EXTEND(EXTEND)

    def set_component_GROUP(self, name, GROUP):
        """
        Method for setting GROUP name of named component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        GROUP : str
            Sets GROUP name for named McStas component
        """

        component = self.get_component(name)
        component.set_GROUP(GROUP)

    def set_component_JUMP(self, name, JUMP):
        """
        Method for setting JUMP expression of named component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        JUMP : str
            Sets JUMP expression for named McStas component
        """

        component = self.get_component(name)
        component.set_JUMP(JUMP)

    def set_component_SPLIT(self, name, SPLIT):
        """
        Method for setting SPLIT value of named component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        SPLIT : int
            Sets SPLIT value for named McStas component
        """

        component = self.get_component(name)
        component.set_SPLIT(SPLIT)

    def set_component_c_code_before(self, name, code):
        """
        Method for setting c code before component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        code : str
            Code to be pasted before component
        """

        component = self.get_component(name)
        component.set_c_code_before(code)

    def set_component_c_code_after(self, name, code):
        """
        Method for setting c code before component

        Parameters
        ----------
        name : str
            Unique name of component to modify

        code : str
            Code to be pasted after component
        """

        component = self.get_component(name)
        component.set_c_code_after(code)

    def set_component_comment(self, name, string):
        """
        Sets a comment displayed before the component in written files

        Parameters
        ----------
        name : str
            Unique name of component to modify

        string : str
            Comment string

        """

        component = self.get_component(name)
        component.set_comment(string)

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

    def print_components(self, **kwargs):
        """
        Method for printing overview of all components in instrument

        Provides overview of component names, what McStas component is
        used for each and their position and rotation in space.

        keyword arguments:
        line_length : int
            Maximum line length in console
        """

        if len(self.component_name_list) == 0:
            print("No components added to instrument object yet.")
            return

        if "line_length" in kwargs:
            line_limit = kwargs["line_length"]
        else:
            line_limit = self.line_limit

        longest_name = len(max(self.component_name_list, key=len))

        # todo Investigate how this could have been done in a better way
        # Find longest field for each type of data printed
        component_type_list = []
        at_xyz_list = []
        at_relative_list = []
        rotated_xyz_list = []
        rotated_relative_list = []
        for component in self.component_list:
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
            for component in self.component_list:
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
            for component in self.component_list:
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
            for component in self.component_list:
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

    def write_full_instrument(self):
        """
        Method for writing full instrument file to disk

        This method writes the instrument described by the instrument
        objects to disk with the name specified in the initialization of
        the object.
        """

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
        fo.write("* Software Center\n")
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
        # Add loop that inserts parameters here
        parameter_list = list(self.parameters)
        for variable in parameter_list[0:-1]:
            variable.write_parameter(fo, ", ")
        if len(parameter_list) > 0:
            parameter_list[-1].write_parameter(fo, " ")
        fo.write(")\n")
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

        # Write initialize
        fo.write("INITIALIZE \n%{\n")
        fo.write(self.initialize_section)
        # Alternatively hide everything in include
        """
        fo.write("%include "generated_includes/"
                  + self.name + "_initialize.c")
        """
        fo.write("%}\n\n")

        # Write trace
        fo.write("TRACE \n")
        for component in self.component_list:
            component.write_component(fo)

        # Write finally
        fo.write("FINALLY \n%{\n")
        fo.write(self.finally_section)
        # Alternatively hide everything in include
        fo.write("%}\n")

        # End instrument file
        fo.write("\nEND\n")

        fo.close()

    def _handle_parameters(self, given_parameters):
        """
        Internal helper function that handles which parameters to pass
        when given a certain set of parameters and values.

        Adds the given parameters to the default parameters, and ensures all
        required parameters are provided. Also checks all given parameters
        match an existing parameter.

        Parameters
        ----------
        given_parameters: dict
            Parameters given by the user for simulation run
        """

        if not isinstance(given_parameters, dict):
            raise RuntimeError("Given parameters must be a dict.")

        # Find required parameters
        required_parameters = []
        default_parameters = {}

        for parameter in self.parameters:
            if parameter.value is None:
                required_parameters.append(parameter.name)
            else:
                default_parameters.update({parameter.name: parameter.value})

        # Check if all given parameters correspond to legal parameters
        for given_par in given_parameters:
            if not isinstance(given_par, str):
                raise NameError("Given parameter must be a string.")
            if (given_par not in required_parameters
                    and given_par not in default_parameters):
                raise NameError("Given parameter: \"" + str(given_par)
                                + "\" did not match any in instrument. "
                                + "Currently available parameters: \n"
                                + "  Required parameters:"
                                + str(required_parameters) + "\n"
                                + "  Default parameters: "
                                + str(list(default_parameters.keys())))

        # Check if required parameters are provided
        if len(given_parameters) == 0:
            if len(required_parameters) > 0:
                # print required parameters and raise error
                print("Required instrument parameters:")
                for name in required_parameters:
                    print("  " + name)
                raise NameError("Required parameters not provided.")
            else:
                # If all parameters have defaults, just run with the defaults.
                return default_parameters
        else:
            for name in required_parameters:
                if name not in given_parameters:
                    raise NameError("The required instrument parameter "
                                    + str(name)
                                    + " was not provided.")
            # Overwrite default parameters with given parameters
            default_parameters.update(given_parameters)
            return default_parameters

    def settings(self, **kwargs):
        """
        Sets parameters and options for McStas run

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

        # Make sure executable path is in kwargs
        if "executable_path" not in kwargs:
            kwargs["executable_path"] = self.executable_path
        else:
            if not os.path.isdir(str(kwargs["executable_path"])):
                raise RuntimeError("The executable_path provided to "
                                   + "run_full_instrument does not point to a"
                                   + "directory: \""
                                   + str(kwargs["executable_path"]) + "\"")

        if "executable" not in kwargs:
            kwargs["executable"] = str(self.executable)
        else:
            # check provided executable can be converted to string
            str(kwargs["executable"])

        if "run_path" not in kwargs:
            # path where mcrun is executed, will load components there
            # if not set, use input_folder given
            kwargs["run_path"] = self.input_path
        else:
            if not os.path.isdir(str(kwargs["run_path"])):
                raise RuntimeError("The run_path provided to "
                                   + "run_full_instrument does not point to a"
                                   + "directory: \""
                                   + str(kwargs["run_path"]) + "\"")

        if "output_path" not in kwargs:
            kwargs["output_path"] = self.output_path

        """
        if "parameters" in kwargs:
            given_parameters = kwargs["parameters"]
        else:
            given_parameters = {}

        kwargs["parameters"] = self._handle_parameters(given_parameters)
        """

        if "force_compile" not in kwargs:
            kwargs["force_compile"] = True

        self.current_run_options = kwargs

    def backengine(self):
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

        if self.current_run_options is None:
            raise RuntimeError("Need to prepare run first!")

        if self.current_run_options["force_compile"]:
            self.write_full_instrument()

        parameters = {}
        for parameter in self.parameters:
            if parameter.value is None:
                raise RuntimeError("Unspecified parameter: '" + parameter.name
                                   + "' set with set_parameters.")

            parameters[parameter.name] = parameter.value

        options = self.current_run_options
        options["parameters"] = parameters

        # Set up the simulation
        simulation = ManagedMcrun(self.name + ".instr", **options)

        # Run the simulation and return data
        simulation.run_simulation(**self.current_run_options)

        # Load data and store in __data
        data = simulation.load_results()
        self._set_data(data)

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
            + "settings and use backengine() to run. See examples in package.")

        if "foldername" in kwargs:
            kwargs["output_path"] = kwargs["foldername"]

        self.settings(**kwargs)
        if "parameters" in kwargs:
            self.set_parameters(kwargs["parameters"])
        self.backengine()
        return self.data

    def show_instrument(self, *args, **kwargs):
        """
        Uses mcdisplay to show the instrument in web browser
        """

        if "parameters" in kwargs:
            given_parameters = kwargs["parameters"]
        else:
            given_parameters = {}

        parameters = self._handle_parameters(given_parameters)

        # add parameters to command
        parameter_string = ""
        for key, val in parameters.items():
            parameter_string = (parameter_string + " "
                                + str(key)  # parameter name
                                + "="
                                + str(val))  # parameter value

        bin_path = os.path.join(self.package_path, "bin", "")
        executable = "mcdisplay-webgl"
        if "format" in kwargs:
            if kwargs["format"] == "webgl":
                executable = "mcdisplay-webgl"
            elif kwargs["format"] == "window":
                executable = "mcdisplay"

        self.write_full_instrument()

        instr_path = os.path.join(self.input_path, self.name + ".instr")
        instr_path = os.path.abspath(instr_path)

        full_command = (bin_path + executable + " "
                        + instr_path
                        + " " + parameter_string)

        process = subprocess.run(full_command, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 universal_newlines=True,
                                 cwd=self.input_path)
        print(process.stderr)
        print(process.stdout)

    def interface(self):
        """
        Shows simulation interface in jupyter notebook interface

        Needs "%matplotlib widget" in notebook to work correctly
        """
        self.write_full_instrument()
        self.widget_interface = SimInterface(self)
        return self.widget_interface.show_interface()

    def get_interface_data(self):
        """
        Returns data from last run performed with the widget interface
        """

        if self.widget_interface is None:
            print("No widget interface initialized, use interface method.")
            return []

        if self.widget_interface.plot_interface.data is None:
            print("No run has been performed with the interface widget yet")
            return []

        return self.widget_interface.plot_interface.data

    def saveH5(self, filename: str, openpmd: bool = True):
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

    executable : str
        Name of executable, mcrun or mxrun

    particle : str
        Name of probe particle, "neutron" or "x-ray"

    package_name : str
        Name of package, "McStas" or "McXtrace"

    input_path : str, default "."
        directory in which simulation is executed, uses components found there

    executable_path : str
        absolute path of mcrun command, or empty if it is in path

    parameters : ParameterContainer instance
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

    show_components(string)
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

    print_components()
        Prints overview of postion / rotation of all components

    write_c_files()
        Writes c files for %include in generated_includes folder

    write_full_instrument()
        Writes full instrument file to current directory

    show_instrument()
        Shows instrument using mcdisplay

    run_full_instrument(**kwargs)
        Writes instrument files and runs simulation.
        Returns list of McStasData

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
        self.executable = "mcrun"
        self.package_name = "McStas"

        super().__init__(name, **kwargs)

    def _read_calibration(self):
        this_dir = os.path.dirname(os.path.abspath(__file__))
        configuration_file_name = os.path.join(this_dir, "..",
                                               "configuration.yaml")
        if not os.path.isfile(configuration_file_name):
            raise NameError("Could not find configuration file!")
        with open(configuration_file_name, 'r') as ymlfile:
            config = yaml.safe_load(ymlfile)

        if type(config) is dict:
            self.executable_path = config["paths"]["mcrun_path"]
            self.package_path = config["paths"]["mcstas_path"]
            self.line_limit = config["other"]["characters_per_line"]
        else:
            # This happens in unit tests that mocks open
            self.executable_path = ""
            self.package_path = ""
            self.line_limit = 180


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

    executable : str
        Name of executable, mcrun or mxrun

    particle : str
        Name of probe particle, "neutron" or "x-ray"

    package_name : str
        Name of package, "McStas" or "McXtrace"

    input_path : str, default "."
        directory in which simulation is executed, uses components found there

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

    component_list : list of Component instances
        list of components in the instrument

    component_name_list : list of strings
        list of names of the components in the instrument

    component_class_lib : dict
        dict of custom Component classes made at run time

    component_reader : ComponentReader
        ComponentReader instance for reading component files

    package_path : str
        Path to mccode package containing component folders

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

    show_components(string)
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

    print_components()
        Prints overview of postion / rotation of all components

    write_c_files()
        Writes c files for %include in generated_includes folder

    write_full_instrument()
        Writes full instrument file to current directory

    show_instrument()
        Shows instrument using mcdisplay

    run_full_instrument(**kwargs)
        Writes instrument files and runs simulation.
        Returns list of McStasData

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
            author : str
                Name of author, written in instrument file

            origin : str
                Affiliation of author, written in instrument file

            executable_path : str
                Absolute path of mxrun or empty if already in path

            input_path : str
                Work directory, will load components from this folder
        """
        self.particle = "x-ray"
        self.executable = "mxrun"
        self.package_name = "McXtrace"

        super().__init__(name, **kwargs)

    def _read_calibration(self):
        this_dir = os.path.dirname(os.path.abspath(__file__))
        configuration_file_name = os.path.join(this_dir, "..",
                                               "configuration.yaml")
        if not os.path.isfile(configuration_file_name):
            raise NameError("Could not find configuration file!")
        with open(configuration_file_name, 'r') as ymlfile:
            config = yaml.safe_load(ymlfile)

        if type(config) is dict:
            self.executable_path = config["paths"]["mxrun_path"]
            self.package_path = config["paths"]["mcxtrace_path"]
            self.line_limit = config["other"]["characters_per_line"]
        else:
            # This happens in unit tests that mocks open
            self.executable_path = ""
            self.package_path = ""
            self.line_limit = 180
