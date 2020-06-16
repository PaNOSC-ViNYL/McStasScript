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

def to_number(input):
    """
    Converts input to the appropriate python number type
    """

    if isinstance(input, int) or isinstance(input, float):
        return input

    try:
        return int(input)
    except:
        try:
            return float(input)
        except:
            pass

    return None

class LegalTypes:
    all_c_types = ["int", "double", "char", "string"]
    py_types = [int, float, str]


class LegalAssignments:
    var_from_py = {"int": int,
                   "double": (int, float),
                   "char": str,
                   "string": str}

    py_to_var = {int: ["int", "double"],
                 float: ["double"],
                 str: ["char", "string"]}

    var_to_var = {"int": ["int"],
                  "double": ["double"],
                  "char": ["char", "string"],
                  "string": ["string"]}
