# geometry_viewer — Issues and Improvements

## Critical Bugs

1. **`viewer.py:57`** — Typo: `instrument_object.compnent_list` (missing 'o', should be `component_list`)

2. **`component_model.py:193-281`** — `guess_geometry_from_comp_object` takes `instr_parameters` but the `transform` variable on lines 213 and 279 is **undefined** — will crash with `NameError`. The parameter `instr_parameters` is also never actually used despite being passed in.

3. **`viewer.py:106`** — `return RuntimeError(...)` returns the exception object instead of raising it. Should be `raise RuntimeError(...)`.

4. **`viewer.py:115-119`** — Dead code after `return` on line 110. The commented-out try/except block for the guess-then-fallback logic is unreachable.

## Structural Issues

5. **No `__init__.py`** — The module isn't a proper Python package. Nothing is importable as `from mcstasscript.geometry_viewer import view`. Compare with `instrument_diagram` which has one.

6. **Not exposed in main package** — `mcstasscript/__init__.py` doesn't import anything from `geometry_viewer`, so users can't discover it.

7. **`component_model.py` — Massive if-elif chain (lines 48-189)** — The drawcall dispatcher is a 140-line switch statement. Should use a registry/dispatch dictionary: `{"box": parse_box_drawcall, "cylinder": parse_cylinder_drawcall, ...}`.

8. **Tight coupling to pythreejs** — `shapes.py` imports pythreejs directly. The `Shape` classes know about `p3.Mesh`, `p3.BoxGeometry`, etc., making it impossible to swap the renderer (e.g., to vtk, trimesh, or a headless exporter). `Shape` should produce renderer-agnostic geometry data, and a separate "renderer backend" handles the pythreejs conversion.

9. **`pythree_specific.py` is a catch-all** — Contains three unrelated concepts: `MaterialLibrary` (material caching), `PyThreeComponent` (thin data holder), and `PyThreeGeometryModel` (scene builder). Should be split.

10. **`InstrumentModel` is trivial** — Just a list wrapper with `add_model`. Could be replaced with a plain `list` or a proper dataclass. ~~(Partially addressed: json_dict init moved into `__init__`.)~~

11. **No tests** — Zero test coverage for this module.

12. **`mcdisplay_runner.py` — Weak error handling** — Returns `None` on failure (line 89), prints to stdout instead of logging, and subprocess output capture mixes stdout/stderr.

13. **Hardcoded values** — Camera position, FOV, axis size, navigator distance, default colors, radial segments (32), circle segments (64) are all magic numbers scattered through the code.

14. **`view()` function is confusing** — The `json_dict` parameter is always overwritten inside the function (line 108), making it useless. The `generate_json` call always runs (lines 99-102), so `view()` never tries the "guess" path despite its docstring saying "Plots quick geometry if possible, runs mcdisplay if necessary."

## Suggested Restructure

```
geometry_viewer/
├── __init__.py              # Expose: view, view_with_json, view_with_guess
├── api.py                   # Public API: view(), view_with_json(), view_with_guess()
├── model/
│   ├── __init__.py
│   ├── instrument.py        # InstrumentModel (collection of components)
│   ├── component.py         # ComponentModel + drawcall parsing (registry pattern)
│   └── shapes.py            # Shape dataclasses (renderer-agnostic geometry data only)
├── renderer/
│   ├── __init__.py
│   ├── base.py              # Abstract renderer backend
│   └── pythreejs.py         # PyThreeGeometryModel, MaterialLibrary, pythreejs conversion
├── transform.py             # Transform, quaternions, matrix utils (renamed from helpers)
├── mcdisplay.py             # mcdisplay-webgl runner (renamed from mcdisplay_runner)
└── config.py                # Defaults: colors, camera, segments, etc.
```

### Key Principles

- **Shapes are data, not rendering** — `Shape` classes store dimensions/vertices only. A renderer backend converts them to pythreejs objects.
- **Registry for drawcalls** — `{"box": parse_box, "cylinder": parse_cylinder, ...}` instead of a 140-line if-elif chain.
- **Fix the `view()` fallback logic** — Actually try `view_with_guess` first, fall back to mcdisplay.
- **Configurable defaults** — Centralize magic numbers in a config module.
