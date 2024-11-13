class SearchStatement:
    def __init__(self, statement, SHELL=False):
        """
        A McStas search statement, used either in instrument before component
        """

        self.statement = str(statement)
        self.SHELL = SHELL

    def make_string(self):
        """
        Generates the search string
        """
        if self.SHELL:
            shell_part = "SHELL "
        else:
            shell_part = ""

        if self.statement[0] != '"' and self.statement[-1] != '"':
            self.statement = '"' + self.statement + '"'

        return f'SEARCH {shell_part}{self.statement}'

    def write(self, fo):
        """
        Writes search string to file
        """
        fo.write(self.make_string() + "\n")

    def __repr__(self):
        """
        Prints search string
        """
        return self.make_string()


class SearchStatementList:
    def __init__(self):
        """
        Keeps a number of search statements together
        """
        self.statements = []

    def add_statement(self, statement):
        """
        Add new search statement
        """
        if not isinstance(statement, SearchStatement):
            raise ValueError("SearchStatementList only supports adding SearchStatement objects.")

        self.statements.append(statement)

    def clear(self):
        """
        Clear all search statements
        """
        self.statements = []

    def write(self, fo):
        """
        Write search statements to a file
        """
        for statement in self.statements:
            statement.write(fo)

    def make_string(self):
        """
        Makes string with all search statements
        """
        string = ""
        for statement in self.statements:
            string += statement.make_string() + "\n"

        return string

    def __repr__(self):
        """
        Show search statements with print
        """
        if len(self.statements) == 0:
            return "No Search statements yet"

        string = "List of SEARCH statements: \n"
        for statement in self.statements:
            string += "  " + statement.make_string() + "\n"

        return string