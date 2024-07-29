def has_component(instrument, component_name=None, component_type=None):
    """
    Checks if given instrument has a component with given name and type

    instrument : McStasScript instrument object

    component_name : (str) name of component

    component_type : (str) type of component, for example Arm
    """
    if component_name is None and component_type is None:
        raise ValueError("Specify component_name, component_type or both.")

    # Run through components in instrument
    for comp in instrument.component_list:
        if component_name is not None:
            if comp.name != component_name:
                continue

        if component_type is not None:
            if comp.component_name != component_type:
                continue

        # Found case where both component name and type matches
        return True

    # Did not find any such component
    return False


def has_parameter(instrument, parameter_name, parameter_type=None):
    """
    Checks if instrument have parameter with given name and type

    instrument : McStasScript instrument object

    parameter_name : (str) Name of parameter

    parameter_type : (str) Type of parameter, "" treated as double
    """
    if parameter_name is None and parameter_type is None:
        raise ValueError("Specify parameter_name, parameter_type or both.")

    parameter_dict = instrument.parameters.parameters

    if parameter_name not in parameter_dict:
        return False

    if parameter_type is not None:
        found_type = parameter_dict[parameter_name].type

        if parameter_type == "double" and found_type == "":
            # Default McStas type is double
            return True

        if found_type != parameter_type:
            return False

    return True


def all_parameters_set(instrument):
    """
    Checks if all parameters of given instrument have default values

    instrument : McStasScript instrument object
    """
    parameter_dict = instrument.parameters.parameters

    for par_object in parameter_dict.values():
        if par_object.value is None:
            return False

    return True