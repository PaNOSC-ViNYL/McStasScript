from __future__ import annotations

import json
import os

import matplotlib.pyplot as plt

from mcstasscript.geometry_viewer.model.component import ComponentModel
from mcstasscript.geometry_viewer.model.instrument import InstrumentModel
from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer
from mcstasscript.geometry_viewer.mcdisplay import (
    _is_notebook,
    generate_json,
    run_mcdisplay,
    display_mcdisplay_html,
)
from mcstasscript.geometry_viewer.config import intensity_to_color


def _get_renderer(backend: str = "pythreejs", **kwargs):
    if backend == "pythreejs":
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        return PyThreejsRenderer(**kwargs)
    else:
        kwargs.pop("instrument_object", None)
        kwargs.pop("component_colors", None)
        kwargs.pop("component_opacity", None)
        if backend in ("matplotlib", "matplotlib_3d"):
            return MatplotlibRenderer(mode="3d", **kwargs)
        elif backend == "matplotlib_2d":
            return MatplotlibRenderer(mode="2d", **kwargs)
        else:
            raise ValueError(f"Unknown backend: {backend}. Use 'pythreejs', 'matplotlib', or 'matplotlib_2d'.")


def _aggregate_intensity(mon_data, aggregation: str) -> float:
    """Extract a single scalar from monitor data using the chosen aggregation.

    In 0D mode (dimension==0) returns total_I (or total_N for 'ncount').
    In 1D mode, aggregations operate on the axis values (e.g. wavelength)
    weighted by intensity:
      - 'total'    : sum of intensities
      - 'min'      : lowest axis value with non-zero intensity
      - 'max'      : highest axis value with non-zero intensity
      - 'span'     : max - min of axis values with non-zero intensity
      - 'mean'     : intensity-weighted average of axis values
      - 'average'  : same as 'mean'
      - 'median'   : axis value at the median of the cumulative intensity
      - 'ncount'   : sum of Ncount (number of rays) bins
    """
    import numpy as np
    if mon_data.metadata.dimension == 0:
        if aggregation == "ncount":
            total_n = getattr(mon_data.metadata, "total_N", None)
            if total_n is not None:
                return float(total_n)
            return float(np.sum(np.asarray(mon_data.Ncount, dtype=float)))
        return mon_data.metadata.total_I
    if aggregation == "ncount":
        return float(np.sum(np.asarray(mon_data.Ncount, dtype=float)))
    intensity = np.asarray(mon_data.Intensity, dtype=float)
    axis = np.asarray(mon_data.xaxis, dtype=float)
    mask = intensity > 0
    if not np.any(mask):
        return 0.0
    axis_active = axis[mask]
    intensity_active = intensity[mask]
    if aggregation == "max":
        return float(np.max(axis_active))
    elif aggregation == "min":
        return float(np.min(axis_active))
    elif aggregation == "span":
        return float(np.max(axis_active) - np.min(axis_active))
    elif aggregation in ("mean", "average"):
        total = np.sum(intensity_active)
        if total == 0:
            return 0.0
        return float(np.sum(axis_active * intensity_active) / total)
    elif aggregation == "median":
        cum = np.cumsum(intensity_active)
        half = cum[-1] / 2.0
        idx = np.searchsorted(cum, half)
        idx = min(idx, len(axis_active) - 1)
        return float(axis_active[idx])
    else:
        return float(np.sum(intensity))


