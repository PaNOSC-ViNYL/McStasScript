from mcstasscript.instr_reader.util import SectionReader


class DefinitionReader(SectionReader):
    """
    Responsible for reading the defintion section of McStas instrument
    file. Contains instrument name and instrument parameters.
    """

    def __init__(self, Instr, write_file, product_filename,
                 get_next_line, return_line):

        super().__init__(Instr, write_file, product_filename,
                         get_next_line, return_line)

    def read_definition_line(self, line):
        """
        Reads line of instrument definition, returns bolean.  If it encounters
        the end of the definition section, it returns False, otherwise True.

        The contents of the definition section is written to the McStasScript
        Instr object.
        """

        continue_definition = True

        # Remove comments
        if "//" in line:
            line = line.split("//")[0]

        if "(" in line:
            # Start of instrument definition, get name
            self.instr_name = line.split("(")[0].strip().split(" ")[-1]
            self._start_py_file()
            # Remove the parameters from the paranthesis
            parameters = line.split("(")[1]
            if ")" in line:
                # Found end of definition
                continue_definition = False
                # these parameters are to be analyzed
                parameters = parameters.split(")")[0]

        elif ")" in line:
            # Found end of definition
            continue_definition = False
            # these parameters are to be analyzed
            parameters = line.split(")")[0]
        else:
            # Neither start or end on this line, analyze everything
            parameters = line

        # Separate into individual parameters
        parameters = parameters.split(",")
        if "\n" in parameters:
            parameters.remove("\n")

        for parameter in parameters:
            # Analyze individual parameter
            parameter = parameter.strip()

            if parameter == "":
                # If the parameter is empty, skip it.
                continue

            # Ready for keyword arguments
            kw_args = {}

            # Default to double type if nothing else is set
            parameter_type = "double"
            if " " and "=" in parameter:
                # Read parameter type
                type_and_name = parameter.split("=", 1)[0].strip()

                if " " in type_and_name:
                    parameter_type = type_and_name.split(" ", 1)[0].strip()
                    parameter = parameter.split(" ", 1)[1].strip()
            elif " " in parameter:
                # Read parameter type
                parameter_type = parameter.split(" ", 1)[0].strip()
                parameter = parameter.split(" ", 1)[1].strip()

            if "=" in parameter:
                # Read default value
                parameter_name = parameter.split("=")[0].strip()
                value = parameter.split("=")[1].strip()

                if parameter_type == "string":
                    if '"' in value:
                        pass
                        # Value has to be normal for object version
                        #value = value.replace('"', "\\\"")
                        #value = "\"" + value + "\""
                else:
                    if parameter_type == "int":
                        value = int(value)
                    else:
                        value = float(value)

                # Add defualt value to keyword arguments
                kw_args["value"] = value

            else:
                # No default value, just return the striped name
                parameter_name = parameter.strip()

            # Add this parameter to the object
            self.Instr.add_parameter(parameter_type, parameter_name, **kw_args)

            # Fix values for script version
            if parameter_type == "string" and "value" in kw_args:
                if isinstance(kw_args["value"], str):
                    kw_args["value"] = kw_args["value"].replace('"', '\\\"')
                    kw_args["value"] = "\"" + kw_args["value"] + "\""

            # Also write it to a file?
            write_string = []
            write_string.append(self.instr_name)
            write_string.append(".add_parameter(")
            write_string.append("\"" + parameter_type + "\"")
            write_string.append(", ")
            write_string.append("\"" + parameter_name + "\"")
            write_string.append(self._kw_to_string(kw_args))
            write_string.append(")\n")

            self._write_to_file(write_string)

        return continue_definition

    def _start_py_file(self):
        write_string = []

        # Write warning about robustness of this feature
        write_string.append("\"\"\"\n")
        write_string.append("This McStasScript file was generated from a\n")
        write_string.append("McStas instrument file. It is advised to check\n")
        write_string.append("the content to ensure it is as expected.\n")
        write_string.append("\"\"\"\n")

        # import McStasScript
        write_string.append("from mcstasscript.interface ")
        write_string.append("import ")
        write_string.append("instr, plotter, functions")
        write_string.append("\n\n")

        write_string.append(self.instr_name)
        write_string.append(" = instr.McStas_instr(")
        write_string.append("\"" + self.instr_name + "_generated\"")
        write_string.append(")\n")

        self._write_to_file(write_string)
