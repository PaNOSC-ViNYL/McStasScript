from mcstasscript.helper.formatting import bcolors
from mcstasscript.helper.formatting import is_legal_parameter
from mcstasscript.helper.exceptions import McStasError
from mcstasscript.helper.name_inspector import find_python_variable_name
from mcstasscript.helper.search_statement import SearchStatement, SearchStatementList

from libpyvinyl.Parameters.Parameter import Parameter


def provide_parameter(*args, **kwargs):
    """Makes a libpyvinyl parameter object

    Examples
    --------

    Creates a parameter with name wavelength and associated comment
    A = provide_parameter("wavelength", comment="wavelength in [AA]")

    Creates a parameter with name A3 and default value
    A = provide_parameter("A3", value=30, comment="A3 angle in [deg]")

    Creates a parameter with type string and name sample_name
    A = provide_parameter("string", "sample_name")

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
        value : float, int or str
            sets default value of parameter
        unit : str
            string that describes the unit
        comment : str
            sets comment displayed next to declaration
        options : list or value
            list or value of allowed values for this parameter
    """
    if len(args) == 0:
        # Check all required keyword arguments present
        if "name" not in kwargs:
            try:
                name = find_python_variable_name(error_text="", n_levels=3)
                kwargs["name"] = name
            except:
                raise RuntimeError("Need to provide name, either as first argument"
                                   + ", keyword argument or python variable.")

        provided_name = kwargs["name"]

        provided_type = ""
        if "type" in kwargs:
            provided_type = kwargs["type"]

    elif len(args) == 1:
        if "name" in kwargs:
            raise RuntimeError("Only specify name with argument or keyword argument")
        provided_name = args[0]

        # Assume default type if not given
        provided_type = ""
        if "type" in kwargs:
            provided_type = kwargs["type"]

    elif len(args) == 2:
        if "type" in kwargs:
            raise RuntimeError("Only specify type with argument or keyword argument")
        provided_type = args[0]

        if "name" in kwargs:
            raise RuntimeError("Only specify name with argument or keyword argument")
        provided_name = args[1]

    else:
        raise RuntimeError("Too many arguments given to parameter")

    if not is_legal_parameter(provided_name):
        raise NameError("The given parameter name: \""
                        + provided_name
                        + "\" is not a legal c variable name, "
                        + " and cannot be used in McStas.")

    allowed_types = {"", "double", "int", "string"}
    if provided_type not in allowed_types:
        raise RuntimeError("Tried to create parameter of type \""
                           + str(provided_type)
                           + "\" which is not among the allowed types "
                           + str(allowed_types) + ".")

    comment = ""
    if "comment" in kwargs:
        if not isinstance(comment, str):
            raise RuntimeError("Tried to create a parameter with a "
                               + "comment that was not a string.")
        comment = kwargs["comment"]

    unit = ""
    if "unit" in kwargs:
        if not isinstance(unit, str):
            raise RuntimeError("Unit has to be a string")
        unit = kwargs["unit"]

    parameter = Parameter(name=provided_name, unit=unit, comment=comment)
    parameter.type = provided_type

    if "options" in kwargs:
        parameter.add_option(kwargs["options"], True)

    if "value" in kwargs:
        parameter.value = kwargs["value"]

    return parameter


