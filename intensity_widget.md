# Intensity Widget — Refactoring Plan

## Status: ✅ Implemented (562 tests passing)

## Goal

Merge `view_with_analysis()` into the `show_instrument()` → `view()` → `view_with_json()` flow.
The pythreejs widget always offers "Intensity" colormode, running the simulation on-demand
when the user selects it.

## Widget Layout (Intensity mode)

```
VBox([
    navigator dropdown,
    colormode dropdown,
    VBox([                          ← intensity_controls (visible/hidden)
        HBox([ncount, variable, Limits checkbox, limits_min, limits_max, Run]),
        HBox([aggregate]),
    ]),
    HBox([scene, colorbar]),
])
```

- `ncount`: `IntText` (no upper bound), defaults to `instrument._run_settings.get("ncount", 1000000)`
- `Limits` checkbox: toggles visibility of Min/Max fields (both variable ≠ None AND checkbox checked required)
- `limits_min` / `limits_max`: text fields, hidden by default
- When variable/ncount/limits change (data stale): grey out all components (#808080)

## Behavior Matrix

| User Action | Sim Run? | Effect |
|---|---|---|
| Select "Intensity" (no cached data) | No | Show controls, grey components, wait for Run |
| Select "Intensity" (cached data) | No | Show controls, re-apply with current aggregate |
| Click Run | Yes | Disable controls, hourglass icon, run simulation, re-enable |
| Change aggregate | No | Re-process cached data, re-color |
| Change variable/ncount/limits | No | Grey components, mark data stale |
| Switch away from Intensity | No | Hide controls, normal coloring |

## Files & Changes

### 1. `mcstasscript/geometry_viewer/renderer/pythreejs.py`

**`__init__`**: Added `instrument_object=None` param + new instance state:
- `self._diag_data`, `self._diag_monitors`, `self._diag_data_dim`, `self._diag_variable`
- `self._data_stale = intensity_map is None`
- `self._intensity_controls_container`, `self._intensity_widgets`

**New methods:**
- `create_intensity_controls()` → `ipywidgets.VBox` with:
  - `ncount` (`IntText`, default from instrument)
  - `variable` (Dropdown: `None` + `l, x, y, z, t, px, py, pz, p4, e, s1, s2, s3`)
  - `Limits` checkbox (toggles Min/Max visibility)
  - `limits_min` / `limits_max` (`Text`, hidden by default)
  - `aggregate` (Dropdown: `total, min, max, average, median, span`)
  - `Run` button (icon: ▶ → ⏳ → ▶)
- `_update_limits_visibility()` — show/hide limits fields based on variable + checkbox
- `_on_variable_change()` — grey components, set `_data_stale = True`, update limits visibility
- `_on_limits_check_change()` — update limits visibility
- `_on_run_click()` — disable controls, run `IntensityDiagnostics`, cache data, call `_apply_intensity_from_data()`, re-enable
- `_on_aggregate_change()` — if data cached and not stale, re-apply with new aggregation
- `_apply_intensity_from_data(aggregation)` — build `intensity_map` from cached data using `_aggregate_intensity()`, update colors + colorbar
- `_grey_all_components()` — set all components to `#808080`
- `_disable_intensity_controls(disabled)` — enable/disable all control widgets

**Modified `create_colormode_selector()`:**
- Always includes "Intensity" option
- On "intensity": show controls container; if `_data_stale`, grey components
- On other: hide controls container, normal coloring

**Modified `_make_colorbar_image()`:**
- Returns empty `Image` for default mode and stale intensity mode (no more `Label` swapping)

### 2. `mcstasscript/geometry_viewer/api.py`

**`_get_renderer()`:**
- Filters `instrument_object` kwarg for non-pythreejs backends

**`view_with_json()`:**
- Passes `instrument_object` to renderer via `kwargs_for_renderer`
- Adds `intensity_controls` widget to layout
- New layout: `VBox([navigator, colormode_selector, intensity_controls, HBox([scene, colorbar])])`

**`view_with_guess()`:**
- Same treatment — passes `instrument_object`, builds full widget layout with intensity controls

### 3. `mcstasscript/interface/instr.py` — `show_instrument()`

- No changes needed; `self` is already passed as `instrument_object` to `view()`

### 4. `mcstasscript/tests/test_geometry_viewer.py`

- Updated `test_colormode_selector_no_intensity` → `test_colormode_selector_always_has_intensity`
- Updated `test_colorbar_default_mode` — expects empty `Image` instead of `Label`
- Added 8 new tests: controls existence, widget population, variable/aggregate options, grey-out, stale data, colorbar stale intensity

### 5. Backward Compatibility

- `view_with_analysis()` remains unchanged
- `view()` with `intensity_map=` still works as before
- Existing callers of `show_instrument()` unaffected
