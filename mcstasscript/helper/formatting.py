import re

class bcolors:
    """
    Helper class that contains formatting classes and functions
    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def is_legal_parameter(name):
    """
    Function that returns true if the given name can be used as a
    parameter in the c programming language.
    """
    # List of C reserved keywords
    reserved_keywords = [
        "auto", "break", "case", "char", "const", "continue", "default", "do",
        "double", "else", "enum", "extern", "float", "for", "goto", "if",
        "inline", "int", "long", "register", "restrict", "return", "short",
        "signed", "sizeof", "static", "struct", "switch", "typedef", "union",
        "unsigned", "void", "volatile", "while", "_Bool", "_Complex", "_Imaginary"
    ]

    # Regular expression pattern for a legal C variable name
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'

    # Check if the input string matches the pattern and is not a reserved keyword
    return re.match(pattern, name) and name not in reserved_keywords


def is_legal_filename(name):
    """
    Function that returns true if the given name can be used as a
    filename
    """

    if name == "":
        return False

    if " " in name:
        return False

    if "/" in name:
        return False

    if "\\" in name:
        return False

    return True
