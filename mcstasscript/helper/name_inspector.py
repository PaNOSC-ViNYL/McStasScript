def find_python_variable_name(error_text, n_levels=1):
    """
    Finds call in stack n_levels above and gets variable name

    This function is used to avoid having to manually specify a name
    in the method or function inputs. For example with a parameters:

    wavelength = instrument.add_parameter("wavelength", value=3)

    can be equivalent to:

    wavelength = instrument.add_parameter(value=3)

    When this function is used to deduct the appropriate name.
    The n_levels is the number of function calls between the user
    call and this function, for each level of nesting add another
    level. An error_text should be given for cases where it was not
    possible to extract the variable name.
    """

    import inspect

    stack = inspect.stack()
    calling_string = ' '.join(stack[n_levels][4])
    if '=' not in calling_string:
        raise NameError(error_text)
    return calling_string.split('=')[0].strip()