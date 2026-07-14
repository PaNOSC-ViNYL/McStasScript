# geometry_viewer — Issues and Improvements

## Resolved

1. **No `__init__.py`** — ~~The module isn't a proper Python package.~~ **Fixed:** `__init__.py` created with full public API exports.

2. **Not exposed in main package** — ~~`mcstasscript/__init__.py` doesn't import anything from `geometry_viewer`.~~ **Partially fixed:** Module is now a proper package. Exposure in main `__init__.py` still pending.

3. **Tight coupling to pythreejs** — ~~`shapes.py` imports pythreejs directly.~~ **Fixed:** Shapes are now pure dataclasses in `model/shapes.py`. Rendering is handled by `renderer/pythreejs.py` and `renderer/matplotlib.py` backends.

4. **`pythree_specific.py` is a catch-all** — ~~Contains three unrelated concepts.~~ **Fixed:** Split into `renderer/pythreejs.py` (renderer + MaterialLibrary) and `renderer/matplotlib.py`.

5. **`InstrumentModel` is trivial** — ~~Just a list wrapper.~~ **Fixed:** Moved to `model/instrument.py`. Renderer-specific methods removed.

6. **`mcdisplay_runner.py` — Weak error handling** — ~~Returns `None` on failure, prints to stdout.~~ **Fixed:** Renamed to `mcdisplay.py`, returns `None` explicitly on failure, cleaner error messages.

7. **Hardcoded values** — ~~Magic numbers scattered through code.~~ **Fixed:** Centralized in `config.py`.

8. **`view()` function is confusing** — ~~`json_dict` parameter always overwritten, guess path never tried.~~ **Fixed:** `view()` now tries `view_with_guess` first, falls back to mcdisplay JSON.

9. **Typo: `compnent_list`** — ~~`viewer.py:57`~~ **Fixed:** Corrected to `component_list` in `api.py`.

10. **Undefined `transform`** — ~~`component_model.py:213/279`~~ **Fixed:** Removed — shapes no longer carry transforms in guess mode (no position info available).

11. **`return RuntimeError`** — ~~`viewer.py:106` returns instead of raises.~~ **Fixed:** Now `raise RuntimeError` in `api.py`.

12. **Dead code after `return`** — ~~`viewer.py:115-119`~~ **Fixed:** Removed.

13. **Massive if-elif chain** — ~~`component_model.py` drawcall dispatcher.~~ **Fixed:** Already had `DRAWCALL_PARSERS` dispatch table, preserved in `model/component.py`.

14. **Matplotlib line segments** — ~~Circular `_ax` dependency: `_render_line_segments` called `self._ax.plot()` before axis existed.~~ **Fixed:** `_render_line_segments` returns a `LineDescriptor(points, color)` dataclass. `make_scene` handles it alongside `Poly3DCollection` when adding children to the axis. Works for both 3D and 2D mode.

15. **No tests** — ~~Zero test coverage for this module.~~ **Fixed:** 69 unit tests in `mcstasscript/tests/test_geometry_viewer.py` covering transforms, shapes, drawcall parsers, ComponentModel, InstrumentModel, config, and API. Tests run in ~30ms.

## Remaining

1. **Not exposed in main package** — `mcstasscript/__init__.py` still doesn't import from `geometry_viewer`.

2. **`guess_geometry_from_comp_object`** — Still incomplete. Only handles parameterless components (axis triad) and xy-rectangle components. Could be extended to cover more component types (Arms, guides, etc.).

## Fixed by Tests

The following bugs were discovered and fixed when writing tests (July 2025):

- **`specified_pars` inverted condition** — `==` should have been `!=` in `guess_geometry_from_comp_object`. Parameters matching defaults were collected instead of parameters differing from defaults.
- **`check_conditions` operator precedence** — `par_name in parameter_names != requirement` is a Python chained comparison. Fixed to `(par_name in parameter_names) != requirement`.

## Current Structure

```
geometry_viewer/
├── __init__.py              # Expose: view, view_with_json, view_with_guess, models, renderers
├── api.py                   # Public API: view(), view_with_json(), view_with_guess()
├── config.py                # Defaults: colors, camera, segments, etc.
├── transform.py             # Transform dataclass + quaternion math (pure numpy)
├── mcdisplay.py             # mcdisplay-webgl runner
├── model/
│   ├── __init__.py
│   ├── shapes.py            # Shape dataclasses (renderer-agnostic geometry data only)
│   ├── component.py         # ComponentModel + drawcall parsing (registry pattern)
│   └── instrument.py        # InstrumentModel (collection of components)
├── renderer/
│   ├── __init__.py
│   ├── base.py              # Abstract renderer backend
│   ├── pythreejs.py         # PyThreejsRenderer + MaterialLibrary
│   └── matplotlib.py        # MatplotlibRenderer (3D + 2D modes)
├── REFACTOR_PLAN.md         # Refactor documentation
└── TODO.md                  # This file
```
