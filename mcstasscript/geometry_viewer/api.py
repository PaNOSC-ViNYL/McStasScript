import json
import os

from mcstasscript.geometry_viewer.model.component import ComponentModel
from mcstasscript.geometry_viewer.model.instrument import InstrumentModel
from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
from mcstasscript.geometry_viewer.mcdisplay import (
    generate_json,
    run_mcdisplay,
    display_mcdisplay_html,
)


def _get_renderer(backend: str = "pythreejs", **kwargs):
    if backend == "pythreejs":
        return PyThreejsRenderer(**kwargs)
    elif backend in ("matplotlib", "matplotlib_3d"):
        return MatplotlibRenderer(mode="3d", **kwargs)
    elif backend == "matplotlib_2d":
        return MatplotlibRenderer(mode="2d", **kwargs)
    else:
        raise ValueError(f"Unknown backend: {backend}. Use 'pythreejs', 'matplotlib', or 'matplotlib_2d'.")


def view_with_guess(instrument_object, backend: str = "pythreejs", **kwargs):
    """
    Plots instrument geometry with best guesses of geometry.

    Fails if location of a component cannot be determined:
    - If non-trivial declared variables used in AT / ROTATED
    - If non-trivial calculations are made in AT / ROTATED
    """
    width = kwargs.pop("width", 900)
    height = kwargs.pop("height", 600)

    instrument_model = InstrumentModel()
    for component in instrument_object.component_list:
        component_model = ComponentModel(component)
        component_model.guess_geometry_from_comp_object()

    renderer = _get_renderer(backend, **kwargs)
    return renderer.render_instrument(instrument_model, width=width, height=height, **kwargs)


def view_with_json(instrument_object, json_dict, backend: str = "pythreejs",
                   index_min: int | None = None, index_max: int | None = None, **kwargs):
    """
    Plots instrument geometry with json input from mcdisplay-webgl.
    """
    width = kwargs.pop("width", 900)
    height = kwargs.pop("height", 600)

    instrument_model = InstrumentModel(instrument_object=instrument_object, json_dict=json_dict)

    renderer = _get_renderer(backend, **kwargs)

    if index_min is None:
        index_min = 0
    if index_max is None:
        index_max = len(instrument_model.component_models)

    all_children = []
    for index, component_model in enumerate(instrument_model.component_models):
        if index_min <= index < index_max:
            if isinstance(renderer, PyThreejsRenderer):
                renderer.register_component(component_model)
                renderer.next_component()
            all_children.extend(renderer.render_component(component_model))

    scene = renderer.make_scene(all_children, width=width, height=height, **kwargs)

    if isinstance(renderer, PyThreejsRenderer):
        import ipywidgets as ipw
        navigator = renderer.create_component_navigator(scene)
        return ipw.VBox([navigator, scene])

    return scene


def view(instrument_object, backend: str = "pythreejs",
         allow_guess: bool = False,
         json_dict: dict | None = None, json_file: str | None = None,
         index_min: int | None = None, index_max: int | None = None,
         width: int = 900, height: int = 600, **kwargs):
    """
    Plots instrument geometry.

    Parameters
    ----------
    instrument_object : McStas_instr or McXtrace_instr
        Instrument to visualize.
    backend : str
        Rendering backend. Options:
        - 'pythreejs' (default): generate JSON via mcdisplay-webgl, render as pythreejs widget
        - 'matplotlib' / 'matplotlib_2d': generate JSON, render as matplotlib figure
        - 'webgl': generate HTML via mcdisplay-webgl, display as IFrame or browser
        - 'webgl-classic': generate HTML via mcdisplay-webgl-classic, display as IFrame or browser
        - 'window': launch mcdisplay-pyqtgraph native window
        - 'guess': skip mcdisplay, guess geometry from component parameters
    allow_guess : bool
        If True, try geometry guess first, fall back to mcdisplay JSON on error.
        Default False.
    json_dict : dict, optional
        Pre-loaded instrument.json dict (skips mcdisplay generation).
    json_file : str, optional
        Path to instrument.json file (skips mcdisplay generation).
    index_min : int, optional
        First component index to render (for JSON-based backends).
    index_max : int, optional
        Last component index to render (for JSON-based backends).
    width : int
        Width of output widget/figure.
    height : int
        Height of output widget/figure.
    """

    # --- mcdisplay HTML backends ---
    if backend in ("webgl", "webgl-classic", "window"):
        html_path = run_mcdisplay(instrument_object, format=backend)
        if html_path is None:
            raise RuntimeError(f"mcdisplay run with format '{backend}' failed.")
        return display_mcdisplay_html(html_path, width=width, height=height)

    # --- guess-only backend ---
    if backend == "guess":
        renderer = kwargs.pop("renderer", "pythreejs")
        return view_with_guess(instrument_object, backend=renderer, width=width, height=height, **kwargs)

    # --- Python rendering backends (pythreejs, matplotlib, matplotlib_2d) ---
    if allow_guess:
        try:
            return view_with_guess(instrument_object, backend=backend, width=width, height=height, **kwargs)
        except Exception:
            pass

    # Load or generate JSON data
    if json_dict is None:
        if json_file is None:
            json_folder = generate_json(instrument_object)
            if json_folder is None:
                raise RuntimeError("Generating json file via mcdisplay-webgl failed.")
            json_file = os.path.join(json_folder, "instrument.json")

        with open(json_file, "r") as f:
            json_dict = json.load(f)

    return view_with_json(
        instrument_object, json_dict,
        backend=backend,
        index_min=index_min,
        index_max=index_max,
        width=width,
        height=height,
        **kwargs,
    )