def write_parameter(fo, parameter, stop_character):
    """
    Writes a parameter object to McStas define section

    Parameters
    ----------

    fo : file object
        Open file object to write parameter string to

    parameter : Parameter
        Parameter object to be written

    stop_character : str
        Character inserted after parameter, usually comma and space
    """
    if not isinstance(stop_character, str):
        raise RuntimeError("stop_character in write_parameter should be "
                           + "a string.")

    if parameter.type is None:
        # This can happen if parameter given by libpyvinyl directly, infer type
        if parameter.value is None:
            raise RuntimeError("Need to set parameter '" + parameter.name
                               + "' before writing instrument.")

        if isinstance(parameter.value, (float, int)):
            parameter.type = "double"
        elif isinstance(parameter.value, str):
            parameter.type = "string"
        else:
            raise RuntimeError("Parameter '" + parameter.name + "' has value "
                               + "of type not recognized by McStasScript.")

    if not parameter.type == "":
        fo.write("%s %s" % (parameter.type, parameter.name))
    else:
        fo.write(parameter.name)

    if parameter.value is not None:
        if isinstance(parameter.value, int):
            fo.write(" = %d" % parameter.value)
        elif isinstance(parameter.value, float):
            fo.write(" = %G" % parameter.value)
        else:
            fo.write(" = %s" % str(parameter.value))
    fo.write(stop_character)

    if parameter.comment is None or parameter.comment == "":
        c_comment = ""
    else:
        c_comment = "// " + parameter.comment

    fo.write(c_comment)
    fo.write("\n")


class DeclareVariable:
    """
    Class describing a declared variable in McStas instrument

    McStas parameters are declared in declare section with c syntax.
    This class is initialized with type, name.  Using keyword
    arguments, the variable can become an array and have its initial
    value set.
    Can also be used as a user variable in uservars (McStas 3.0)

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
    def __init__(self, type, name=None, **kwargs):
        """
        Initializing mcstas declare variable or user variable object

        Examples
        --------

        Creates a variable with name A3 and default value
        A = DeclareVariable("double", "A3", value=30)

        Creates a variable with type integer and name A
        A = DeclareVariable("int")

        Creates a variable with type integer and name sample_number
        A = DeclareVariable("int", "sample_number")

        Creates an array variable called m_values
        A = DeclareVariable("double", "m_values", array=3,
                             value=[2, 2.5, 2])

        Parameters
        ----------
        type : str
            Type of the parameter, double, int or string

        name : str
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

        self.type = type
        if not isinstance(self.type, str):
            raise RuntimeError("Given type of DeclareVariable should be a "
                               + "string.")

        if name is None:
            error_text = ("When using automatic assignment of name, the call"
                          " need to assign it to a variable name")
            name = find_python_variable_name(error_text=error_text, n_levels=3)

        self.name = str(name)

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
                except TypeError:
                    # Value could not be converted to float, write as string
                    fo.write("%s %s = %s;%s" % (self.type, self.name,
                                                self.value, self.comment))
        if self.value == "" and self.vector != 0:
            fo.write("%s %s[%d];%s" % (self.type, self.name,
                                       self.vector, self.comment))
        if self.value != "" and self.vector != 0:
            if isinstance(self.value, str):
                # value is a string
                string = self.value
                fo.write("%s %s[%d] = %s;" % (self.type, self.name,
                                              self.vector, string))
            else:
                # list of values
                fo.write("%s %s[%d] = {" % (self.type, self.name, self.vector))
                for i in range(0, len(self.value) - 1):
                    fo.write("%G," % self.value[i])
                fo.write("%G};%s" % (self.value[-1], self.comment))

    def __repr__(self):
        string = "Declare variable: '"
        string += str(self.name)
        string += "' of type "
        string += str(self.type)

        if self.value != "":
            string += " with value: "
            string += str(self.value)

        if self.vector != 0:
            string += ". Array with length "
            string += str(self.vector)

        return string


