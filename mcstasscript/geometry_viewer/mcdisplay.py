import os
import subprocess
import webbrowser


class McdisplayError(RuntimeError):
    """Raised when mcdisplay cannot produce the requested visualization."""

    def __init__(self, message, returncode=None, stdout="", stderr="", command=None):
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.command = command


def _extract_params(instrument_object):
    """Validate and collect instrument parameters."""
    parameters = []
    for parameter in instrument_object.parameters:
        if parameter.value is None:
            raise RuntimeError(
                f"Parameter value not set for parameter: '{parameter.name}' "
                f"set with set_parameters."
            )
        parameters.append(parameter)
    return parameters


def _format_parameter(parameter):
    """Format an instrument parameter for mcdisplay's argv interface."""
    value = parameter.value
    if (parameter.type == "string" and isinstance(value, str)
            and len(value) >= 2 and value[0] == value[-1] == '"'):
        # The quotes are needed in the generated C declaration, but are not
        # shell syntax when the value is passed through an argv list.
        value = value[1:-1]
    return f"{parameter.name}={value}"


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


def _create_output_path(output_path):
    """Return a fresh output path, incrementing an existing path as needed."""
    output_path = os.path.abspath(os.fspath(output_path))
    output_parent = os.path.dirname(output_path)
    if output_parent:
        os.makedirs(output_parent, exist_ok=True)

    candidate = output_path
    index = 0
    while os.path.exists(candidate):
        candidate = output_path + "_" + str(index)
        index += 1
    return candidate


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


def run_mcdisplay(instrument_object, format="webgl-classic", nobrowse=None,
                  output_path=None):
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
    output_path : str, optional
        Output directory for generated visualization files. If omitted, an
        explicitly configured instrument output path is used; otherwise the
        legacy ``<input_path>/<instrument>_mcdisplay`` location is retained.

    Returns
    -------
    html_path : str or None
        Path to generated index.html (for webgl formats), or None for 'window'.
    """
    parameters = _extract_params(instrument_object)
    base_executable = _get_format_executable(
        instrument_object.package_name, format
    )
    bin_path = _find_executable(base_executable, instrument_object._run_settings)
    configured_output_path = output_path
    if configured_output_path is None:
        configured_output_path = getattr(instrument_object, "_run_settings", {}).get("output_path")

    if configured_output_path is None:
        dir_name = _create_output_dir(instrument_object.name, instrument_object.input_path)
        dirname_argument = dir_name
        html_path = os.path.join(instrument_object.input_path, dir_name, "index.html")
    else:
        dir_name = _create_output_path(configured_output_path)
        dirname_argument = os.path.relpath(
            dir_name,
            start=os.path.abspath(instrument_object.input_path),
        )
        html_path = os.path.join(dir_name, "index.html")

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

    command = [bin_path, "--dirname", dirname_argument]
    if nobrowse:
        command.append("--nobrowse")
    command.append(instr_path)
    command.extend(_format_parameter(parameter) for parameter in parameters)

    try:
        process = subprocess.run(
            command, shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            cwd=instrument_object.input_path,
        )
    except OSError as exc:
        raise McdisplayError(
            f"Could not start mcdisplay: {exc}", command=command,
        ) from exc

    if format == "window":
        # Closing the GUI can produce a non-zero Qt exit status and verbose
        # shutdown output. The process was successfully started, so do not
        # turn normal window close behavior into a Python error.
        return None

    if process.returncode != 0:
        print(process.stderr or "")
        print(process.stdout or "")
        raise McdisplayError(
            f"mcdisplay failed with return code {process.returncode}",
            returncode=process.returncode,
            stdout=process.stdout or "",
            stderr=process.stderr or "",
            command=command,
        )

    if not os.path.exists(html_path):
        raise McdisplayError(
            f"mcdisplay completed successfully but did not create {html_path}",
            returncode=process.returncode,
            stdout=process.stdout or "",
            stderr=process.stderr or "",
            command=command,
        )

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
        iframe_src = html_path
        if os.path.isabs(iframe_src):
            iframe_src = os.path.relpath(iframe_src, start=os.getcwd())
        iframe_src = iframe_src.replace(os.sep, "/")
        return IFrame(
            src=iframe_src,
            width=width,
            height=height,
        )
    else:
        abs_path = os.path.abspath(html_path)
        webbrowser.open("file://" + abs_path)
        return None


def generate_json(instrument_object, output_path=None):
    """
    Run mcdisplay-webgl to generate instrument.json.

    Kept for backward compatibility. Internally calls run_mcdisplay.

    Returns
    -------
    dir_name : str or None
        Path to the output directory containing instrument.json.
    """
    html_path = run_mcdisplay(
        instrument_object,
        format="webgl",
        nobrowse=True,
        output_path=output_path,
    )
    if html_path is None:
        return None
    return os.path.dirname(html_path)
