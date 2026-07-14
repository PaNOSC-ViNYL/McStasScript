
import os
import subprocess
import copy


def generate_json(instrument_object):

    if instrument_object.package_name == "McXtrace":
        executable = "mxdisplay"
    else:
        executable = "mcdisplay"

    instr_path = os.path.join(instrument_object.input_path,
                              instrument_object.name + ".instr")

    instr_path = os.path.abspath(instr_path)

    parameters = {}
    for parameter in instrument_object.parameters:
        if parameter.value is None:
            raise RuntimeError("Parameter value not set for parameter: '" + parameter.name
                               + "' set with set_parameters.")

        parameters[parameter.name] = parameter.value

    options = copy.deepcopy(instrument_object._run_settings)
    options["parameters"] = parameters
    options["output_path"] = instrument_object.output_path
    options["input_path"] = instrument_object.input_path

    instrument_object.write_full_instrument()

    if "parameters" in options:
        parameters = options["parameters"]
    else:
        raise ValueError("generate_json needs parameters dict in input")

    parameter_string = ""
    for key, val in parameters.items():
        parameter_string = (parameter_string + " "
                            + str(key)  # parameter name
                            + "="
                            + str(val))  # parameter value

    executable_path = options["executable_path"]
    executable = executable + "-webgl"

    bin_path = os.path.join(executable_path, executable)

    # Append .bat on windows - or script will not be found...
    if os.name == 'nt':
        bin_path = bin_path + '.bat'

    if not os.path.isfile(bin_path):
        # Take bin in package path into account
        package_path = options["package_path"]
        bin_path = os.path.join(package_path, "bin", executable)

    dir_name_original = options["output_path"] + "_mcdisplay"
    dir_name = os.path.abspath(dir_name_original)
    index = 0
    while os.path.exists(dir_name):
        dir_name = dir_name_original + "_" + str(index)
        index += 1
    dir_control = "--dirname " + dir_name + " "

    full_command = ('"' + bin_path + '" '
                    + dir_control
                    + "--nobrowse "
                    + instr_path
                    + " " + parameter_string)

    instrument_folder = os.path.dirname(instr_path)

    process = subprocess.run(full_command, shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             universal_newlines=True,
                             cwd=instrument_folder)

    if process.returncode != 0:
        print("Simulation signaled that it failed by non-zero return code")
        print(process.stdout)

    if os.path.isdir(dir_name):
        return dir_name
    else:
        print("Didn't find created data")
