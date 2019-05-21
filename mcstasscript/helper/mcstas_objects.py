from mcstasscript.helper.formatting import bcolors
from mcstasscript.helper.formatting import is_legal_parameter

class parameter_variable:
    """
    Class describing a input parameter in McStas instrument

    McStas input parameters are of default type double, but can be
    cast.  If two positional arguments are given, the first is the
    type, and the second is the parameter name.  With one input, only
    the parameter name is read.  It is also possible to assign a
    default value and a comment through keyword arguments.

    Attributes
    ----------
    type : str
        McStas type of input: Double, Int, String

    name : str
        Name of input parameter

    value : any
        Default value/string of parameter, converted to string

    comment : str
        Comment displayed next to the parameter, could contain units

    Methods
    -------
    write_parameter(fo,stop_character)
        writes the parameter to file fo, uses given stop character
    """

    def __init__(self, *args, **kwargs):
        """Initializing mcstas parameter object

        Parameters
        ----------
        If giving a type:
        Positional argument 1: type: str
            Type of the parameter, double, int or string
        Positional argument 2: name: str
            Name of input parameter

        If not giving type
        Positional argument 1: name : str
            Name of input parameter

        Keyword arguments
            value : any
                sets default value of parameter
            comment : str
                sets comment displayed next to declaration
        """
        if len(args) == 1:
            self.type = ""
            self.name = str(args[0])
        if len(args) == 2:
            self.type = args[0] + " "
            self.name = str(args[1])

        if not is_legal_parameter(self.name):
            raise NameError("The given parameter name: \""
                            + self.name
                            + "\" is not a legal c variable name, "
                            + " and cannot be used in McStas.")

        self.value = ""
        if "value" in kwargs:
            self.value = kwargs["value"]

        self.comment = ""
        if "comment" in kwargs:
            self.comment = "// " + kwargs["comment"]

        # could check for allowed types
        # they are int, double, string, are there more?

    def write_parameter(self, fo, stop_character):
        """Writes input parameter to file"""
        fo.write("%s%s" % (self.type, self.name))
        if self.value is not "":
            if isinstance(self.value, int):
                fo.write(" = %d" % self.value)
            elif isinstance(self.value, float):
                fo.write(" = %G" % self.value)
            else:
                fo.write(" = %s" % str(self.value))
        fo.write(stop_character)
        fo.write(self.comment)
        fo.write("\n")


class declare_variable:
    """
    Class describing a declared variable in McStas instrument

    McStas parameters are declared in declare section with c syntax.
    This class is initialized with type, name.  Using keyword
    arguments, the variable can become an array and have its initial
    value set.

    Attributes
    ----------
    type : str
        McStas type to declare: Double, Int, String

    name : str
        Name of variable

    value : any
        Initial value of variable, converted to string

    comment : str
        Comment displayed next to the declaration, could contain units

    vector : int
        0 if a single value is given, ortherwise contains the length

    Methods
    -------
    write_line(fo)
        Writes a line to text file fo declaring the parameter in c
    """
    def __init__(self, *args, **kwargs):
        """Initializing mcstas parameter object

        Parameters
        ----------
        Positional argument 1: type : str
            Type of the parameter, double, int or string

        Positional argument 2: name : str
            Name of input parameter

        Keyword arguments
            array : int
                length of array to be allocated, 0 if single value

            value : any
                sets initial value of parameter,
                can be a list with length matching array

            comment : str
                sets comment displayed next to declaration
        """
        self.type = args[0]
        self.name = str(args[1])

        if not is_legal_parameter(self.name):
            raise NameError("The given parameter name: \""
                            + self.name
                            + "\" is not a legal c variable name, "
                            + " and cannot be used in McStas.")

        self.value = ""
        if "value" in kwargs:
            self.value = kwargs["value"]

        self.vector = 0
        if "array" in kwargs:
            self.vector = kwargs["array"]

        self.comment = ""
        if "comment" in kwargs:
            self.comment = " // " + kwargs["comment"]

    def write_line(self, fo):
        """Writes line declaring variable to file fo

        Parameters
        ----------
        fo : file object
            File the line will be written to
        """
        if self.value is "" and self.vector == 0:
            fo.write("%s %s;%s" % (self.type, self.name, self.comment))
        if self.value is not "" and self.vector == 0:
            if self.type == "int":
                fo.write("%s %s = %d;%s" % (self.type, self.name,
                                            self.value, self.comment))
            else:
                fo.write("%s %s = %G;%s" % (self.type, self.name,
                                            self.value, self.comment))
        if self.value is "" and self.vector != 0:
            fo.write("%s %s[%d];%s" % (self.type, self.name,
                                       self.vector, self.comment))
        if self.value is not "" and self.vector != 0:
            fo.write("%s %s[%d] = {" % (self.type, self.name, self.vector))
            for i in range(0, len(self.value) - 1):
                fo.write("%G," % self.value[i])
            fo.write("%G};%s" % (self.value[-1], self.comment))


