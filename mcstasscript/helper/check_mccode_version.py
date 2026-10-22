import os
import re
import subprocess

def _parse_version(output):
    output = output.decode("utf-8")
    output = output.split(" (", 1)[0]
    output = output.split("version", 1)[1].strip()
    parts = output.split(".")

    def _int_prefix(part):
        match = re.match(r"\d+", part)
        return int(match.group()) if match else 0

    major = _int_prefix(parts[0])
    minor = _int_prefix(parts[1]) if len(parts) > 1 else 0
    patch = parts[2] if len(parts) > 2 else "0"
    return major, minor, patch


def _check_version(mcstas_bin_path, executable):
    command = os.path.join(mcstas_bin_path, executable)
    output = subprocess.check_output([command, "-v"])
    return _parse_version(output)


def check_mcstas_version(mcstas_bin_path):
    """
    Check the installed McStas version.

    Returns
    -------
    tuple
        Major and minor versions as integers, followed by the raw patch
        version string.
    """
    return _check_version(mcstas_bin_path, "mcstas")


def check_mcxtrace_version(mcstas_bin_path):
    """
    Check the installed McXtrace version.

    Returns
    -------
    tuple
        Major and minor versions as integers, followed by the raw patch
        version string.
    """
    return _check_version(mcstas_bin_path, "mcxtrace")