def view_with_analysis(instrument_object, backend: str = "pythreejs",
                       variable: str | None = None, limits: list | None = None,
                       cmap: str = "inferno", log_scale: bool = True,
                       aggregation: str = "total",
                       width: int = 900, height: int = 600, **kwargs):
    """
    Run intensity diagnostics and visualize components colored by intensity.

    Parameters
    ----------
    instrument_object : McStas_instr or McXtrace_instr
        Instrument to analyze and visualize.
    backend : str
        Rendering backend. Default 'pythreejs'.
    variable : str, optional
        Scan variable for diagnostic run (e.g. 'l', 'x', 't'). If None,
        runs a single simulation and uses total intensity.
    limits : list, optional
        [min, max] limits for the scan variable.
    cmap : str
        Colormap name for intensity coloring. Default 'inferno'.
    log_scale : bool
        If True, use log-scale normalization. Default True.
    aggregation : str
        How to reduce a 1D intensity distribution to a single scalar for
        coloring. In 1D mode, aggregations operate on the axis values
        (e.g. wavelength) weighted by intensity. Options:
        - 'total' (default): sum of all bins (equivalent to total_I in 0D mode)
        - 'min': lowest axis value with non-zero intensity
        - 'max': highest axis value with non-zero intensity
        - 'span': difference between max and min axis value with intensity
        - 'mean' / 'average': intensity-weighted average of axis values
        - 'median': axis value at the median of the cumulative intensity
        - 'ncount': sum of Ncount (number of rays) bins; colorbar labeled 'N rays'
        Ignored when variable is None (0D mode always uses total_I, or total_N for 'ncount').
    width : int
        Width of output widget/figure.
    height : int
        Height of output widget/figure.
    """
    from mcstasscript.instrument_diagnostics.intensity_diagnostics import IntensityDiagnostics
    from mcstasscript.interface.functions import name_search

    if aggregation not in ("total", "max", "min", "mean", "average", "median", "span", "ncount"):
        raise ValueError(
            f"aggregation must be one of 'total', 'max', 'min', 'mean', 'average', 'median', 'span', 'ncount', got {aggregation!r}"
        )

    diag = IntensityDiagnostics(instrument_object)
    if variable is not None:
        diag.run_general(variable=variable, limits=limits)
    else:
        diag.run()

    intensity_map = {}
    for mon_name, comp_name in diag.monitors:
        try:
            mon_data = name_search(mon_name, diag.data)
            intensity_map[comp_name] = _aggregate_intensity(mon_data, aggregation)
        except Exception:
            intensity_map[comp_name] = 0.0

    colorbar_label = None
    if diag.monitors:
        first_mon_name = diag.monitors[0][0]
        try:
            first_mon_data = name_search(first_mon_name, diag.data)
            source_name = instrument_object.component_list[0].name
            intensity_map[source_name] = _aggregate_intensity(first_mon_data, aggregation)
            if aggregation == "ncount":
                colorbar_label = "N rays"
            elif diag.data_dim == 1 and first_mon_data.metadata.xlabel:
                colorbar_label = first_mon_data.metadata.xlabel
            else:
                colorbar_label = "Intensity [n/s]"
        except Exception:
            pass

    return view(
        instrument_object,
        backend=backend,
        intensity_map=intensity_map,
        cmap=cmap,
        log_scale=log_scale,
        colorbar_label=colorbar_label,
        width=width,
        height=height,
        **kwargs,
    )


def view_with_guess(instrument_object, backend: str = "pythreejs",
                      component_colors: dict[str, str] | None = None,
                      component_opacity: dict[str, float] | None = None, **kwargs):
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
        instrument_model.add_model(component_model)

    num_components = len(instrument_model.component_models)
    kwargs.setdefault("num_components", num_components)
    intensity_map = kwargs.get("intensity_map")
    if intensity_map is not None:
        kwargs["colormode"] = "intensity"
    else:
        kwargs.setdefault("colormode", "default")

    kwargs_for_renderer = dict(kwargs)
    kwargs_for_renderer["instrument_object"] = instrument_object
    kwargs_for_renderer["component_colors"] = component_colors
    kwargs_for_renderer["component_opacity"] = component_opacity
    renderer = _get_renderer(backend, **kwargs_for_renderer)

    from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

    all_children = []
    for index, component_model in enumerate(instrument_model.component_models):
        if isinstance(renderer, PyThreejsRenderer):
            renderer.register_component(component_model)
        all_children.extend(renderer.render_component(component_model, component_index=index))
        renderer.next_component()

    scene = renderer.make_scene(all_children, width=width, height=height, **kwargs)

    if isinstance(renderer, PyThreejsRenderer):
        import ipywidgets as ipw
        navigator = renderer.create_component_navigator(scene)
        colormode_selector = renderer.create_colormode_selector()
        custom_colors_checkbox = renderer.create_custom_colors_checkbox()
        custom_opacities_checkbox = renderer.create_custom_opacities_checkbox()
        intensity_controls = renderer.create_intensity_controls()
        colorbar = renderer.create_colorbar()
        controls = [navigator, colormode_selector]
        if custom_colors_checkbox is not None:
            controls.append(custom_colors_checkbox)
        if custom_opacities_checkbox is not None:
            controls.append(custom_opacities_checkbox)
        controls.extend([intensity_controls, ipw.HBox([scene, colorbar])])
        return ipw.VBox(controls)

    if isinstance(renderer, MatplotlibRenderer):
        plt.show()
        return None

    return scene