class component:
    """
    A class describing a McStas component to be written to a instrument

    This class is used by the instrument class when setting up
    components as dynamic subclasses to this class.  Most information
    can be given on initialize using keyword arguments, but there are
    methods for setting the attributes describing the component. The
    class contains both methods to write the component to a instrument
    file and methods for printing to the python terminal for checking
    the information. The McStas_Instr class creates subclasses from
    this class that have attributes for all parameters for the given
    component. The component information is read directly from the
    component files in the McStas installation.  This class is frozen
    after __init__ so that no new attributes can be created, which
    allows direct feedback to the user if a parameter name is
    misspelled.

    Attributes
    ----------
    name : str
        Name of the component instance in McStas (must be unique)

    component_name : str
        Name of the component code to use, e.g. Arm, Guide_gravity, ...

    AT_data : list of 3 floats
        Position data of the component

    AT_relative : str
        Name of former component to use as reference for position

    ROTATED_data : list of 3 floats
        Rotation data of the component

    ROTATED_relative : str
        Name of former component to use as reference for position

    WHEN : str
        String with logical c expression x for when component is active

    EXTEND : str
        c code for McStas EXTEND section

    GROUP : str
        Name of group the component should belong to

    JUMP : str
        String describing use of JUMP, need to contain all after "JUMP"

    component_parameters : dict
        Parameters to be used with component in dictionary

    comment : str
        Comment inserted before the component as an explanation

    __isfrozen : bool
        If true no new attributes can be created, when false they can

    Methods
    -------
    set_AT(at_list,**kwargs)
        Sets AT_data, can set AT_relative using keyword

    set_ROTATED(rotated_list,**kwargs)
        Sets ROTATED_data, can set ROTATED_relative using keyword

    set_RELATIVE(relative_name)
        Set both AT_relative and ROTATED_relative to relative_name

    set_parameters(dict_input)
        Adds dictionary entries to parameter dictionary

    set_WHEN(string)
        Sets WHEN string

    set_GROUP(string)
        Sets GROUP name

    set_JUMP(string)
        Sets JUMP string

    append_EXTEND(string)
        Append string to EXTEND string

    set_comment(string)
        Sets comment for component

    write_component(fo)
        Writes component code to instrument file

    print_long()
        Prints basic view of component code (not correct syntax)

    print_short(**kwargs)
        Prints short description, used in print_components

    __setattr__(key, value)
        Overwriting __setattr__ to implement ability to freeze

    _freeze()
        Freeze the class so no new attributes can be defined

    _unfreeze()
        Unfreeze the class so new attributes can be defined again
    """

    __isfrozen = False  # When frozen, no new attributes allowed

    def __init__(self, instance_name, component_name, **kwargs):
        """
        Initializes McStas component with specified name and component

        Parameters
        ----------
        instance_name : str
            name of the instance of the component

        component_name : str
            name of the component type e.g. Arm, Guide_gravity, ...

        keyword arguments:
            AT : list of 3 floats
                Sets AT_data describing position of component

            AT_RELATIVE : str
                sets AT_relative, describing position reference

            ROTATED : list of 3 floats
                Sets ROTATED_data, describing rotation of component

            ROTATED_RELATIVE : str
                Sets ROTATED_relative, sets reference for rotation

            RELATIVE : str
                Sets both AT_relative and ROTATED_relative

            WHEN : str
                Sets WHEN string, should contain logical c expression

            EXTEND : str
                Sets initial EXTEND string, should contain c code

            GROUP : str
                Sets name of group the component should belong to

            JUMP : str
                Sets JUMP str

            comment: str
                Sets comment string
        """

        # Allow addition of attributes in init
        self._unfreeze()

        self.name = instance_name
        self.component_name = component_name

        if "AT" in kwargs:
            self.AT_data = kwargs["AT"]
        else:
            self.AT_data = [0, 0, 0]
        # Could check if AT_RELATIVE is a string
        if "AT_RELATIVE" in kwargs:
            self.AT_relative = "RELATIVE " + kwargs["AT_RELATIVE"]
        else:
            self.AT_relative = "ABSOLUTE"

        if "ROTATED" in kwargs:
            self.ROTATED_data = kwargs["ROTATED"]
        else:
            self.ROTATED_data = [0, 0, 0]
        # Could check if ROTATED_RELATIVE is a string
        if "ROTATED_RELATIVE" in kwargs:
            self.ROTATED_relative = "RELATIVE " + kwargs["ROTATED_RELATIVE"]
        else:
            self.ROTATED_relative = "ABSOLUTE"

        # Could check if RELATIVE is a string
        if "RELATIVE" in kwargs:
            self.AT_relative = "RELATIVE " + kwargs["RELATIVE"]
            self.ROTATED_relative = "RELATIVE " + kwargs["RELATIVE"]

        if "WHEN" in kwargs:
            self.WHEN = "WHEN (" + kwargs["WHEN"] + ")"
        else:
            self.WHEN = ""

        if "EXTEND" in kwargs:
            self.EXTEND = kwargs["EXTEND"] + "\n"
        else:
            self.EXTEND = ""

        if "GROUP" in kwargs:
            self.GROUP = kwargs["GROUP"]
        else:
            self.GROUP = ""

        if "JUMP" in kwargs:
            self.JUMP = kwargs["JUMP"]
        else:
            self.JUMP = ""

        if "comment" in kwargs:
            self.comment = kwargs["comment"]
        else:
            self.comment = ""

        """
        Could store an option for whether this component should be
        printed in instrument file or in a seperate file which would
        then be included.
        """

        # Do not allow addition of attributes after init
        self._freeze()

    def __setattr__(self, key, value):
        if self.__isfrozen and not hasattr(self, key):
            raise AttributeError("No parameter called '"
                                 + key
                                 + "' in component named "
                                 + self.name
                                 + " of component type "
                                 + self.component_name
                                 + ".")
        object.__setattr__(self, key, value)

    def _freeze(self):
        self.__isfrozen = True

    def _unfreeze(self):
        self.__isfrozen = False

    def set_AT(self, at_list, **kwargs):
        """Sets AT data, List of 3 floats"""
        self.AT_data = at_list
        if "RELATIVE" in kwargs:
            relative_name = kwargs["RELATIVE"]
            if relative_name == "ABSOLUTE":
                self.AT_relative = relative_name
            else:
                self.AT_relative = "RELATIVE " + relative_name

    def set_ROTATED(self, rotated_list, **kwargs):
        """Sets ROTATED data, List of 3 floats"""
        self.ROTATED_data = rotated_list
        if "RELATIVE" in kwargs:
            relative_name = kwargs["RELATIVE"]
            if relative_name == "ABSOLUTE":
                self.ROTATED_relative = relative_name
            else:
                self.ROTATED_relative = "RELATIVE " + relative_name

    def set_RELATIVE(self, relative_name):
        """Sets both AT_relative and ROTATED_relative"""
        if relative_name == "ABSOLUTE":
            self.AT_relative = relative_name
            self.ROTATED_relative = relative_name
        else:
            self.AT_relative = "RELATIVE " + relative_name
            self.ROTATED_relative = "RELATIVE " + relative_name

    def set_parameters(self, dict_input):
        """
        Adds parameters and their values from dictionary input

        Relies on attributes added when McStas_Instr creates a
        subclass from the component class where each component
        parameter is added as an attribute.

        """
        for key, val in dict_input.items():
            if not hasattr(self, key):
                raise NameError("No parameter called "
                                + key
                                + " in component named "
                                + self.name
                                + " of component type "
                                + self.component_name
                                + ".")
            else:
                setattr(self, key, val)

    def set_WHEN(self, string):
        """Sets WHEN string, should be a c logical expression"""
        self.WHEN = "WHEN (" + string + ")"

    def set_GROUP(self, string):
        """Sets GROUP name"""
        self.GROUP = string

    def set_JUMP(self, string):
        """Sets JUMP string, should contain all text after JUMP"""
        self.JUMP = string

    def append_EXTEND(self, string):
        """Appends a line of code to EXTEND block of component"""
        self.EXTEND = self.EXTEND + string + "\n"

    def set_comment(self, string):
        """Method that sets a comment to be written to instrument file"""
        self.comment = string

    def write_component(self, fo):
        """
        Method that writes component to file

        Relies on attributes added when McStas_Instr creates a subclass
        based on the component class.

        """
        parameters_per_line = 2
        # Could use character limit on lines instead
        parameters_written = 0  # internal parameter

        # Write comment if present
        if len(self.comment) > 1:
            fo.write("// %s\n" % (str(self.comment)))

        # Write component name and component type
        fo.write("COMPONENT %s = %s(" % (self.name, self.component_name))

        component_parameters = {}
        for key in self.parameter_names:
            val = getattr(self, key)
            if val is None:
                if self.parameter_defaults[key] is None:
                    raise NameError("Required parameter named "
                                    + key
                                    + " in component named "
                                    + self.name
                                    + " not set.")
                else:
                    continue

            component_parameters[key] = val

        number_of_parameters = len(component_parameters)

        if number_of_parameters == 0:
            fo.write(")\n")  # If there are no parameters, close immediately
        else:
            fo.write("\n")  # If there are parameters, start a new line

        for key, val in component_parameters.items():
            if isinstance(val, float):  # CHeck if value is a number
                # Small or large numbers written in scientific format
                fo.write(" %s = %G" % (str(key), val))
            else:
                fo.write(" %s = %s" % (str(key), str(val)))
            parameters_written = parameters_written + 1
            if parameters_written < number_of_parameters:
                fo.write(",")  # Comma between parameters
                if parameters_written % parameters_per_line == 0:
                    fo.write("\n")
            else:
                fo.write(")\n")  # End paranthesis after last parameter

        # Optional WHEN section
        if not self.WHEN == "":
            fo.write("%s\n" % self.WHEN)

        # Write AT and ROTATED section
        fo.write("AT (%s,%s,%s)" % (str(self.AT_data[0]),
                                    str(self.AT_data[1]),
                                    str(self.AT_data[2])))
        fo.write(" %s\n" % self.AT_relative)
        fo.write("ROTATED (%s,%s,%s)" % (str(self.ROTATED_data[0]),
                                         str(self.ROTATED_data[1]),
                                         str(self.ROTATED_data[2])))
        fo.write(" %s\n" % self.ROTATED_relative)

        if not self.GROUP == "":
            fo.write("GROUP %s\n" % self.GROUP)

        # Optional EXTEND section
        if not self.EXTEND == "":
            fo.write("EXTEND %{\n")
            fo.write("%s" % self.EXTEND)
            fo.write("%}\n")

        if not self.JUMP == "":
            fo.write("JUMP %s\n" % self.JUMP)

        # Leave a new line between components for readability
        fo.write("\n")

    def print_long(self):
        """
        Prints contained information to Python terminal

        Includes information on required parameters if they are not yet
        specified. Information on the components are added when the
        class is used as a superclass for classes describing each
        McStas component.
        """
        if len(self.comment) > 1:
            print("// " + self.comment)
        print("COMPONENT", str(self.name),
              "=", str(self.component_name))
        for key in self.parameter_names:
            val = getattr(self, key)
            parameter_name = bcolors.BOLD + key + bcolors.ENDC
            if val is not None:
                unit = ""
                if key in self.parameter_units:
                    unit = "[" + self.parameter_units[key] + "]"
                value = (bcolors.BOLD
                         + bcolors.OKGREEN
                         + str(val)
                         + bcolors.ENDC
                         + bcolors.ENDC)
                print(" ", parameter_name, "=", value, unit)
            else:
                if self.parameter_defaults[key] is None:
                    print("  "
                          + parameter_name
                          + bcolors.FAIL
                          + " : Required parameter not yet specified"
                          + bcolors.ENDC)

        if not self.WHEN == "":
            print(self.WHEN)
        print("AT", self.AT_data, self.AT_relative)
        print("ROTATED", self.ROTATED_data, self.ROTATED_relative)
        if not self.GROUP == "":
            print("GROUP " + self.GROUP)
        if not self.EXTEND == "":
            print("EXTEND %{")
            print(self.EXTEND + "%}")
        if not self.JUMP == "":
            print("JUMP " + self.JUMP)

    def print_short(self, **kwargs):
        """Prints short description of component to list print"""
        if "longest_name" in kwargs:
            number_of_spaces = 3+kwargs["longest_name"]-len(self.name)
            print(str(self.name) + " "*number_of_spaces, end='')
            print(str(self.component_name),
                  "\tAT", self.AT_data, self.AT_relative,
                  "ROTATED", self.ROTATED_data, self.ROTATED_relative)
        else:
            print(str(self.name), "=", str(self.component_name),
                  "\tAT", self.AT_data, self.AT_relative,
                  "ROTATED", self.ROTATED_data, self.ROTATED_relative)

    def show_parameters(self):
        """
        Shows available parameters and their defaults for the component

        Any value specified is not reflected in this view. The
        additional attributes defined when McStas_Instr creates
        subclasses for the individual components are required to run
        this method.
        """

        print(" ___ Help "
              + self.component_name + " "
              + (62-len(self.component_name))*"_")
        print("|"
              + bcolors.BOLD + "optional parameter" + bcolors.ENDC + "|"
              + bcolors.BOLD
              + bcolors.UNDERLINE + "required parameter" + bcolors.ENDC
              + bcolors.ENDC + "|"
              + bcolors.BOLD
              + bcolors.OKBLUE + "default value" + bcolors.ENDC
              + bcolors.ENDC + "|"
              + bcolors.BOLD
              + bcolors.OKGREEN + "user specified value" + bcolors.ENDC
              + bcolors.ENDC + "|")

        for parameter in self.parameter_names:
            unit = ""
            if parameter in self.parameter_units:
                unit = " [" + self.parameter_units[parameter] + "]"
            comment = ""
            if parameter in self.parameter_comments:
                if not self.parameter_comments[parameter] == "":
                    comment = " // " + self.parameter_comments[parameter]

            parameter_name = bcolors.BOLD + parameter + bcolors.ENDC
            value = ""
            if self.parameter_defaults[parameter] is None:
                parameter_name = (bcolors.UNDERLINE
                                  + parameter_name
                                  + bcolors.ENDC)
            else:
                value = (" = "
                         + bcolors.BOLD
                         + bcolors.OKBLUE
                         + str(self.parameter_defaults[parameter])
                         + bcolors.ENDC
                         + bcolors.ENDC)

            if getattr(self, parameter) is not None:
                value = (" = "
                         + bcolors.BOLD
                         + bcolors.OKGREEN
                         + str(getattr(self, parameter))
                         + bcolors.ENDC
                         + bcolors.ENDC)

            print(parameter_name
                  + value
                  + unit
                  + comment)

        print(73*"-")

    def show_parameters_simple(self):
        """
        Shows available parameters and their defaults for the component

        Any value specified is not reflected in this view. The
        additional attributes defined when McStas_Instr creates
        subclasses for the individual components are required to run
        this method.
        """
        print("---- Help " + self.component_name + " -----")
        for parameter in self.parameter_names:
            value = ""
            if self.parameter_defaults[parameter] is not None:
                value = " = " + str(self.parameter_defaults[parameter])
            if getattr(self, parameter) is not None:
                value = " = " + str(getattr(self, parameter))
            
            unit = ""
            if parameter in self.parameter_units:
                unit = " [" + self.parameter_units[parameter] + "]"
            
            comment = ""
            if parameter in self.parameter_comments:
                if self.parameter_comments[parameter] is not "":
                    comment = " // " + self.parameter_comments[parameter]

            print(parameter + value + unit + comment)
                
        print("----------" + "-"*len(self.component_name) + "------")
