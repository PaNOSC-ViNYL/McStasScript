from libpyvinyl.Parameters.Parameter import Parameter
from mcstasscript.helper.mcstas_objects import DeclareVariable

def component_description(component):
    """
    Returns string of information about the component

    Includes information on required parameters if they are not yet
    specified. Information on the components are added when the
    class is used as a superclass for classes describing each
    McStas component. Uses mathtext for bold and italics.
    """
    string = ""

    if len(component.c_code_before) > 1:
        string += component.c_code_before + "\n"
    if len(component.comment) > 1:
        string += "// " + component.comment + "\n"
    if component.SPLIT != 0:
        string += "SPLIT " + str(component.SPLIT) + " "
    string += "COMPONENT " + str(component.name)
    string += " = $\\bf{" + str(component.component_name).replace("_", "\\_") + "}$\n"
    for key in component.parameter_names:
        val = getattr(component, key)
        parameter_name = key
        if val is not None:
            unit = ""
            if key in component.parameter_units:
                unit = "[" + component.parameter_units[key] + "]"
            if isinstance(val, Parameter):
                val_string = val.name
            elif isinstance(val, DeclareVariable):
                val_string = val.name
            else:
                val_string = str(val)

            value = "$\\bf{" + val_string.replace("_", "\\_").replace('\"', "''").replace('"', "\''") + "}$"
            string += "  $\\bf{" + parameter_name.replace("_", "\\_") + "}$"
            string += " = " + value + " " + unit + "\n"
        else:
            if component.parameter_defaults[key] is None:
                string += "  $\\bf{" + parameter_name.replace("_", "\\_") + "}$"
                string += " : $\\bf{Required\\ parameter\\ not\\ yet\\ specified}$\n"

    if not component.WHEN == "":
        string += component.WHEN + "\n"

    string += "AT " + str(component.AT_data)
    if component.AT_reference is None:
        string += " $\\it{ABSOLUTE}$\n"
    else:
        string += " RELATIVE $\\it{" + component.AT_reference.replace("_", "\\_") + "}$\n"

    if component.ROTATED_specified:
        string += "ROTATED " + str(component.ROTATED_data)
        if component.ROTATED_reference is None:
            string += " $\\it{ABSOLUTE}$\n"
        else:
            string += " $\\it{" + component.ROTATED_reference.replace("_", "\\_") + "}$\n"

    if not component.GROUP == "":
        string += "GROUP " + component.GROUP + "\n"
    if not component.EXTEND == "":
        string += "EXTEND %{" + "\n"
        string += component.EXTEND + "%}" + "\n"
    if not component.JUMP == "":
        string += "JUMP " + component.JUMP + "\n"
    if len(component.c_code_after) > 1:
        string += component.c_code_after + "\n"

    return string.strip()
