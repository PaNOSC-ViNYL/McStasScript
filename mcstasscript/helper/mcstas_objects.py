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
        if self.value != "":
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
        0 if a single value is given, otherwise contains the length

    Methods
    -------
    write_line(fo)
        Writes a line to text file fo declaring the parameter in c
    """
    def __init__(self, *args, **kwargs):
        """
        Initializing mcstas parameter object

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


        par_name = self.name
        if "*" in par_name[0]:
            # Remove any number of prefixed *, indicating variable is a pointer
            par_name = par_name.split("*")[-1]
        elif "&" in par_name[0]:
            # Remove the first & indicating the variable is an address
            par_name = par_name[1:]
            
        if not is_legal_parameter(par_name):
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
        """
        Writes line declaring variable to file fo

        Parameters
        ----------
        fo : file object
            File the line will be written to
        """
        if self.value == "" and self.vector == 0:
            fo.write("%s %s;%s" % (self.type, self.name, self.comment))
        if self.value != "" and self.vector == 0:
            if self.type == "int":
                fo.write("%s %s = %d;%s" % (self.type, self.name,
                                            self.value, self.comment))
            else:
                try:
                    fo.write("%s %s = %G;%s" % (self.type, self.name,
                                                self.value, self.comment))
                except:
                    fo.write("%s %s = %s;%s" % (self.type, self.name,
                                                self.value, self.comment))
        if self.value == "" and self.vector != 0:
            fo.write("%s %s[%d];%s" % (self.type, self.name,
                                       self.vector, self.comment))
        if self.value != "" and self.vector != 0:
            if isinstance(self.value, str):
                # value is a string
                string = self.value
                #string = string.replace('"',"\\\"")
                fo.write("%s %s[%d] = %s;" % (self.type, self.name, self.vector, string))
            else:
                # list of values
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
    set_AT(at_list, RELATIVE)
        Sets AT_data, can set AT_relative using keyword

    set_AT_RELATIVE(relative)
        Can set RELATIVE for position

    set_ROTATED(rotated_list, RELATIVE)
        Sets ROTATED_data, can set ROTATED_relative using keyword

    set_ROTATED_RELATIVE(relative)
        Can set RELATIVE for rotation

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
                
            SPLIT : int
                Sets SPLIT value

            comment: str
                Sets comment string
        """

        # Allow addition of attributes in init
        self._unfreeze()

        self.name = instance_name
        self.component_name = component_name

        # initialize McStas information
        self.AT_data = [0, 0, 0]
        self.AT_relative = "ABSOLUTE"
        self.ROTATED_specified = False
        self.ROTATED_data = [0, 0, 0]
        self.ROTATED_relative = "ABSOLUTE"
        self.WHEN = ""
        self.EXTEND = ""
        self.GROUP = ""
        self.JUMP = ""
        self.SPLIT = 0
        self.comment = ""
        self.c_code_before = "" 
        self.c_code_after = ""

        # If any keywords are set in kwargs, update these
        self.set_keyword_input(**kwargs)

        """
        Could store an option for whether this component should be
        printed in instrument file or in a seperate file which would
        then be included.
        """

        # Do not allow addition of attributes after init
        self._freeze()
    
    def set_keyword_input(self, **kwargs):
        # Allow addition of attributes in init
        self._unfreeze()

        if "AT" in kwargs:
            self.set_AT(kwargs["AT"])

        if "AT_RELATIVE" in kwargs:
            self.set_AT_RELATIVE(kwargs["AT_RELATIVE"])

        self.ROTATED_specified = False
        if "ROTATED" in kwargs:
            self.set_ROTATED(kwargs["ROTATED"])

        if "ROTATED_RELATIVE" in kwargs:
            self.set_ROTATED_RELATIVE(kwargs["ROTATED_RELATIVE"])

        if "RELATIVE" in kwargs:
            self.set_RELATIVE(kwargs["RELATIVE"])

        if "WHEN" in kwargs:
            self.WHEN = "WHEN (" + kwargs["WHEN"] + ")"

        if "EXTEND" in kwargs:
            self.EXTEND = kwargs["EXTEND"] + "\n"

        if "GROUP" in kwargs:
            self.GROUP = kwargs["GROUP"]

        if "JUMP" in kwargs:
            self.JUMP = kwargs["JUMP"]
            
        if "SPLIT" in kwargs:
            self.SPLIT = kwargs["SPLIT"]

        if "comment" in kwargs:
            self.comment = kwargs["comment"]
            
        if "c_code_before" in kwargs:
            self.c_code_before = kwargs["c_code_before"]
        
        if "c_code_after" in kwargs:
            self.c_code_after = kwargs["c_code_after"]
        

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

    def set_AT(self, at_list, RELATIVE=None):
        """Sets AT data, List of 3 floats"""
        self.AT_data = at_list
        if RELATIVE is not None:
            self.set_AT_RELATIVE(RELATIVE)

    def set_AT_RELATIVE(self, relative):
        """Sets AT RELATIVE with string or component instance"""

        # Extract name if component instance is given
        if isinstance(relative, component):
            relative = relative.name
        elif not isinstance(relative, str):
            raise ValueError("Relative must be either string or "
                             + "component object.")

        # Set AT relative
        if relative == "ABSOLUTE":
            self.AT_relative = "ABSOLUTE"
        else:
            self.AT_relative = "RELATIVE " + relative

    def set_ROTATED(self, rotated_list, RELATIVE=None):
        """Sets ROTATED data, List of 3 floats"""
        self.ROTATED_data = rotated_list
        self.ROTATED_specified = True
        if RELATIVE is not None:
            self.set_ROTATED_RELATIVE(RELATIVE)

    def set_ROTATED_RELATIVE(self, relative):
        """Sets ROTATED RELATIVE with string or component instance"""

        self.ROTATED_specified = True
        # Extract name if a component instance is given
        if isinstance(relative, component):
            relative = relative.name
        elif not isinstance(relative, str):
            raise ValueError("Relative must be either string or "
                             + "component object.")

        # Set ROTATED relative
        if relative == "ABSOLUTE":
            self.ROTATED_relative = "ABSOLUTE"
        else:
            self.ROTATED_relative = "RELATIVE " + relative

    def set_RELATIVE(self, relative):
        """Sets both AT_relative and ROTATED_relative"""
        # Extract name if a component instance is given
        if isinstance(relative, component):
            relative = relative.name
        elif not isinstance(relative, str):
            raise ValueError("Relative must be either string or "
                             + "component object.")

        if relative == "ABSOLUTE":
            self.AT_relative = "ABSOLUTE"
            self.ROTATED_relative = "ABSOLUTE"
        else:
            self.AT_relative = "RELATIVE " + relative
            self.ROTATED_relative = "RELATIVE " + relative

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
        
    def set_SPLIT(self, value):
        """Sets SPLIT value, should contain all text after JUMP"""
        self.SPLIT = value

    def append_EXTEND(self, string):
        """Appends a line of code to EXTEND block of component"""
        self.EXTEND = self.EXTEND + string + "\n"

    def set_comment(self, string):
        """Method that sets a comment to be written to instrument file"""
        self.comment = string
        
    def set_c_code_before(self, string):
        """Method that sets c code to be written before the component"""
        self.c_code_before = string
        
    def set_c_code_after(self, string):
        """Method that sets c code to be written after the component"""
        self.c_code_after = string

    def write_component(self, fo):
        """
        Method that writes component to file

        Relies on attributes added when McStas_Instr creates a subclass
        based on the component class.

        """
        parameters_per_line = 2
        # Could use character limit on lines instead
        parameters_written = 0  # internal parameter


        if len(self.c_code_before) > 0:
            explanation = "From component named " + self.name
            fo.write("%s // %s\n" % (str(self.c_code_before), explanation))
            fo.write("\n")

        # Write comment if present
        if len(self.comment) > 1:
            fo.write("// %s\n" % (str(self.comment)))

        if self.SPLIT != 0:
            fo.write("SPLIT " + str(self.SPLIT) + " ") 

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
        
        if self.ROTATED_specified:
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
            
        if len(self.c_code_after) > 0:
            fo.write("\n")
            explanation = "From component named " + self.name
            fo.write("%s // %s\n" % (str(self.c_code_after), explanation))

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
        if len(self.c_code_before) > 1:
            print(self.c_code_before)
        if len(self.comment) > 1:
            print("// " + self.comment)
        if self.SPLIT != 0:
            print("SPLIT " + str(self.SPLIT) + " ", end="")
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
        if self.ROTATED_specified:
            print("ROTATED", self.ROTATED_data, self.ROTATED_relative)
        if not self.GROUP == "":
            print("GROUP " + self.GROUP)
        if not self.EXTEND == "":
            print("EXTEND %{")
            print(self.EXTEND + "%}")
        if not self.JUMP == "":
            print("JUMP " + self.JUMP)
        if len(self.c_code_after) > 1:
            print(self.c_code_after)

    def print_short(self, **kwargs):
        """Prints short description of component to list print"""
        if self.ROTATED_specified:
            print_rotate_rel = self.ROTATED_relative
        else:
            print_rotate_rel = self.AT_relative
        
        if "longest_name" in kwargs:
            number_of_spaces = 3+kwargs["longest_name"]-len(self.name)
            print(str(self.name) + " "*number_of_spaces, end='')
            print(str(self.component_name),
                  "\tAT", self.AT_data, self.AT_relative,
                  "ROTATED", self.ROTATED_data, print_rotate_rel)
        else:
            print(str(self.name), "=", str(self.component_name),
                  "\tAT", self.AT_data, self.AT_relative,
                  "ROTATED", self.ROTATED_data, print_rotate_rel)

    def show_parameters(self, **kwargs):
        """
        Shows available parameters and their defaults for the component

        Any value specified is not reflected in this view. The
        additional attributes defined when McStas_Instr creates
        subclasses for the individual components are required to run
        this method.
        """

        if "line_length" in kwargs:
            line_limit = kwargs["line_length"]
        else:
            line_limit = self.line_limit

        # Minimum reasonable line length
        if line_limit < 74:
            line_limit = 74

        print(" ___ Help "
              + self.component_name + " "
              + (line_limit - 11 - len(self.component_name))*"_")
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
            characters_before_comment = 4
            unit = ""
            if parameter in self.parameter_units:
                unit = " [" + self.parameter_units[parameter] + "]"
                characters_before_comment += len(unit)
            comment = ""
            if parameter in self.parameter_comments:
                if not self.parameter_comments[parameter] == "":
                    comment = " // " + self.parameter_comments[parameter]

            parameter_name = bcolors.BOLD + parameter + bcolors.ENDC
            characters_before_comment += len(parameter)

            value = ""
            characters_from_value = 0
            if self.parameter_defaults[parameter] is None:
                parameter_name = (bcolors.UNDERLINE
                                  + parameter_name
                                  + bcolors.ENDC)
            else:
                this_default = str(self.parameter_defaults[parameter])
                value = (" = "
                         + bcolors.BOLD
                         + bcolors.OKBLUE
                         + this_default
                         + bcolors.ENDC
                         + bcolors.ENDC)
                characters_from_value = 3 + len(this_default)

            if getattr(self, parameter) is not None:
                this_set_value = str(getattr(self, parameter))
                value = (" = "
                         + bcolors.BOLD
                         + bcolors.OKGREEN
                         + this_set_value
                         + bcolors.ENDC
                         + bcolors.ENDC)
                characters_from_value = 3 + len(this_set_value)
            characters_before_comment += characters_from_value

            print(parameter_name + value + unit, end="")

            if characters_before_comment + len(comment) < line_limit:
                print(comment)
            else:
                length_for_comment = line_limit - characters_before_comment
                # Split comment into several lines
                original_comment = comment
                words = comment.split(" ")
                words_left = len(words)
                last_index = 0
                current_index = 0
                comment = ""
                iterations = 0
                max_iterations = 50
                while(words_left > 0):
                    iterations += 1
                    if iterations > max_iterations:
                        #  Something went long, print on one line
                        break

                    line_left = length_for_comment

                    while(line_left > 0):
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
                        comment += "\n" + " "*characters_before_comment
                        last_index = current_index

                if not iterations == max_iterations + 1:
                    print(comment)
                else:
                    print(str(original_comment))

        print(line_limit*"-")

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
                if self.parameter_comments[parameter] != "":
                    comment = " // " + self.parameter_comments[parameter]

            print(parameter + value + unit + comment)

        print("----------" + "-"*len(self.component_name) + "------")
