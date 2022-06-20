from mcstasscript.instr_reader.util import SectionReader


class UservarsReader(SectionReader):
    """
    Reads the uservars section of a McStas instrument file and adds
    the found parameters / functions / structs to the McStasScript
    Instr instance. The information can also be written to a python
    file for reproduction of a McStas instrument.
    """

    def __init__(self, Instr, write_file, product_filename,
                 get_next_line, return_line):

        super().__init__(Instr, write_file, product_filename,
                         get_next_line, return_line)

        self.in_uservars_function = False
        self.in_struct_definition = False
        self.bracket_counter = 0

    def read_uservars_line(self, line):
        """
        Reads line of instrument uservars, returns bolean.  If it encounters
        the end of the uservars section, it returns False, otherwise True.

        The contents of the uservars section is written to the McStasScript
        Instr object.
        """

        continue_uservars = True

        # Remove comments
        if "//" in line:
            line = line.split("//", 1)[0]

        # Remove %} and signify end if this is found
        if "%}" in line:
            continue_uservars = False
            line = line.split("%}", 1)[0]

        if "/*" in line:
            line = line.split("/*", 1)[0].strip()

        if self.in_uservars_function:
            if "{" in line:
                self.bracket_counter += 1

            if "}" in line:
                self.bracket_counter -= 1

            if self.bracket_counter == 0:
                self.in_uservars_function = False

            self.Instr.append_uservars(line)
            self._write_uservars_line(line)

        # Check for functions
        if ("(" in line and ";" not in line and " " in line.strip()
                and not self.in_uservars_function):

            # If in function, it will define a block
            n_curly_brackets = line.count("{")
            n_curly_brackets -= line.count("}")

            while n_curly_brackets != 0 or ("{" not in line):
                next_line = self.get_next_line()
                line += next_line

                n_curly_brackets = line.count("{")
                n_curly_brackets -= line.count("}")

            after_curly_bracket = line.split("}")[-1]

            uservars_lines = line.split("\n")
            for uservars_line in uservars_lines:
                uservars_line = uservars_line.rstrip()
                uservars_line = uservars_line.replace('\\n', "\\\\n")
                uservars_line = uservars_line.replace('"', "\\\"")
                self.Instr.append_uservars(uservars_line)
                self._write_uservars_line(uservars_line)

            line = after_curly_bracket

        # Check for struct / function that returns struct
        if line.strip().startswith("struct "):
            # Can be a function returning struct or struct definition

            # If struct definition, no parenthesis and ; after )
            n_curly_brackets = line.count("{")
            n_curly_brackets -= line.count("}")

            # Add lines until end of block found
            while n_curly_brackets != 0 or ("{" not in line):

                next_line = self.get_next_line()
                line += next_line

                n_curly_brackets = line.count("{")
                n_curly_brackets -= line.count("}")

                if "{" in line:
                    before_curly_bracket = line.split("{", 1)[0]
                    if "(" in before_curly_bracket and ")" in before_curly_bracket:
                        # This is a function that returns a struct!
                        self.in_uservars_function = True

            after_curly_bracket = line.split("}")[-1]

            # if not in function, add until ; is found
            while ";" not in after_curly_bracket and not self.in_uservars_function:
                # It is surely a struct, find ;
                line += self.get_next_line()
                after_curly_bracket = line.split("}")[-1]

            uservars_lines = line.split("\n")
            for uservars_line in uservars_lines:
                uservars_line = uservars_line.rstrip()
                uservars_line = uservars_line.replace('\\n', "\\\\n")
                uservars_line = uservars_line.replace('"', "\\\"")
                self.Instr.append_uservars(uservars_line)
                self._write_uservars_line(uservars_line)

            if self.in_uservars_function:
                line = line.split("}")[-1].strip()
            else:
                line = line.split(";")[-1].strip()

            # if in function, stop now
            self.in_uservars_function = False

        # Grab defines
        if line.strip().startswith("#define"):
            # Include define statements as uservars append
            line = line.rstrip()
            line = line.replace('\\n', "\\\\n")
            line = line.replace('"', "\\\"")
            self.Instr.append_uservars(line)
            self._write_uservars_line(line)

        if "\n" in line:
            line = line.strip("\n")

        # Read single line parameter definitions
        if ";" in line and not self.in_uservars_function:
            # This line contains c statements
            statements = line.split(";")

            for statement in statements:
                statement = statement.strip()
                if (statement != "\n" and statement != " "
                        and len(statement) > 1):
                    self._read_uservars_statement(statement)

        return continue_uservars

    def _read_uservars_statement(self, statement):
        """
        Reads single uservars statements, which can have multiple
        variables.
        """

        statement = statement.strip()

        # Find type (same for all parameters in one statement)
        this_type = statement.split(" ", 1)[0]
        statement = statement.split(" ", 1)[1].strip()

        if this_type == "const":  # other c keywords to consider?
            this_type += " " + statement.split(" ", 1)[0]
            statement = statement.split(" ", 1)[1].strip()

        # Check for bracket initialization of arrays
        if "," in statement:
            variables = statement.split(",")
            fixed_variables = []
            array_mode = False
            for variable in variables:

                if "{" not in variable and array_mode is False:
                    fixed_variables.append(variable)
                elif "{" in variable:
                    temp_variable = variable + ","
                    array_mode = True
                elif "}" not in variable:
                    temp_variable += variable + ","
                else:
                    temp_variable += variable
                    fixed_variables.append(temp_variable)
                    array_mode = False

            variables = fixed_variables

        else:
            # No commas means just one parameter
            variables = [statement]

        # Treat each variable independently
        for variable in variables:
            variable = variable.strip()

            dynamic_size = False
            kw_args = {}

            if "=" in variable:
                value = variable.split("=")[1].strip()
                # remove the value part before proceeding
                variable = variable.split("=")[0].strip()

                if "{" in value:
                    # handle array as value
                    value = value.split("{")[1]
                    if "{" in value:
                        raise ValueError("Can not load arrays with larger"
                                         + "than 1 dimension yet.")
                    value = value.split("}")[0]
                    values = value.split(",")
                    return_value = []
                    for val in values:
                        return_value.append(float(val))
                else:
                    try:
                        return_value = float(value)
                    except:
                        value = value.replace('"', "\\\"")
                        #return_value = '"' + value + '"'
                        return_value = value

                kw_args["value"] = return_value

            # Handle array
            if "[" in variable:
                array_sizes = []
                array_size_strings = variable.split("[")
                # remove the array size part before proceeding
                variable = variable.split("[", 1)[0].strip()
                for array_size_string in array_size_strings:
                    if "]" in array_size_string:
                        this_size = array_size_string.split("]")[0]
                        try:
                            # Size uservarsd normally
                            array_sizes.append(int(this_size))
                        except:
                            # No size uservarsd means the size is automatic
                            dynamic_size = True

                if len(array_sizes) > 1:
                    raise ValueError("Can not handle arrays with larger"
                                     + " than 1 dimension yet")
                if not dynamic_size:
                    kw_args["array"] = array_sizes[0]

            if dynamic_size:
                # McStasScript needs size of array, so it is found manually
                kw_args["array"] = len(kw_args["value"])

            # value, array and typeremoved, all that remians is the name
            variable_name = variable
            self.Instr.add_user_var(this_type, variable_name, **kw_args)

            # Also write it to a file?
            write_string = []
            write_string.append(self.instr_name)
            write_string.append(".add_user_var(")
            write_string.append("\"" + this_type + "\"")
            write_string.append(", ")
            write_string.append("\"" + variable_name + "\"")
            write_string.append(self._kw_to_string(kw_args))
            write_string.append(")\n")

            # Write uservars parameter to python file
            self._write_to_file(write_string)

    def _write_uservars_line(self, string):

        string = string.rstrip()

        write_string = []
        write_string.append(self.instr_name)
        write_string.append(".append_uservars(")
        write_string.append("\"" + string + "\"")
        write_string.append(")\n")

        self._write_to_file(write_string)
