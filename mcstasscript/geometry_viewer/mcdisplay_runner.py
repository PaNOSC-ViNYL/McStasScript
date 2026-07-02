
import os
import subprocess


def generate_json(base_executable_name, abs_instr_path, **kwargs):

    if "parameters" in kwargs:
        parameters = kwargs["parameters"]
    else:
        raise ValueError("generate_json needs parameters dict in input")

    parameter_string = ""
    for key, val in parameters.items():
        parameter_string = (parameter_string + " "
                            + str(key)  # parameter name
                            + "="
                            + str(val))  # parameter value

    executable_path = kwargs["executable_path"]
    executable = base_executable_name + "-webgl"

    bin_path = os.path.join(executable_path, executable)

    # Append .bat on windows - or script will not be found...
    if os.name == 'nt':
        bin_path = bin_path + '.bat'

    if not os.path.isfile(bin_path):
        # Take bin in package path into account
        package_path = kwargs["package_path"]
        bin_path = os.path.join(package_path, "bin", executable)

    dir_name_original = kwargs["output_path"] + "_mcdisplay"
    dir_name = dir_name_original
    index = 0
    while os.path.exists(os.path.join(kwargs["input_path"], dir_name)):
        dir_name = dir_name_original + "_" + str(index)
        index += 1

    dir_control = "--dirname " + dir_name + " "

    full_command = ('"' + bin_path + '" '
                    + dir_control
                    + "--nobrowse "
                    + abs_instr_path
                    + " " + parameter_string)

    instrument_folder = os.path.dirname(abs_instr_path)

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