class Component:
    """
    A class describing a McStas component to be written to an instrument

    This class is used by the instrument class when setting up
    components as dynamic subclasses to this class.  Most information
    can be given on initialize using keyword arguments, but there are
    methods for setting the attributes describing the component. The
    class contains both methods to write the component to an instrument
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

    AT_data : list of 3 floats, default [0, 0, 0]
        Position data of the component

    AT_relative : str, default "ABSOLUTE"
        Name of former component to use as reference for position

    ROTATED_data : list of 3 floats, default [0, 0, 0]
        Rotation data of the component

    ROTATED_relative : str, default "ABSOLUTE"
        Name of former component to use as reference for position

    WHEN : str, default ""
        String with logical c expression x for when component is active

    EXTEND : str, default ""
        c code for McStas EXTEND section

    GROUP : str, default ""
        Name of group the component should belong to

    JUMP : str, default ""
        String describing use of JUMP, need to contain all after "JUMP"

    SPLIT : int, default 0 (disabled)
        Integer setting SPLIT, splitting the neutron before this component

    c_code_before : str, default ""
        C code inserted before the component

    c_code_after : str, default ""
        C code inserted after the component

    component_parameters : dict
        Parameters to be used with component in dictionary

    comment : str, default ""
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

    set_SPLIT(value)
        Sets SPLIT value, a value of 0 disables SPLIT

    set_GROUP(string)
        Sets GROUP name

    set_JUMP(string)
        Sets JUMP string

    append_EXTEND(string)
        Append string to EXTEND string

    set_c_code_before(string)
        Sets c code to be inserted before component

    set_c_code_before(string)
        Sets c code to be inserted after component

    set_comment(string)
        Sets comment for component

    write_component(fo)
        Writes component code to instrument file

    show_parameters()
        Prints current component state with all parameters

    print_long()
        Prints basic view of component code (not correct syntax)

    print_long_deprecated()
        Prints basic view of component code (obsolete)

    print_short(**kwargs)
        Prints short description, used in print_components

    set_keyword_input(**kwargs)
        Handle keyword arguments during initialize

    __setattr__(key, value)
        Overwriting __setattr__ to implement ability to freeze

    _freeze()
        Freeze the class so no new attributes can be defined

    _unfreeze()
        Unfreeze the class so new attributes can be defined again
    """

    __isfrozen = False  # When frozen, no new attributes allowed

    def __init__(self, instance_name, component_name, AT=None,
                 AT_RELATIVE=None, ROTATED=None, ROTATED_RELATIVE=None,
                 RELATIVE=None, WHEN=None, EXTEND=None, GROUP=None,
                 JUMP=None, SPLIT=None, comment=None, c_code_before=None,
                 c_code_after=None, save_parameters=False):
        """
        Initializes McStas component with specified name and component

        Parameters
        ----------
        instance_name : str
            name of the instance of the component

        component_name : str
            name of the component type e.g. Arm, Guide_gravity, ...

        keyword arguments:
            AT : list of 3 floats, default [0, 0, 0]
                Sets AT_data describing position of component

            AT_RELATIVE : str, default "ABSOLUTE"
                sets AT_relative, describing position reference

            ROTATED : list of 3 floats, default [0, 0, 0]
                Sets ROTATED_data, describing rotation of component

            ROTATED_RELATIVE : str, default "ABSOLUTE"
                Sets ROTATED_relative, sets reference for rotation

            RELATIVE : str
                Sets both AT_relative and ROTATED_relative

            WHEN : str, default ""
                Sets WHEN string, should contain logical c expression

            EXTEND : str, default ""
                Sets initial EXTEND string, should contain c code

            GROUP : str, default ""
                Sets name of group the component should belong to

            JUMP : str, default ""
                Sets JUMP str

            SPLIT : int, default 0 (disabled)
                Sets SPLIT value

            comment: str, default ""
                Sets comment string

            c_code_before: str, default ""
                Sets c code before component

            c_code_after: str, default ""
                Sets c code after component
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
        self.search_statement_list = SearchStatementList()
        self.save_parameters = save_parameters

        # references to component names
        self.AT_reference = None
        self.ROTATED_reference = None

        # If any keywords are set in kwargs, update these
        self.set_keyword_input(AT=AT, AT_RELATIVE=AT_RELATIVE, ROTATED=ROTATED,
                               ROTATED_RELATIVE=ROTATED_RELATIVE,
                               RELATIVE=RELATIVE, WHEN=WHEN, EXTEND=EXTEND,
                               GROUP=GROUP, JUMP=JUMP, SPLIT=SPLIT,
                               comment=comment, c_code_before=c_code_before,
                               c_code_after=c_code_after)

        """
        Could store an option for whether this component should be
        printed in instrument file or in a separate file which would
        then be included.
        """

        # Do not allow addition of attributes after init
        self._freeze()

    def set_keyword_input(self, AT=None, AT_RELATIVE=None, ROTATED=None,
                          ROTATED_RELATIVE=None, RELATIVE=None, WHEN=None,
                          EXTEND=None, GROUP=None, JUMP=None, SPLIT=None,
                          comment=None, c_code_before=None, c_code_after=None,
                          save_parameters=None):
        # Allow addition of attributes in init
        self._unfreeze()

        if AT is not None:
            self.set_AT(AT)

        if AT_RELATIVE is not None:
            self.set_AT_RELATIVE(AT_RELATIVE)

        self.ROTATED_specified = False
        if ROTATED is not None:
            self.set_ROTATED(ROTATED)

        if ROTATED_RELATIVE is not None:
            self.set_ROTATED_RELATIVE(ROTATED_RELATIVE)

        if RELATIVE is not None:
            self.set_RELATIVE(RELATIVE)

        if WHEN is not None:
            self.set_WHEN(WHEN)

        if EXTEND is not None:
            self.append_EXTEND(EXTEND)

        if GROUP is not None:
            self.set_GROUP(GROUP)

        if JUMP is not None:
            self.set_JUMP(JUMP)

        if SPLIT is not None:
            self.set_SPLIT(SPLIT)

        if comment is not None:
            self.set_comment(comment)

        if c_code_before is not None:
            self.set_c_code_before(c_code_before)

        if c_code_after is not None:
            self.set_c_code_after(c_code_after)

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
        """
        Method for setting position of component

        Sets the position of the component using provided length 3 list as a
        vector. If only a float is given, it is considered along the beam
        direction, [0, 0, z]. The RELATIVE keyword is used to specify in
        relation to what the position is given, and can take either a string
        with a component name or a Component object.

        Parameters
        ----------
        at_list : List of 3 floats or float
            Position of component relative to reference component

        keyword arguments:
            RELATIVE : str
                Sets reference component for position
        """
        if isinstance(at_list, (int, float, str)):
            at_list = [0, 0, at_list]

        if not isinstance(at_list, list):
            raise RuntimeError("set_AT should be given either a list or "
                               + "float, but received "
                               + str(type(at_list)))

        if len(at_list) != 3:
            raise RuntimeError("Position data given to set_AT should "
                               + "either be of length 3 or just a float.")

        # If parameter objects given, take their name instead
        for index, element in enumerate(at_list):
            if isinstance(element, (Parameter, DeclareVariable)):
                at_list[index] = element.name

        self.AT_data = at_list
        if RELATIVE is not None:
            self.set_AT_RELATIVE(RELATIVE)

    def set_AT_RELATIVE(self, relative):
        """
        Sets AT RELATIVE with string or Component instance

        Set relative which becomes the reference for this components position,
        it is possible to use a string that match another component name or
        use a Component object where the name is used as the reference.

        Parameters
        ----------

        relative : str or Component object
            Used as reference for component position
        """

        # Extract name if Component instance is given
        if isinstance(relative, Component):
            relative = relative.name
        elif not isinstance(relative, str):
            raise ValueError("Relative must be either string or "
                             + "Component object.")

        # Set AT relative
        if relative == "ABSOLUTE":
            self.AT_relative = "ABSOLUTE"
            self.AT_reference = None
        else:
            self.AT_relative = "RELATIVE " + relative
            self.AT_reference = relative

    def set_ROTATED(self, rotated_list, RELATIVE=None):
        """
        Method for setting rotation of component

        Parameters
        ----------
        rotated_list : List of 3 floats
            Rotation of component relative to reference component

        keyword arguments:
            RELATIVE : str
                Sets reference component for rotation
        """
        if not isinstance(rotated_list, list):
            raise RuntimeError("set_ROTATED should be given a list "
                               + " but received "
                               + str(type(rotated_list)))

        if len(rotated_list) != 3:
            raise RuntimeError("Rotation data given to set_ROTATED should "
                               + "be of length 3.")

        # If parameter objects given, take their name instead
        for index, element in enumerate(rotated_list):
            if isinstance(element, (Parameter, DeclareVariable)):
                rotated_list[index] = element.name

        self.ROTATED_data = rotated_list
        self.ROTATED_specified = True
        if RELATIVE is not None:
            self.set_ROTATED_RELATIVE(RELATIVE)

    def set_ROTATED_RELATIVE(self, relative):
        """
        Sets ROTATED RELATIVE with string or Component instance

        Set relative which becomes the reference for this components rotation,
        it is possible to use a string that match another component name or
        use a Component object where the name is used as the reference.

        Parameters
        ----------

        relative : str or Component object
            Used as reference for component rotation
        """

        self.ROTATED_specified = True
        # Extract name if a Component instance is given
        if isinstance(relative, Component):
            relative = relative.name
        elif not isinstance(relative, str):
            raise ValueError("Relative must be either string or "
                             + "Component object.")

        # Set ROTATED relative
        if relative == "ABSOLUTE":
            self.ROTATED_relative = "ABSOLUTE"
            self.ROTATED_reference = None
        else:
            self.ROTATED_relative = "RELATIVE " + relative
            self.ROTATED_reference = relative

    def set_RELATIVE(self, relative):
        """
        Method for setting reference of component position and rotation

        Input can be either a string matching an earlier component or a
        Component object.

        Parameters
        ----------
        relative : str
            Reference component for position and rotation
        """
        # Extract name if a Component instance is given
        if isinstance(relative, Component):
            relative = relative.name
        elif not isinstance(relative, str):
            raise ValueError("Relative must be either string or "
                             + "Component object.")

        if relative == "ABSOLUTE":
            self.AT_relative = "ABSOLUTE"
            self.AT_reference = None
            self.ROTATED_relative = "ABSOLUTE"
            self.ROTATED_reference = None
        else:
            self.AT_relative = "RELATIVE " + relative
            self.AT_reference = relative
            self.ROTATED_relative = "RELATIVE " + relative
            self.ROTATED_reference = relative

    def set_parameters(self, args_as_dict=None, **kwargs):
        """
        Set Component parameters from dictionary input or keyword arguments

        Relies on attributes added when McCode_Instr creates a subclass from
        the Component class where each component parameter is added as an
        attribute.

        An error is raised if trying to set a parameter that does not exist

        Parameters
        ----------
        args_as_dict : dict
            Parameters names and their values as dictionary
        """
        if args_as_dict is not None:
            parameter_dict = args_as_dict
        else:
            parameter_dict = kwargs

        for key, val in parameter_dict.items():
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
        """
        Method for setting WHEN c expression of this component

        Parameters
        ----------
        WHEN : str
            Sets WHEN c expression for named McStas component
        """
        if not isinstance(string, str):
            raise RuntimeError("set_WHEN expect a string, but was "
                               + "given " + str(type(string)))
        self.WHEN = "WHEN (" + string + ")"

    def set_GROUP(self, string):
        """
        Method for setting GROUP keyword of this component

        Parameters
        ----------
        GROUP : str
            Sets GROUP name for named McStas component
        """
        if not isinstance(string, str):
            raise RuntimeError("set_GROUP expect a string, but was "
                               + "given " + str(type(string)))
        self.GROUP = string

    def set_JUMP(self, string):
        """
        Method for setting JUMP expression of this component

        Should contain all code needed after JUMP

        Parameters
        ----------
        JUMP : str
            Sets JUMP expression for named McStas component
        """
        if not isinstance(string, str):
            raise RuntimeError("set_JUMP expect a string, but was "
                               + "given " + str(type(string)))
        self.JUMP = string

    def set_SPLIT(self, value):
        """
        Method for setting SPLIT value of this component

        Parameters
        ----------
        SPLIT : int or str
            Sets SPLIT value for named McStas component
        """
        if not isinstance(value, (int, str)):
            raise RuntimeError("set_SPLIT expect a integer or string, but "
                               + "was given " + str(type(value)))

        if isinstance(value, int):
            if value < 0:
                raise RuntimeError("set_SPLIT got a negative value, this is "
                                   + "meaningless, has to be a "
                                   + "positive value.")

        self.SPLIT = value

    def append_EXTEND(self, string):
        """
        Method for adding line of c to EXTEND section of this component

        Parameters
        ----------
        EXTEND : str
            Line of c code added to EXTEND section of named component
        """
        if not isinstance(string, str):
            raise RuntimeError("append_EXTEND expect a string, but was "
                               + "given " + str(type(string)))
        self.EXTEND = self.EXTEND + string + "\n"

    def set_comment(self, string):
        """
        Sets a comment displayed before the component in written files

        Parameters
        ----------
        string : str
            Comment string
        """
        if not isinstance(string, str):
            raise RuntimeError("set_comment expect a string, but was "
                               + "given " + str(type(string)))
        self.comment = string

    def set_c_code_before(self, string):
        """
        Method for setting c code before this component

        Parameters
        ----------
        code : str
            Code to be pasted before component
        """
        if not isinstance(string, str):
            raise RuntimeError("set_c_code_before expect a string, but was "
                               + "given " + str(type(string)))
        self.c_code_before = string

    def set_c_code_after(self, string):
        """
        Method for setting c code after this component

        Parameters
        ----------
        code : str
            Code to be pasted after component
        """
        if not isinstance(string, str):
            raise RuntimeError("set_c_code_after expect a string, but was "
                               + "given " + str(type(string)))
        self.c_code_after = string

    def set_save_parameters(self, value):
        if value:
            self.save_parameters = True
        else:
            self.save_parameters = False

    def add_search(self, statement, SHELL=False):
        """
        Adds a search statement to the component

        The search line can be used to tell McStas to search for files in
        additional locations. Double quotes are added.

        Parameters
        ----------
            statement : str
                The search statement

            SHELL : bool (default False)
                if True, shell keyword is added
        """

        self.search_statement_list.add_statement(SearchStatement(statement, SHELL=SHELL))

    def clear_search(self):
        """
        Clears the component of all search statements
        """

        self.search_statement_list.clear()

    def show_search(self):
        """
        Shows all search statements of component
        """

        print(self.search_statement_list)

    def write_component(self, fo, instrument_search=None):
        """
        Method that writes component to file

        Relies on attributes added when McStas_Instr creates a subclass
        based on the component class.

        """
        parameters_per_line = 2
        # Could use character limit on lines instead
        parameters_written = 0  # internal parameter

        save_parameter_string = ""

        if len(self.c_code_before) > 0:
            explanation = "From component named " + self.name
            fo.write("%s // %s\n" % (str(self.c_code_before), explanation))
            fo.write("\n")

        # Write comment if present
        if len(self.comment) > 1:
            fo.write("// %s\n" % (str(self.comment)))

        # Write search statements
        self.search_statement_list.write(fo)

        # Add search statement for instrument if supplied
        if instrument_search is not None:
            instrument_search.write(fo)

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
            elif isinstance(val, (Parameter, DeclareVariable)):
                # Extract the parameter name
                val = val.name

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

        if self.save_parameters:
            save_parameter_string += " %s\n" % self.AT_relative

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

    def make_write_string(self):
        string = ""

        string += f'fprintf(file, "COMPONENT {self.name} = {self.component_name}\\n");\n'

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
            elif isinstance(val, (Parameter, DeclareVariable)):
                # Extract the parameter name
                val = val.name

            component_parameters[key] = val

        for key, val in component_parameters.items():
            par_type = self.parameter_types[key] # from component reader

            cast = ""
            if par_type == "" or par_type == "double":
                type_string = "%lf"
                cast = "(double)"
            elif par_type == "int":
                type_string = "%d"
                cast = "(int)"
            elif par_type == "string":
                type_string = "%s"
            else:
                raise ValueError("Unknown parameter type: " + par_type)

            string += f'fprintf(file, "{key}={type_string}\\n", {cast} {val});\n'

        string += f'fprintf(file, "AT (%lf,%lf,%lf) {self.AT_relative}\\n",'
        string += "(double) " + str(self.AT_data[0]) + ","
        string += "(double) " + str(self.AT_data[1]) + ","
        string += "(double) " + str(self.AT_data[2]) + ");\n"

        if self.ROTATED_specified:
            string += f'fprintf(file, "ROTATED (%lf,%lf,%lf) {self.ROTATED_relative}\\n",'
            string += "(double) " + str(self.ROTATED_data[0]) + ","
            string += "(double) " + str(self.ROTATED_data[1]) + ","
            string += "(double) " + str(self.ROTATED_data[2]) + ");\n"

        return string

    def __str__(self):
        """
        Returns string of information about the component

        Includes information on required parameters if they are not yet
        specified. Information on the components are added when the
        class is used as a superclass for classes describing each
        McStas component.
        """
        string = ""

        if len(self.c_code_before) > 1:
            string += self.c_code_before + "\n"
        string += self.search_statement_list.make_string()
        if len(self.comment) > 1:
            string += "// " + self.comment + "\n"
        if self.SPLIT != 0:
            string += "SPLIT " + str(self.SPLIT) + " "
        string += "COMPONENT " + str(self.name)
        string += " = " + str(self.component_name) + "("

        last_par_name = ""
        for key in self.parameter_names:
            if getattr(self, key) is not None:
                last_par_name = key

        for key in self.parameter_names:
            val = getattr(self, key)
            parameter_name = bcolors.BOLD + key + bcolors.ENDC
            if val is not None:
                unit = ""
                if key in self.parameter_units:
                    unit += " // [" + self.parameter_units[key] + "]"
                if isinstance(val, Parameter):
                    #val_string = val.print_line() # too long
                    val_string = val.name
                elif isinstance(val, DeclareVariable):
                    val_string = val.name
                else:
                    val_string = str(val)

                value = (bcolors.BOLD
                         + bcolors.OKGREEN
                         + val_string
                         + bcolors.ENDC
                         + bcolors.ENDC)

                string += "\n"
                string += "  " + parameter_name
                string += " = " + value
                if key != last_par_name:
                    string += ","
                string += unit

            else:
                if self.parameter_defaults[key] is None:
                    string += "\n"
                    string += "  " + parameter_name
                    string += bcolors.FAIL
                    string += " : Required parameter not yet specified"
                    string += bcolors.ENDC

        string += "\n)"
        if not self.WHEN == "":
            string += " " + self.WHEN
        string += "\n"
        string += f"AT {tuple(self.AT_data)} "
        #"AT (" + str(self.AT_data[0]) + ", " + str(self.AT_data[1]) + ", " + str(self.AT_data[2]) + ") "
        string += str(self.AT_relative) + "\n"
        if self.ROTATED_specified:
            string += f"ROTATED {tuple(self.ROTATED_data)}"
            string += " " + self.ROTATED_relative + "\n"
        if not self.GROUP == "":
            string += "GROUP " + self.GROUP + "\n"
        if not self.EXTEND == "":
            string += "EXTEND %{" + "\n"
            string += self.EXTEND + "%}" + "\n"
        if not self.JUMP == "":
            string += "JUMP " + self.JUMP + "\n"
        if len(self.c_code_after) > 1:
            string += self.c_code_after + "\n"

        return string.strip()

    def print_long(self):
        """
        Prints information about the component

        Includes information on required parameters if they are not yet
        specified. Information on the components are added when the
        class is used as a superclass for classes describing each
        McStas component.
        """
        print(self.__str__())

    def __repr__(self):
        return self.__str__()

    def print_short(self, longest_name=None):
        """Prints short description of component to list print"""
        if self.ROTATED_specified:
            print_rotate_rel = self.ROTATED_relative
        else:
            print_rotate_rel = self.AT_relative

        if longest_name is not None:
            number_of_spaces = 3+longest_name-len(self.name)
            print(str(self.name) + " "*number_of_spaces, end='')
            print(str(self.component_name),
                  "\tAT", self.AT_data, self.AT_relative,
                  "ROTATED", self.ROTATED_data, print_rotate_rel)
        else:
            print(str(self.name), "=", str(self.component_name),
                  "\tAT", self.AT_data, self.AT_relative,
                  "ROTATED", self.ROTATED_data, print_rotate_rel)

    def show_parameters(self, line_length=None):
        """
        Shows available parameters and their defaults for the component

        Any value specified is not reflected in this view. The
        additional attributes defined when McStas_Instr creates
        subclasses for the individual components are required to run
        this method.
        """

        # line_limit created in _create_component_instance on instr
        if line_length is None:
            line_length = self.line_limit

        # Minimum reasonable line length
        if line_length < 74:
            line_length = 74

        print(" ___ Help "
              + self.component_name + " "
              + (line_length - 11 - len(self.component_name))*"_")
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
                parameter_input = getattr(self, parameter)
                # Use name when an par/var object is found
                if isinstance(parameter_input, (Parameter, DeclareVariable)):
                    parameter_input = parameter_input.name

                this_set_value = str(parameter_input)
                value = (" = "
                         + bcolors.BOLD
                         + bcolors.OKGREEN
                         + this_set_value
                         + bcolors.ENDC
                         + bcolors.ENDC)
                characters_from_value = 3 + len(this_set_value)
            characters_before_comment += characters_from_value

            print(parameter_name + value + unit, end="")

            if characters_before_comment + len(comment) < line_length:
                print(comment)
            else:
                length_for_comment = line_length - characters_before_comment
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

        print(line_length*"-")

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

    def check_parameters(self, instrument_variables):
        """
        Checks the current component parameters are in given name list

        The name list will typically be a list of instrument parameters and
        declared variables.

        Parameters
        ----------

        instrument_variables : list of str
            List of instrument variable names
        """
        McStas_constants = ["DEG2RAD", "RAD2DEG", "MIN2RAD", "RAD2MIN", "V2K",
                            "K2V", "VS2E", "SE2V", "FWHM2RMS", "RMS2FWHM",
                            "MNEUTRON" "HBAR", "PI", "FLT_MAX"]

        # parameter_names attribute added in _create_component_instance
        for par_name in self.parameter_names:
            par = getattr(self, par_name)
            if isinstance(par, str):
                if not par.isalpha():
                    # Allow numbers and strings with math symbols
                    # They may have errors, but can't be easily checked
                    continue

                if par in McStas_constants:
                    # Allow McStas defined constants
                    continue

                if par in instrument_variables:
                    # Allow variables on given whitelist
                    continue

                # If none of the above approves the variable, raise error
                raise McStasError("Variable not recognized.\n"
                                  f"Unrecognized variable '{par}' "
                                  "assigned to component parameter "
                                  f"'{par_name}' in component "
                                  f"'{self.name}' of type "
                                  f"'{self.component_name}'.\n"
                                  "This check can be skipped with "
                                  "settings(checks=False)")
