import os
import subprocess
import webbrowser
import warnings


def _extract_params(instrument_object):
    """Validate and collect instrument parameters as a dict."""
    parameters = {}
    for parameter in instrument_object.parameters:
        if parameter.value is None:
            raise RuntimeError(
                f"Parameter value not set for parameter: '{parameter.name}' "
                f"set with set_parameters."
            )
        parameters[parameter.name] = parameter.value
    return parameters


def _find_executable(base_name, run_settings):
    """Discover the mcdisplay binary path."""
    executable_path = run_settings.get("executable_path", "")
    bin_path = os.path.join(executable_path, base_name)

    if os.name == "nt":
        bin_path = bin_path + ".bat"

    if not os.path.isfile(bin_path):
        package_path = run_settings.get("package_path", "")
        bin_path = os.path.join(package_path, "bin", base_name)

    return bin_path


def _create_output_dir(name, input_path):
    """Create a unique output directory for mcdisplay output."""
    dir_name_original = name + "_mcdisplay"
    dir_name = dir_name_original
    index = 0
    while os.path.exists(os.path.join(input_path, dir_name)):
        dir_name = dir_name_original + "_" + str(index)
        index += 1
    return dir_name


def _is_notebook():
    """Detect whether running inside a Jupyter notebook."""
    try:
        shell = get_ipython().__class__.__name__
        return shell == "ZMQInteractiveShell"
    except Exception:
        return False


def _get_format_executable(package_name, format):
    """Map format string to the mcdisplay executable suffix."""
    base = "mxdisplay" if package_name == "McXtrace" else "mcdisplay"
    if format == "webgl":
        return base + "-webgl"
    elif format == "webgl-classic":
        return base + "-webgl-classic"
    elif format == "window":
        return base + "-pyqtgraph"
    else:
        raise ValueError(
            f"Did not recognize given format '{format}', "
            f"must be webgl-classic, webgl or window."
        )


def run_mcdisplay(instrument_object, format="webgl-classic", nobrowse=None):
    """
    Run mcdisplay to generate visualization output.

    Parameters
    ----------
    instrument_object : McStas_instr or McXtrace_instr
        Instrument to visualize.
    format : str
        Display format: 'webgl', 'webgl-classic', or 'window'.
    nobrowse : bool or None
        If True, don't open browser. If None, auto-detect notebook.

    Returns
    -------
    html_path : str or None
        Path to generated index.html (for webgl formats), or None for 'window'.
    """
    parameters = _extract_params(instrument_object)
    parameter_string = " ".join(f"{k}={v}" for k, v in parameters.items())

    base_executable = _get_format_executable(
        instrument_object.package_name, format
    )
    bin_path = _find_executable(base_executable, instrument_object._run_settings)
    dir_name = _create_output_dir(instrument_object.name, instrument_object.input_path)

    instrument_object.write_full_instrument()
    instr_path = os.path.join(
        instrument_object.input_path,
        instrument_object.name + ".instr",
    )
    instr_path = os.path.abspath(instr_path)

    notebook = _is_notebook()
    if nobrowse is None:
        # webgl starts a Vite dev server — mcdisplay must open the browser
        # itself since it knows the correct URL (http://localhost:5173).
        nobrowse = notebook and format not in ("window", "webgl")

    options = ""
    if nobrowse:
        options = "--nobrowse "

    dir_control = "--dirname " + dir_name + " "
    full_command = (
        '"' + bin_path + '" '
        + dir_control
        + options
        + instr_path
        + " " + parameter_string
    )

    process = subprocess.run(
        full_command, shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        cwd=instrument_object.input_path,
    )

    if format == "window":
        if process.returncode != 0:
            print(process.stderr)
        return None

    html_path = os.path.join(
        instrument_object.input_path, dir_name, "index.html"
    )

    if process.returncode != 0 or not os.path.exists(html_path):
        print(process.stderr)
        print(process.stdout)
        print("")
        print("mcdisplay run failed.")
        return None

    return html_path


def display_mcdisplay_html(html_path, width=800, height=450):
    """
    Display mcdisplay HTML output.

    In a notebook, returns an IFrame widget. In a terminal, opens the
    browser. Used for webgl-classic (static HTML that embeds correctly).

    Parameters
    ----------
    html_path : str
        Path to the generated index.html file.
    width : int
        Width of IFrame (notebook only).
    height : int
        Height of IFrame (notebook only).

    Returns
    -------
    IFrame or None
        IFrame widget in notebook, None in terminal.
    """
    if not os.path.exists(html_path):
        print("HTML file not found:", html_path)
        return None

    notebook = _is_notebook()
    if notebook:
        from IPython.display import IFrame
        return IFrame(src=html_path, width=width, height=height)
    else:
        abs_path = os.path.abspath(html_path)
        webbrowser.open("file://" + abs_path)
        return None


def generate_json(instrument_object):
    """
    Run mcdisplay-webgl to generate instrument.json.

    Kept for backward compatibility. Internally calls run_mcdisplay.

    Returns
    -------
    dir_name : str or None
        Path to the output directory containing instrument.json.
    """
    html_path = run_mcdisplay(instrument_object, format="webgl", nobrowse=True)
    if html_path is None:
        return None
    return os.path.dirname(html_path)
