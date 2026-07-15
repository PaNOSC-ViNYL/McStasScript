# geometry_viewer — Summary

## Architecture

The module implements a backend-agnostic instrument geometry viewer. The architecture separates concerns into three layers:

- **model/** — Pure data: `Shape` dataclasses, `ComponentModel`, `InstrumentModel`, `Transform`
- **renderer/** — Backend-specific rendering: `PyThreejsRenderer`, `MatplotlibRenderer` (3D + 2D)
- **api.py** — Unified `view()` entry point with backend routing (`pythreejs`, `matplotlib`, `matplotlib_2d`, `webgl`, `webgl-classic`, `window`, `guess`)

All major refactoring goals have been implemented: shapes are pure data, transforms are pure numpy, style is hints-not-materials, and drawcall parsing uses a registry pattern. The old duplicated mcdisplay logic in `instr.py::show_instrument()` is consolidated into `mcdisplay.py` with a thin wrapper. The module has 75 unit tests, all passing on CI (Python 3.8, 3.9, 3.10).

`PyThreejsRenderer` is imported lazily — the module loads without pythreejs installed. `show_instrument()` checks for pythreejs before using it and raises `ImportError` with an install hint if missing.

## Remaining Considerations

### Missing import — `Any` in `matplotlib.py` — FIXED

**Resolved:** Added `from typing import Any` to the imports in `renderer/matplotlib.py`.

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

### Matplotlib 2D backend shows no geometry — FIXED

**Resolved:** In 2D mode, all render methods (`_render_box`, `_render_cylinder`, `_render_cone`, `_render_circle`, `_render_polyhedron`) were creating `Poly3DCollection` objects. The `_make_2d_scene` method then tried to extract face data via `child.get_paths()`, but `Poly3DCollection.get_paths()` returns empty or malformed data when the collection hasn't been added to a 3D axis. Fix: render methods now create `PolyCollection` (2D) or `Poly3DCollection` (3D) via a new `_make_collection()` helper, and `_make_2d_scene` adds `PolyCollection` children directly to the 2D axis.

### Per-component color control — FIXED

**Resolved:** Previously, `MatplotlibRenderer` advanced the color index per-shape (`_next_color()` in each `_render_*`), while `PyThreejsRenderer` advanced per-component via `next_component()`. This inconsistency meant multi-shape components had different colors per shape in matplotlib. Fix: both renderers now use a consistent `next_component()` / `current_color` pattern. `render_component()` captures `current_color` once, and all shapes in that component share it. Additionally, `update_component_color(index, color)` is available on both renderers to change a component's color after rendering. `MaterialLibrary.next()` was also fixed to return-then-advance (was advance-then-return).

### Colormode — FIXED

**Resolved:** Both renderers now accept a `colormode` parameter with two options:
- `"default"` (default): cycle through `DEFAULT_COLORS` palette, one color per component
- `"component"`: map each component's index to a color on the viridis colormap via `config.index_to_color()`

The `num_components` parameter is passed through from `view_with_json()` and `view_with_guess()` so the colormap can be properly normalized. In pythreejs, `_get_material()` routes to `get_material_for_color()` with the computed viridis color when in component mode.

### Matplotlib 2D projection selection

`MatplotlibRenderer` accepts a `projection` keyword argument (`"xy"`, `"zx"`, `"zy"`) that controls which axes are displayed in 2D mode. The first character is the horizontal axis, the second is vertical. Default is `"zx"` (Z horizontal = beam direction, X vertical), matching McStas convention. The parameter flows through `**kwargs` from `view()` → `_get_renderer()` → `MatplotlibRenderer`, allowing a future widget to select the projection without API changes.

### PyThreejsRenderer.make_scene() missing **kwargs — FIXED

**Resolved:** `PyThreejsRenderer.make_scene()` was missing `**kwargs` in its signature, causing `TypeError: got an unexpected keyword argument 'num_components'` when `api.py` passed `num_components` through. Added `**kwargs` to match the `MatplotlibRenderer.make_scene()` signature.

### Matplotlib component colormode shows single color — FIXED

**Resolved:** `MatplotlibRenderer.next_component()` always called `_next_color()` which advanced `_color_index` modulo `len(self.colors)`, causing all components to cycle through the same palette instead of mapping to unique viridis colors. In component mode, `next_component()` now increments `_color_index` linearly so each component gets a distinct color from `index_to_color()`.