def view_with_json(instrument_object, json_dict, backend: str = "pythreejs",
                     index_min: int | None = None, index_max: int | None = None,
                     component_colors: dict[str, str] | None = None,
                     component_opacity: dict[str, float] | None = None, **kwargs):
    """
    Plots instrument geometry with json input from mcdisplay-webgl.
    """
    width = kwargs.pop("width", 900)
    height = kwargs.pop("height", 600)

    instrument_model = InstrumentModel(instrument_object=instrument_object, json_dict=json_dict)

    if index_min is None:
        index_min = 0
    if index_max is None:
        index_max = len(instrument_model.component_models)

    num_components = index_max - index_min
    kwargs.setdefault("num_components", num_components)

    intensity_map = kwargs.get("intensity_map")
    if intensity_map is not None:
        kwargs["colormode"] = "intensity"

    kwargs_for_renderer = dict(kwargs)
    kwargs_for_renderer["instrument_object"] = instrument_object
    kwargs_for_renderer["component_colors"] = component_colors
    kwargs_for_renderer["component_opacity"] = component_opacity
    renderer = _get_renderer(backend, **kwargs_for_renderer)

    from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer

    all_children = []
    for index, component_model in enumerate(instrument_model.component_models):
        if index_min <= index < index_max:
            if isinstance(renderer, PyThreejsRenderer):
                renderer.register_component(component_model)
            all_children.extend(renderer.render_component(component_model, component_index=index))
            renderer.next_component()

    scene = renderer.make_scene(all_children, width=width, height=height, **kwargs)

    if isinstance(renderer, PyThreejsRenderer):
        import ipywidgets as ipw
        navigator = renderer.create_component_navigator(scene)
        colormode_selector = renderer.create_colormode_selector()
        custom_colors_checkbox = renderer.create_custom_colors_checkbox()
        custom_opacities_checkbox = renderer.create_custom_opacities_checkbox()
        intensity_controls = renderer.create_intensity_controls()
        colorbar = renderer.create_colorbar()
        controls = [navigator, colormode_selector]
        if custom_colors_checkbox is not None:
            controls.append(custom_colors_checkbox)
        if custom_opacities_checkbox is not None:
            controls.append(custom_opacities_checkbox)
        controls.extend([intensity_controls, ipw.HBox([scene, colorbar])])
        return ipw.VBox(controls)

    if isinstance(renderer, MatplotlibRenderer):
        plt.show()
        return None

    return scene


def view(instrument_object, backend: str = "pythreejs",
          allow_guess: bool = False,
          json_dict: dict | None = None, json_file: str | None = None,
          index_min: int | None = None, index_max: int | None = None,
          width: int = 900, height: int = 600,
          intensity_map: dict | None = None,
          cmap: str = "inferno",
          log_scale: bool = True,
          colorbar_label: str | None = None,
          component_colors: dict[str, str] | None = None,
          component_opacity: dict[str, float] | None = None,
          **kwargs):
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
    intensity_map : dict, optional
        Mapping of component name to intensity value. When provided,
        components are colored by intensity using the specified colormap.
    cmap : str
        Colormap name for intensity coloring. Default 'inferno'.
    log_scale : bool
        If True, use log-scale normalization for intensity coloring.
        Default True.
    component_colors : dict, optional
        Mapping of component name to hex color string. When provided with
        the 'pythreejs' backend, adds a "Custom colors" checkbox to the
        widget that, when checked, overrides the current colorscheme for
        the specified components. Ignored for other backends.
    component_opacity : dict, optional
        Mapping of component name to opacity value (float in [0.0, 1.0]).
        When provided with the 'pythreejs' backend, adds a "Custom opacity"
        checkbox to the widget that, when checked, overrides the current
        opacity for the specified components. Ignored for other backends.
    projection : str
        Axis projection for matplotlib_2d backend. One of 'xy', 'zx', 'zy'.
        Default 'zx' (matches McStas beam-layout convention). Ignored for 3D backends.
    colormode : str
        Color assignment mode. Options:
        - 'default' (default): cycle through a fixed palette of colors
        - 'component': map component index to a viridis colorscale
        - 'intensity': color by neutron intensity (requires intensity_map)
    """

    # --- mcdisplay HTML backends ---
    if backend in ("webgl", "webgl-classic", "window"):
        if backend == "webgl" and _is_notebook():
            print("Starting mcdisplay-webgl (Vite dev server)...")
            print("A browser tab will open with the visualization.")
            print("Press the Stop button in the notebook toolbar to return here.")
        html_path = run_mcdisplay(instrument_object, format=backend)
        if backend == "window":
            return None
        if html_path is None:
            raise RuntimeError(f"mcdisplay run with format '{backend}' failed.")
        if backend == "webgl":
            # mcdisplay-webgl starts a Vite dev server and opens the browser
            # itself with the correct URL (http://localhost:5173).
            return None
        return display_mcdisplay_html(html_path, width=width, height=height)

    # --- guess-only backend ---
    if backend == "guess":
        renderer = kwargs.pop("renderer", "pythreejs")
        return view_with_guess(instrument_object, backend=renderer, width=width, height=height,
                                component_colors=component_colors,
                                component_opacity=component_opacity, **kwargs)

    # --- Python rendering backends (pythreejs, matplotlib, matplotlib_2d) ---
    if allow_guess:
        try:
            return view_with_guess(instrument_object, backend=backend, width=width, height=height,
                                    component_colors=component_colors,
                                    component_opacity=component_opacity, **kwargs)
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
        intensity_map=intensity_map,
        cmap=cmap,
        log_scale=log_scale,
        colorbar_label=colorbar_label,
        component_colors=component_colors,
        component_opacity=component_opacity,
        **kwargs,
    )
