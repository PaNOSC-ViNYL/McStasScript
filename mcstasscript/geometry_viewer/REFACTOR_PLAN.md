# geometry_viewer Refactor Plan

## Goal

Decouple shape data from rendering backends. Currently `shapes.py` is tightly coupled to pythreejs — every `make_geometry()` returns a `p3.BoxGeometry`, `make_mesh()` creates `p3.Mesh`, and `material_kwargs()` references `p3.MeshLambertMaterial`. The target is backend-agnostic shape dataclasses with separate renderer backends for pythreejs and matplotlib.

## Target Structure

```
geometry_viewer/
├── __init__.py              # Expose: view, view_with_json, view_with_guess
├── api.py                   # Public API with backend parameter
├── config.py                # Defaults: colors, camera, segments, etc.
├── transform.py             # Transform dataclass + quaternion math (pure numpy)
├── mcdisplay.py             # mcdisplay-webgl runner (renamed from mcdisplay_runner)
├── model/
│   ├── __init__.py
│   ├── shapes.py            # Pure dataclasses: BoxShape, CylinderShape, etc.
│   ├── component.py         # ComponentModel + drawcall parsing (DRAWCALL_PARSERS)
│   └── instrument.py        # InstrumentModel (collection of ComponentModels)
├── renderer/
│   ├── __init__.py
│   ├── base.py              # ABC: RendererBackend
│   ├── pythreejs.py         # PyThreejsRenderer (extracted from old shapes.py + pythree_specific.py)
│   └── matplotlib.py        # MatplotlibRenderer (3D interactive + 2D projection)
└── TODO.md                  # Updated
```

## Key Principles

- **Shapes are data, not rendering** — `Shape` classes store dimensions/vertices only. A renderer backend converts them to visual objects.
- **Transform is pure** — `Transform` holds `position`, `rotation_matrix`, `quaternion` as numpy data. No `apply_to()` method. Each renderer knows how to apply transforms.
- **Style hints, not materials** — `Style(opacity, color, wireframe)` carries rendering hints. Each backend's `create_material()` interprets them.
- **Opacity heuristics live in renderers** — Size-based opacity (large cylinders → more transparent) is computed per-backend in `create_material()`.
- **Registry for drawcalls** — `DRAWCALL_PARSERS` dispatch table instead of if-elif chains.

## Execution Order

1. `config.py`, `transform.py` — no dependencies
2. `model/shapes.py` — depends on transform
3. `renderer/base.py` — depends on shapes, transform
4. `model/component.py` — depends on shapes, transform
5. `model/instrument.py` — depends on component
6. `renderer/pythreejs.py` — depends on all above
7. `renderer/matplotlib.py` — depends on shapes, transform, base
8. `api.py` — depends on model + renderer
9. `__init__.py` — wires it up
10. Remove old files, update TODO.md

## Bug Fixes Applied

- `compnent_list` → `component_list` typo (old viewer.py:57)
- Undefined `transform` in `guess_geometry_from_comp_object` (old component_model.py:213/279)
- `return RuntimeError` → `raise RuntimeError` (old viewer.py:106)
- Fixed `view()` fallback logic to actually try guess-first

## Matplotlib Renderer

Supports two modes via `mode` parameter:

- **3D** (`mode="3d"`): Uses `mpl_toolkits.mplot3d`. Boxes → `Poly3DCollection`, cylinders → sampled mesh, lines → `ax.plot()`, polyhedra → `Poly3DCollection`. Returns `plt.Figure` with native 3D rotation.
- **2D** (`mode="2d"`): Top-down XY projection. Boxes → `Rectangle`/`Polygon`, cylinders → `Circle`, lines → `ax.plot()`, polyhedra → projected `PolyCollection`. Returns `plt.Figure`.
