import sys
import os

class HiddenPrints:
    """
    Environment which suppress prints
    """
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout


def parameter_has_default(parameter):
    """
    Checks if ParameterVariable has a default value, returns bool

    Parameters
    ----------

    parameter: ParameterVariable
        The parameter to check for default value
    """
    if parameter.value is None:
        return False
    return True


def get_parameter_default(parameter):
    """
    Returns the default value of a parameter

    Parameters
    ----------

    parameter: ParameterVariable
        The parameter for which the default value is returned
    """
    if parameter.value is not None:
        if parameter.type == "string":
            return parameter.value
        elif parameter.type == "double" or parameter.type == "":
            return float(parameter.value)
        elif parameter.type == "int":
            return int(parameter.value)
        else:
            raise RuntimeError("Unknown parameter type '"
                               + parameter.type + "' of par named '"
                               + parameter.name + "'.")

    return None
