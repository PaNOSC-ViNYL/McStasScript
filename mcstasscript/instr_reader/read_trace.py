from mcstasscript.instr_reader.util import SectionReader


class TraceReader(SectionReader):
    """
    Reads the trace section of a McStas instrument file. For each
    component a McStasScript component instance is created and the
    parameters/keywords are applied to this instance. When the next
    component is found, the previous component is written to the
    python file for reproduction of the McStas instrument.
    """

    def __init__(self, Instr, write_file, product_filename,
                 get_next_line, return_line):

        super().__init__(Instr, write_file, product_filename,
                         get_next_line, return_line)

        self.current_component = None
        self.in_component_mode = False
        self.EXTEND_mode = False
        self.component_copy_target = None
        self.SPLIT = 0
        self.stored_include = None

    def sanitize_line(self, line):
        """
        Removes comments, the starting blok and newline characters
        """

        line = line.strip()

        # Remove comments
        if "//" in line:
            line = line.split("//", 1)[0].strip()

        if line.startswith("TRACE"):
            line = line.split("TRACE", 1)[1].strip()

        if "/*" in line:
            if "*/" in line:
                line = line.split("/*", 1)[0] + line.split("*/", 1)[1]
            else:
                line = line.split("/*", 1)[0]

        # Remove newline at the end of the line
        if line.endswith("\n"):
            line = line[:-1]

        return line

    def read_trace_line(self, line):
        """
        Reads line of McStas file from TRACE section. Has the responsibility
        of setting continue_trace to false when finding the end of the TRACE
        section. May take extra lines through get_new_line if statements are
        spaced out over several lines.
        """

        continue_trace = True

        # Find stop characeters
        if line.startswith("FINALLY"):
            continue_trace = False

        if line.startswith("END"):
            continue_trace = False

        if line.strip().startswith("%include") or line.strip().startswith("#include"):
            # Handle include statement and attatch it to a component
            if self.current_component is not None:
                c_code_after = self.current_component.c_code_after + line + "\n"
                self.current_component.set_c_code_after(c_code_after)
            else:
                # If the include statement is before the first component,
                # it is saved and attatched to the next component
                line = line.replace('"', "\\\"")
                self.stored_include = line.strip()

        # If the line is just a new line quit
        if line == "\n" or line == "":
            return continue_trace

        line = self.sanitize_line(line)

        # Handle keywords that appear before components
        if line.startswith("SPLIT"):
            # Read split and save for the next component
            line = line.split("SPLIT", 1)[1].strip()
            if line.startswith("COMPONENT"):
                # Default split without indicating amount
                self.SPLIT = ""
            else:
                try:
                    self.SPLIT = int(line.split(" ", 1)[0].strip())
                except:
                    #self.SPLIT = "\"" + line.split(" ", 1)[0].strip() + "\""
                    self.SPLIT = line.split(" ", 1)[0].strip()

                if " " in line:
                    # If the line continues, remove the SPLIT number
                    line = line.split(" ", 1)[1].strip()

        # Read component definition (can be over several lines)
        if line.startswith("COMPONENT") or line.startswith("REMOVABLE COMPONENT"):
            # Start ned component, but write the previous component to file first
            if self.stored_include is not None and self.current_component is not None:
                # In case an include statement was stored, include that statement
                self.current_component.set_c_code_before(self.stored_include)
                self.stored_include = None
            # write previous component
            self._write_component_to_py()

            # start new component
            self.in_component_mode = True
            # Assume this is not a copy
            self.component_copy_target = None

            # Remove COMPONENT from line
            if line.startswith("COMPONENT"):
                line = line[9:].strip()
            elif line.startswith("REMOVABLE COMPONENT"):
                line = line[19:].strip()

            # Add new lines until the entire component definition is found
            full_component_line = False
            while not full_component_line:

                expected_end_parenthesis = 1 + line.count("COPY")

                if line.count("(") >= expected_end_parenthesis:
                    full_component_line = True

                if not full_component_line:
                    new_line = self.get_next_line()
                    new_line = self.sanitize_line(new_line)
                    if new_line.startswith("AT") or new_line.startswith("WHEN"):
                        full_component_line = True
                        self.return_line()
                    else:
                        line += new_line

            # Retrieve information from component definition
            instance_name = line.split("=", 1)[0].strip()
            component_name = line.split("=", 1)[1].split("(", 1)[0].strip()
            line = line.split("=", 1)[1].split("(", 1)[1].strip()
            if component_name == "COPY":
                # Copy instance
                self.component_copy_target = line.split(")", 1)[0].strip()

                if line.strip().startswith("("):
                    line = line.split("(", 1)[1].strip()

                if self.component_copy_target == "PREVIOUS":
                    # Get the previous component name
                    last_component = self.Instr.get_last_component()
                    self.component_copy_target = last_component.name

                if "(" in instance_name:
                    # Using the copy notation, replace this with meaningful replacement
                    base_name = self.component_copy_target + "_copy"
                    name = base_name
                    comp_names = [x.name for x in self.Instr.component_list]
                    index = 0
                    while name in comp_names:
                        name = base_name + "_" + str(index)
                        index += 1

                    instance_name = name

                self.current_component = self.Instr.copy_component(instance_name,
                                                                   self.component_copy_target)

            else:
                # Normal component instance
                self.current_component = self.Instr.add_component(instance_name,
                                                                  component_name)

            # In case there are no parameters, stop in_component_mode
            if line.startswith(")"):
                self.in_component_mode = False
                line = line.split(")", 1)[1]

            if self.SPLIT != 0:
                self.current_component.set_SPLIT(self.SPLIT)
                self.SPLIT = 0

        # In case of COPY, there can be empty parameter lists
        if self.in_component_mode:  # and self.component_copy_target != None:
            # Check if this line starts WHEN or AT
            if line.strip().startswith("AT"):
                self.in_component_mode = False
            if line.strip().startswith("WHEN"):
                self.in_component_mode = False
            # If none of these occur, read the parameters

        # In component mode reads parameters of each new line read
        if self.in_component_mode:

            par_line = line
            # check for parameters
            if par_line.strip().startswith("("):
                par_line = line.split("(", 1)[1]

            # _in_func like python in, but does not look inside parenthesis
            if self._in_func(line, ")"):
                self.in_component_mode = False
                par_line = self._split_func(line, ")", 1)[0]
                line = self._split_func(line, ")", 1)[1]

            # All parameters found saved in dictionary
            par_dict = {}

            """
            A parameter line can contain a comma for separating parameters or
            inside of a string. This piece of code finds the next comma and
            checks if there is an equal number of quotation marks in the first
            part, if not it increases the read part of the line to the next
            comma. In this way commas in strings do not separate parameters
            in the component input.
            """
            while len(par_line) > 0:
                # find the next parameter expression
                if self._in_func_brack(par_line, ","):
                    # start of expression to evaluate
                    par_exp = par_line.split(",", 1)[0].strip()
                    par_exp = self._split_func_brack(par_line, ",", 1)[0]
                    # remove the part already taken from the par_line
                    par_line = self._split_func_brack(par_line, ",", 1)[1]
                    # The length of quotation_split will be one more than
                    #  the number of quotation marks in par_exp
                    quotation_split = par_exp.split('"')
                    while (len(quotation_split) - 1) % 2 != 0:
                        # There is an uneven number of quotation marks
                        par_exp += ","
                        if "," in par_line:
                            # include up to the next comma in par_exp
                            par_exp += par_line.split(",", 1)[0]
                            # remove the part of the par_line added to par_exp
                            par_line = par_line.split(",", 1)[1]
                        else:
                            # no commas left, must be end of par_line
                            par_exp += par_line.strip()
                            par_line = ""

                        quotation_split = par_exp.split('"')
                else:
                    # last parameter
                    par_exp = par_line
                    par_line = ""

                if "=" in par_exp:
                    par_name = par_exp.split("=", 1)[0].strip()
                    par_value = par_exp.split("=", 1)[1].strip()

                    par_dict[par_name] = par_value

            # Set all found parameters in the component
            self.current_component.set_parameters(par_dict)

        # Read keywords given after parameters but before position (WHEN)
        if line.strip().upper().startswith("WHEN"):
            if "(" in line:
                line = line.split("(", 1)[1].strip()
                # need to find the closing parenthesis
                parenthesis_counter = 1
                character_index = -1
                for character in line:
                    character_index += 1
                    if character == "(":
                        parenthesis_counter += 1
                    if character == ")":
                        parenthesis_counter -= 1
                    if parenthesis_counter == 0:
                        end_index = character_index
                        break

                WHEN_statement = line[:character_index]
                WHEN_statement = WHEN_statement.replace('"', "\\\"")
                line = line[character_index+1:].strip()
            else:
                # WHEN statement that does not use parenthesis
                if "AT" in line:
                    WHEN_statement = line.split("AT", 1)[0]
                    line = "AT" + line.split("AT", 1)[1]
                else:
                    WHEN_statement = line.split("WHEN ", 1)[1]
                    line = ""

            self.current_component.set_WHEN(WHEN_statement)

        # Read component position
        if line.strip().startswith("AT"):
            # read AT statement
            line = line.split("(", 1)[1].strip()
            AT_data = []
            AT_data.append(self._split_func(line, ",", 1)[0])
            line = self._split_func(line, ",", 1)[1]
            AT_data.append(self._split_func(line, ",", 1)[0])
            line = self._split_func(line, ",", 1)[1]
            AT_data.append(self._split_func(line, ")", 1)[0])
            line = self._split_func(line, ")", 1)[1]

            if line.strip().startswith("ABSOLUTE"):
                line = line.split(" ", 1)[1].strip()
                relative_name = "ABSOLUTE"
                # The line can continue, remove the used part
                if " " in line.strip():
                    line = line.strip().split(" ", 1)[1].strip()
                else:
                    line = ""
            elif line.strip().startswith("RELATIVE"):
                line = line.strip().split(" ", 1)[1].strip()
                if " " in line:
                    relative_name = line.split(" ", 1)[0].strip()
                else:
                    relative_name = line.strip()
                # The line can continue, remove the used part
                if " " in line:
                    line = line.split(" ", 1)[1].strip()
                else:
                    line = ""
            else:
                raise ValueError("Could not read: " + line)

            self.current_component.set_AT(AT_data, RELATIVE=relative_name)

        # Read component rotation
        if line.strip().startswith("ROTATED"):
            # read ROTATED statement
            line = line.split("(", 1)[1].strip()
            ROTATED_data = []

            ROTATED_data.append(self._split_func(line, ",", 1)[0])
            line = self._split_func(line, ",", 1)[1]
            ROTATED_data.append(self._split_func(line, ",", 1)[0])
            line = self._split_func(line, ",", 1)[1]
            ROTATED_data.append(self._split_func(line, ")", 1)[0])
            line = self._split_func(line, ")", 1)[1]

            if line.strip().startswith("ABSOLUTE"):
                relative_name = "ABSOLUTE"
                if " " in line.strip():
                    line = line.strip().split(" ", 1)[1].strip()
                else:
                    line = ""
            elif line.strip().startswith("RELATIVE"):
                line = line.strip().split(" ", 1)[1].strip()
                relative_name = line.split(" ", 1)[0].strip()
                # The line can continue, remove the used part
                if " " in line:
                    line = line.split(" ", 1)[1].strip()
                else:
                    line = ""
            else:
                raise ValueError("Could not read: " + line)

            self.current_component.set_ROTATED(ROTATED_data,
                                               RELATIVE=relative_name)

        # Read keywords after component position (GROUP, EXTEND, JUMP)
        if line.strip().upper().startswith("GROUP"):
            line = line.strip()

            group_name = line.split(" ", 1)[1].strip()
            #group_name = "\"" + group_name + "\""
            group_name = group_name

            line = ""

            self.current_component.set_GROUP(group_name)

        if line.strip().upper().startswith("EXTEND"):
            line = line.split("EXTEND", 1)[1].strip()
            self.EXTEND_mode = True

        if self.EXTEND_mode:
            if "%{" in line:
                line = line.strip().split("%{", 1)[1].strip()

            if "%}" in line:
                line = line.strip().split("%}", 1)[0].strip()
                self.EXTEND_mode = False

            if len(line) > 0 and line != "\n":
                line = line.replace('\\n', "\\\\n")
                line = line.replace('"', "\\\"")
                self.current_component.append_EXTEND(line)

        if line.strip().upper().startswith("JUMP "):
            line = line.strip().split(" ", 1)[1]
            self.current_component.set_JUMP(line)

        if not continue_trace:
            # write last component
            self._write_component_to_py()

        return continue_trace

    def _write_component_to_py(self):
        # code for writing McStasScript python file
        if self.current_component is not None:

            # Write the add_component statement
            write_string = ["\n"]
            write_string.append(self.current_component.name)
            write_string.append(" = ")
            write_string.append(self.instr_name)
            if self.component_copy_target is None:
                write_string.append(".add_component(")
                write_string.append("\"" + self.current_component.name + "\"")
                write_string.append(", ")
                component_name = str(self.current_component.component_name)
                write_string.append("\"" + component_name + "\"")
            else:
                write_string.append(".copy_component(")
                write_string.append("\"" + self.current_component.name + "\"")
                write_string.append(", ")
                write_string.append("\"" + self.component_copy_target + "\"")
            write_string.append(")\n")

            self._write_to_file(write_string)

            # Write all parameters as attribute updates
            for key in self.current_component.parameter_names:
                val = getattr(self.current_component, key)
                if val is not None:
                    write_string = []
                    write_string.append(self.current_component.name)
                    write_string.append(".")
                    write_string.append(key)
                    write_string.append(" = ")

                    try:
                        # No problems if the value is a number
                        float(val)
                    except:
                        # If the value is a string, it needs quotes
                        if '"' in val:
                            # If it already has quotes, these need escapes
                            val = val.replace('"', '\\\"')
                        val = '"' + val + '"'

                    write_string.append(val)
                    write_string.append("\n")

                    self._write_to_file(write_string)

            # Write EXTEND block if present
            if self.current_component.EXTEND != "":
                EXTEND = self.current_component.EXTEND
                EXTEND_lines = EXTEND.split("\n")
                EXTEND_lines = EXTEND_lines[:-1]

                for EXTEND_line in EXTEND_lines:
                    write_string = []
                    write_string.append(self.current_component.name)
                    write_string.append(".append_EXTEND(")
                    write_string.append("\"" + EXTEND_line + "\"")
                    write_string.append(")\n")

                    self._write_to_file(write_string)

            # Write WHEN statement if present
            if self.current_component.WHEN != "":
                write_string = []
                write_string.append(self.current_component.name)
                write_string.append(".set_WHEN(")
                WHEN = self.current_component.WHEN
                WHEN = WHEN.split("(", 1)[1].strip()
                WHEN = WHEN[:-1]
                write_string.append("\"" + WHEN + "\"")
                write_string.append(")\n")

                self._write_to_file(write_string)

            # Write SPLIT if present
            if self.current_component.SPLIT != 0:
                write_string = []
                write_string.append(self.current_component.name)
                write_string.append(".set_SPLIT(")
                if self.current_component.SPLIT == "":
                    write_string.append('""')
                else:
                    if isinstance(self.current_component.SPLIT, str) and self.current_component.SPLIT != "":
                        write_string.append('"' + str(self.current_component.SPLIT) + '"')
                    else:
                        write_string.append(str(self.current_component.SPLIT))
                write_string.append(")\n")

                self._write_to_file(write_string)

            # Write GROUP if present
            if self.current_component.GROUP != "":
                write_string = []
                write_string.append(self.current_component.name)
                write_string.append(".set_GROUP(\"")
                write_string.append(str(self.current_component.GROUP))
                write_string.append("\")\n")

                self._write_to_file(write_string)

            # Write JUMP if present
            if self.current_component.JUMP != "":
                write_string = []
                write_string.append(self.current_component.name)
                write_string.append(".set_JUMP(")
                jump_string = str(self.current_component.JUMP)
                write_string.append("\"" + jump_string + "\"")
                write_string.append(")\n")

                self._write_to_file(write_string)

            # Write c_code_before if present
            if self.current_component.c_code_before != "":
                write_string = []
                write_string.append(self.current_component.name)
                write_string.append(".set_c_code_before(")
                c_code_string = str(self.current_component.c_code_before)
                write_string.append("\"" + c_code_string + "\"")
                write_string.append(")\n")

                self._write_to_file(write_string)

            # Write c_code_after if present
            if self.current_component.c_code_after != "":
                write_string = []
                write_string.append(self.current_component.name)
                write_string.append(".set_c_code_after(")
                c_code_string = str(self.current_component.c_code_after)
                write_string.append("\"" + c_code_string + "\"")
                write_string.append(")\n")

                self._write_to_file(write_string)

            # Write AT
            write_string = []
            write_string.append(self.current_component.name)
            write_string.append(".set_AT(")
            write_string.append(str(self.current_component.AT_data))
            write_string.append(", RELATIVE=")
            if self.current_component.AT_relative == "ABSOLUTE":
                write_string.append("\"" + "ABSOLUTE" + "\"")
            else:
                relative = self.current_component.AT_relative.split(" ")[1]
                write_string.append("\"" + relative + "\"")
            write_string.append(")\n")

            self._write_to_file(write_string)

            # Write ROTATED
            write_string = []
            write_string.append(self.current_component.name)
            write_string.append(".set_ROTATED(")
            write_string.append(str(self.current_component.ROTATED_data))
            write_string.append(", RELATIVE=")
            if self.current_component.ROTATED_relative == "ABSOLUTE":
                write_string.append("\"" + "ABSOLUTE" + "\"")
            else:
                relative = self.current_component.ROTATED_relative.split(" ")
                relative = relative[1]
                write_string.append("\"" + relative + "\"")
            write_string.append(")\n")

            if self.current_component.ROTATED_specified:
                self._write_to_file(write_string)
