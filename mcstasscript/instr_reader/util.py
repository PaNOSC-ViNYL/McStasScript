
class SectionReader:
    """
    Super class for the many necessary readers
    """

    def __init__(self, Instr, write_file, product_filename,
                 get_next_line, return_line):
        self.Instr = Instr
        self.write_file = write_file
        self.product_filename = product_filename
        self.instr_name = ""
        self.get_next_line = get_next_line
        self.return_line = return_line

    def set_instr_name(self, name):
        self.instr_name = name

    def _write_to_file(self, string_array):
        """
        In case a py file is being written, this function writes to the
        appropriate file.
        """

        if self.write_file:
            with open(self.product_filename, "a") as product_file:
                for string in string_array:
                    product_file.write(string)

    def _kw_to_string(self, kwargs):
        """
        Used when a dict containing keyword arguments need to be written
        to a string. This string can be used as argument in method call.
        """

        output_string = ""
        for kwarg in kwargs:
            output_string += ", "
            output_string += kwarg + "=" + str(kwargs[kwarg])

        return output_string

    def _split_func(self, *args):
        """
        Returns list of strings seperated by commas that are not
        within open parenthesis.
        """

        string = args[0]
        split_character = args[1]

        if len(args) == 3:
            limit = args[2]
        else:
            limit = -1

        split_positions = []
        parenthesis = 0
        for index in range(len(string)):
            character = string[index]
            if (character == split_character and parenthesis == 0
                    and limit != 0):
                split_positions.append(index)
                limit -= 1
            else:
                if character == "(":
                    parenthesis += 1
                if character == ")":
                    parenthesis -= 1

        split_positions.append(len(string)+1)  # virtual comma at the end

        result = []
        last_position = 0
        for position in split_positions:
            result.append(string[last_position:position])
            last_position = position + 1

        return result

    def _split_func_brack(self, *args):
        """
        Returns list of strings seperated by commas that are not
        within open parenthesis / brackets
        """

        string = args[0]
        split_character = args[1]

        if len(args) == 3:
            limit = args[2]
        else:
            limit = -1

        split_positions = []
        parenthesis = 0
        brackets = 0
        for index in range(len(string)):
            character = string[index]
            if (character == split_character and parenthesis == 0
                    and brackets == 0 and limit != 0):
                split_positions.append(index)
                limit -= 1
            else:
                if character == "(":
                    parenthesis += 1
                if character == ")":
                    parenthesis -= 1
                if character == "{":
                    brackets += 1
                if character == "}":
                    brackets -= 1

        split_positions.append(len(string)+1)  # virtual comma at the end

        result = []
        last_position = 0
        for position in split_positions:
            result.append(string[last_position:position])
            last_position = position + 1

        return result

    def _in_func(self, string, character):
        """
        Returns true of character is in string when excluding occurances
        within parenthesis.
        """

        if len(self._split_func(string, character, 1)) == 2:
            return True
        else:
            return False

    def _in_func_brack(self, string, character):
        """
        Returns true of character is in string when excluding occurances
        within parenthesis and brackets.
        """

        if len(self._split_func_brack(string, character, 1)) == 2:
            return True
        else:
            return False
