import os
import subprocess

def check_mcstas_major_version(mcstas_bin_path):
    """
    Checks installed McStas version
    """
    mcstas_command = os.path.join(mcstas_bin_path, "mcstas")
    output = subprocess.check_output([mcstas_command, "-v"])

    output = output.decode("utf-8")
    output = output.split(" (", 1)[0]
    output = output.split("version", 1)[1]
    major_version = output.split(".", 1)[0]

    return int(major_version)

def check_mcxtrace_major_version(mcstas_bin_path):
    """
    Checks installed McXtrace version
    """
    mcstas_command = os.path.join(mcstas_bin_path, "mcxtrace")
    output = subprocess.check_output([mcstas_command, "-v"])

    output = output.decode("utf-8")
    output = output.split(" (", 1)[0]
    output = output.split("version", 1)[1]
    major_version = output.split(".", 1)[0]

    return int(major_version)