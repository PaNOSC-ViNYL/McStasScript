# geometry_viewer — Summary

## Architecture

The module implements a backend-agnostic instrument geometry viewer. The architecture separates concerns into three layers:

- **model/** — Pure data: `Shape` dataclasses, `ComponentModel`, `InstrumentModel`, `Transform`
- **renderer/** — Backend-specific rendering: `PyThreejsRenderer`, `MatplotlibRenderer` (3D + 2D)
- **api.py** — Unified `view()` entry point with backend routing (`pythreejs`, `matplotlib`, `matplotlib_2d`, `webgl`, `webgl-classic`, `window`, `guess`)

All major refactoring goals have been implemented: shapes are pure data, transforms are pure numpy, style is hints-not-materials, and drawcall parsing uses a registry pattern. The old duplicated mcdisplay logic in `instr.py::show_instrument()` is consolidated into `mcdisplay.py` with a thin wrapper. The module has 69 unit tests.

`PyThreejsRenderer` is imported lazily — the module loads without pythreejs installed. `show_instrument()` checks for pythreejs before using it and raises `ImportError` with an install hint if missing.

## Remaining Considerations

### Missing import — `Any` in `matplotlib.py`

`renderer/matplotlib.py:44` uses `-> Any` in the `render_shape` signature but `Any` is not imported from `typing`. This will raise a `NameError` at runtime. Fix: add `from typing import Any` to the imports.

### Config constants not wired into pythreejs renderer

`config.py` defines `DEFAULT_CAMERA_POSITION`, `DEFAULT_CAMERA_TARGET`, `DEFAULT_FOV`, `DEFAULT_NEAR`, `DEFAULT_FAR`, `DEFAULT_RENDERER_SIZE`, and `DEFAULT_NAVIGATOR_DISTANCE`. The `pythreejs.py::make_scene()` method hardcodes the same values (`[5, 3, 10]`, `[0, 0, 2]`, `50`, `0.01`, `2000`) instead of importing the config constants. Similarly, `create_component_navigator()` hardcodes `distance = 2.0` instead of using `DEFAULT_NAVIGATOR_DISTANCE`. The constants serve as documentation but are not actually enforced by the code.

### Incomplete geometry guessing

`guess_geometry_from_comp_object` only handles two cases: parameterless components (axis triad) and xy-rectangle components (xwidth/yheight). It does not cover Arms, guides, or other component types. The function also uses `eval()` to evaluate parameter expressions, which is acceptable for trusted McStas instrument files but worth noting.

### Error output via `print()` in `mcdisplay.py`

`mcdisplay.py` uses `print()` for error messages (lines 132, 140-143) rather than `logging`. The caller in `api.py` checks for `None` return and raises `RuntimeError`, so errors are handled, but diagnostic output goes to stdout rather than a proper logging facility.

### Matplotlib circle and cylinder geometries are axis-flipped

In the matplotlib backend, cylinders have their axis of symmetry along Z instead of Y, and circles that should lie in the ZX plane are rendered in the YX plane. This is likely caused by a missing rotation step in the transform pipeline: there are two rotations — one to orient the shape into the component's coordinate frame, and a second rotation within that frame — and one of them is not being applied.

### Matplotlib backend displays both static image and interactive widget

When using the matplotlib backend, the output shows both a static inline image and an interactive widget. The static image is a duplicate and should be suppressed so only the interactive widget is displayed.
