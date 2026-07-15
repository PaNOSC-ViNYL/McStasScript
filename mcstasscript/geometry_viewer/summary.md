# geometry_viewer — Summary

## Architecture

The module implements a backend-agnostic instrument geometry viewer. The architecture separates concerns into three layers:

- **model/** — Pure data: `Shape` dataclasses, `ComponentModel`, `InstrumentModel`, `Transform`
- **renderer/** — Backend-specific rendering: `PyThreejsRenderer`, `MatplotlibRenderer` (3D + 2D)
- **api.py** — Unified `view()` entry point with backend routing (`pythreejs`, `matplotlib`, `matplotlib_2d`, `webgl`, `webgl-classic`, `window`, `guess`)

All major refactoring goals have been implemented: shapes are pure data, transforms are pure numpy, style is hints-not-materials, and drawcall parsing uses a registry pattern. The old duplicated mcdisplay logic in `instr.py::show_instrument()` is consolidated into `mcdisplay.py` with a thin wrapper. The module has 75 unit tests, all passing on CI (Python 3.8, 3.9, 3.10).

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

### Matplotlib circle and cylinder orientations — FIXED

**Resolved:** `MatplotlibRenderer._transform_points()` now uses `transform.final_quaternion()` to get the combined rotation (rotation_matrix + quaternion) instead of calling `transform.transform_points()` which ignored the quaternion field. A new `quaternion_to_rotation_matrix()` function in `transform.py` converts the combined quaternion back to a 3x3 matrix for point transformation.

### Matplotlib backend displays both static image and interactive widget — FIXED

**Resolved:** `view_with_json()` and `view_with_guess()` in `api.py` now call `plt.show()` and return `None` for matplotlib backends. With `%matplotlib widget`, the widget is already displayed by `plt.figure()` and `return None` suppresses Jupyter's auto-display of the returned `plt.Figure` as a duplicate static PNG. With `%matplotlib inline`, `plt.show()` renders the figure and `return None` prevents a second copy.

### Matplotlib 2D projection selection

`MatplotlibRenderer` accepts a `projection` keyword argument (`"xy"`, `"zx"`, `"zy"`) that controls which axes are displayed in 2D mode. The first character is the horizontal axis, the second is vertical. Default is `"zx"` (Z horizontal = beam direction, X vertical), matching McStas convention. The parameter flows through `**kwargs` from `view()` → `_get_renderer()` → `MatplotlibRenderer`, allowing a future widget to select the projection without API changes.
