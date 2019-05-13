from __future__ import print_function

import os
import datetime

from mcstasscript.helper.mcstas_objects import declare_variable
from mcstasscript.helper.mcstas_objects import parameter_variable
from mcstasscript.helper.mcstas_objects import component
from mcstasscript.data.data import McStasData
from mcstasscript.helper.component_reader import ComponentReader
from mcstasscript.helper.managed_mcrun import ManagedMcrun

class McStas_instr:
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

    author : str
        name of user of McStasScript, written to the file

    origin : str
        origin of instrument file (affiliation)

    mcrun_path : str
        absolute path of mcrun command, or empty if it is in path

    parameter_list : list of parameter_variable instances
        contains all input parameters to be written to file

    declare_list : list of declare_variable instances
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

    Methods
    -------
    add_parameter(*args,**kwargs)
        Adds input parameter to the define section

    add_declare_var()
        Adds declared variable ot the declare section

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

    add_component(instance_name,component_name,**kwargs)
        Add a component to the instrument file

    get_component(instance_name)
        Returns component instance with name instance_name

    get_last_component()
        Returns component instance of last component

    set_component_parameter(instance_name,dict)
        Adds parameters as dict to component with instance_name

    set_component_AT(instance_name,AT_data,**kwargs)
        Sets position of component named instance_name

    set_component_ROTATED(instance_name,ROTATED_data,**kwargs)
        Sets rotation of component named instance_name

    set_component_RELATIVE(instane_name,string)
        Sets position and rotation reference for named component

    set_component_WHEN(instance_name,string)
        Sets WHEN condition of named component, is logical c expression

    set_component_GROUP(instance_name,string)
        Sets GROUP name of component named instance_name

    append_component_EXTEND(instance_name,string)
        Appends a line to EXTEND section of named component

    set_component_JUMP(instance_name,string)
        Sets JUMP code for named component

    set_component_comment(instance_name,string)
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

    run_full_instrument(**kwargs)
        Writes instrument files and runs simulation.
        Returns list of McStasData
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

            mcrun_path : str
                Absolute path of mcrun or empty if already in path
        """

        self.name = name

        if "author" in kwargs:
            self.author = kwargs["author"]
        else:
            self.author = "Python McStas Instrument Generator"

        if "origin" in kwargs:
            self.origin = kwargs["origin"]
        else:
            self.origin = "ESS DMSC"

        if "mcrun_path" in kwargs:
            self.mcrun_path = kwargs["mcrun_path"]
        else:
            self.mcrun_path = ""

        if "mcstas_path" in kwargs:
            self.mcstas_path = kwargs["mcstas_path"]
        else:
            self.mcstas_path = ""
            raise NameError("At this stage of development "
                            + "McStasScript need the absolute path "
                            + "for the McStas installation as keyword "
                            + "named mcstas_path")

        self.parameter_list = []
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

        # Read info on active McStas components
        self.component_reader = ComponentReader(self.mcstas_path)
        self.component_class_lib = {}

    def add_parameter(self, *args, **kwargs):
        """
        Method for adding input parameter to instrument

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
        # parameter_variable class documented independently
        self.parameter_list.append(parameter_variable(*args, **kwargs))

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
        # declare_variable class documented independently
        self.declare_list.append(declare_variable(*args, **kwargs))

    def append_initialize(self, string):
        """
        Method for appending code to the intialize section

        The intialize section consists of c code and will be compiled,
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
        Method for appending code to the intialize section, no new line

        The intialize section consists of c code and will be compiled,
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
        component categories.  The first input

        """
        if len(args) == 0:
            print("Here are the availalbe component categories:")
            self.component_reader.show_categories()
            print("Call show_components(category_name) to display")

        else:
            category = args[0]
            print("Here are all components in the "
                  + category
                  + " category.")
            self.component_reader.show_components_in_category(category)

    def component_help(self, name):
        """
        Method for showing parameters for a component before adding it
        to the instrument

        """

        dummy_instance = self._create_component_instance("dummy", name)
        dummy_instance.show_parameters()

    def _create_component_instance(self, *args, **kwargs):
        """
        Dynamically creates a class for the requested component type

        Created classses kept in dictionary, if the same component type
        is requested again, the class in the dictionary is used.  The
        method returns an instance of the created class that was
        initialized with the paramters passed to this function.
        """

        if len(args) < 2:
            raise NameError("Attempting to create component without name")

        component_name = args[1]

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

            self.component_class_lib[component_name] = type(component_name,
                                                            (component,),
                                                            input_dict)

        return self.component_class_lib[component_name](*args, **kwargs)

    def add_component(self, *args, **kwargs):
        """
        Method for adding a new component instance to the instrument

        Creates a new component instance in the instrument.  This
        requires a unique instance name of the component to be used for
        future reference and the name of the McStas component to be
        used.  The component is placed at the end of the instrument file
        unless otherwise specified with the after and before keywords.
        The component may be initialized using other keyword arguments,
        but all attributes can be set with approrpiate methods.

        Parameters
        ----------
        First positional argument : str
            Unique name of component instance

        Second positional argument : str
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

        if args[0] in self.component_name_list:
            raise NameError(("Component name \"" + str(args[0])
                             + "\" used twice, McStas does not allow this."
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

            new_component = self._create_component_instance(*args, **kwargs)
            self.component_list.insert(new_index + 1, new_component)

            self.component_name_list.insert(new_index+1, args[0])

        # Insert component after component with this name
        elif "before" in kwargs:
            if kwargs["before"] not in self.component_name_list:
                raise NameError(("Trying to add a component before a "
                                 + "component named \""
                                 + str(kwargs["before"])
                                 + "\", but a component with that "
                                 + "name was not found."))

            new_index = self.component_name_list.index(kwargs["before"])

            new_component = self._create_component_instance(*args, **kwargs)
            self.component_list.insert(new_index, new_component)

            self.component_name_list.insert(new_index, args[0])

        # If after or before keywords absent, place component at the end
        else:
            new_component = self._create_component_instance(*args, **kwargs)
            self.component_list.append(new_component)
            self.component_name_list.append(args[0])

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
            Unique name of component whos instance should be returned
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

    def print_components(self):
        """
        Method for printing overview of all components in instrument

        Provides overview of component names, what McStas component is
        used for each and their position and rotation in space.
        """

        longest_name = len(max(self.component_name_list, key=len))

        # Investigate how this could have been done in a better way
        # Find longest field for each type of data printed
        component_type_list = []
        at_x_list = []
        at_y_list = []
        at_z_list = []
        at_relative_list = []
        rotated_x_list = []
        rotated_y_list = []
        rotated_z_list = []
        rotated_relative_list = []
        for component in self.component_list:
            component_type_list.append(component.component_name)
            at_x_list.append(str(component.AT_data[0]))
            at_y_list.append(str(component.AT_data[1]))
            at_z_list.append(str(component.AT_data[2]))
            at_relative_list.append(component.AT_relative)
            rotated_x_list.append(str(component.ROTATED_data[0]))
            rotated_y_list.append(str(component.ROTATED_data[1]))
            rotated_z_list.append(str(component.ROTATED_data[2]))
            rotated_relative_list.append(component.ROTATED_relative)

        longest_component_name = len(max(component_type_list, key=len))
        longest_at_x_name = len(max(at_x_list, key=len))
        longest_at_y_name = len(max(at_y_list, key=len))
        longest_at_z_name = len(max(at_z_list, key=len))
        longest_at_relative_name = len(max(at_relative_list, key=len))
        longest_rotated_x_name = len(max(rotated_x_list, key=len))
        longest_rotated_y_name = len(max(rotated_y_list, key=len))
        longest_rotated_z_name = len(max(rotated_z_list, key=len))
        longest_rotated_relative_name = len(max(rotated_relative_list,
                                                key=len))

        # Have longest field for each type, use ljust to align all columns
        for component in self.component_list:
            print(str(component.name).ljust(longest_name+2), end=' ')

            comp_name = component.component_name
            comp_name_print = str(comp_name).ljust(longest_component_name + 2)
            print(comp_name_print, end=' ')

            comp_at_data = str(component.AT_data)
            longest_at_xyz_sum = (longest_at_x_name
                                  + longest_at_y_name
                                  + longest_at_z_name)
            print("AT ",
                  comp_at_data.ljust(longest_at_xyz_sum + 11),
                  end='')

            comp_at_relative = component.AT_relative
            print(comp_at_relative.ljust(longest_at_relative_name + 2),
                  end=' ')

            comp_rotated_data = str(component.ROTATED_data)
            longest_rotated_xyz_sum = (longest_rotated_x_name
                                       + longest_rotated_y_name
                                       + longest_rotated_z_name)
            print("ROTATED ",
                  comp_rotated_data.ljust(longest_rotated_xyz_sum + 11),
                  end='')
            print(component.ROTATED_relative)
            # print("")

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
        path = path + "/generated_includes"
        if not os.path.isdir(path):
            try:
                os.mkdir(path)
            except OSError:
                print("Creation of the directory %s failed" % path)

        fo = open("./generated_includes/" + self.name + "_declare.c", "w")
        fo.write("// declare section for %s \n" % self.name)
        fo.close()
        fo = open("./generated_includes/" + self.name + "_declare.c", "a")
        for dec_line in self.declare_list:
            dec_line.write_line(fo)
            fo.write("\n")
        fo.close()

        fo = open("./generated_includes/" + self.name + "_initialize.c", "w")
        fo.write(self.initialize_section)
        fo.close()

        fo = open("./generated_includes/" + self.name + "_trace.c", "w")
        fo.write(self.trace_section)
        fo.close()

        fo = open("./generated_includes/" + self.name
                  + "_component_trace.c", "w")
        for component in self.component_list:
            component.write_component(fo)
        fo.close()

    def write_full_instrument(self):
        """
        Method for writing full instrument file to disk

        This method writes the instrument described by the instrument
        objects to disk with the name specified in the initialization of
        the object.
        """

        # Create file identifier
        fo = open(self.name + ".instr", "w")

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
        for variable in self.parameter_list[0:-1]:
            variable.write_parameter(fo, ",")
        if len(self.parameter_list) > 0:
            self.parameter_list[-1].write_parameter(fo, " ")
        fo.write(")\n")
        fo.write("\n")

        # Write declare
        fo.write("DECLARE \n%{\n")
        for dec_line in self.declare_list:
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

    def run_full_instrument(self, *args, **kwargs):
        """
        Runs McStas instrument described by this class, returns list of
        McStasData

        This method will write the instrument to disk and then run it
        using the mcrun command of the system. Options are set using
        keyword arguments.  Some options are mandatory, for example
        foldername, which can not already exist, if it does data will
        be read from this folder.  If the mcrun command is not in the
        path of the system, the absolute path can be given with the
        mcrun_path keyword argument.  This path could also already have
        been set at initialization of the instrument object.

        Parameters
        ----------
        Keyword arguments
            foldername : str
                Sets data_folder_name
            ncount : int
                Sets ncount
            mpi : int
                Sets thread count
            parameters : dict
                Sets parameters
            custom_flags : str
                Sets custom_flags passed to mcrun
            mcrun_path : str
                Path to mcrun command, "" if already in path
        """
        # Write the instrument file
        self.write_full_instrument()

        # Make sure mcrun path is in kwargs
        if "mcrun_path" not in kwargs:
            kwargs["mcrun_path"] = self.mcrun_path

        # Set up the simulation
        simulation = ManagedMcrun(self.name + ".instr", **kwargs)

        # Run the simulation and return data
        return simulation.run_simulation()
    

