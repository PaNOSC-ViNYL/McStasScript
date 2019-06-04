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

    if name is "":
        return False

    if " " in name:
        return False

    if "." in name:
        return False

    if not name[0].isalpha():
        return False

    return True


def is_legal_filename(name):
    """
    Function that returns true if the given name can be used as a
    filename
    """

    if name is "":
        return False

    if " " in name:
        return False

    if "/" in name:
        return False

    if "\\" in name:
        return False

    return True
