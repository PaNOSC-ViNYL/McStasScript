# Intensity-Based Component Coloring

## Overview

Add a new `"intensity"` colormode to the geometry_viewer that colors each component based on the neutron intensity reaching it, sourced from `IntensityDiagnostics`. Includes a convenience `view_with_analysis()` that auto-runs the simulation and visualizes the result.

## Design Decisions

- **Colormap**: User-configurable (default `"inferno"`), log-scale normalization by default
- **Zero intensity**: Very dark (near-black) via log floor at `1e-30 * max_I`
- **Source component**: Colored by what it emits (= first monitor's reading after it)
- **Backends**: All three (pythreejs, matplotlib 3D, matplotlib 2D)
- **Auto-run**: `view_with_analysis()` runs `IntensityDiagnostics` internally
- **1D aggregation**: When `variable` is set (1D mode), aggregations operate on **axis values** (e.g. wavelength) weighted by intensity — not on intensity values themselves. E.g. `aggregation="max"` returns the highest wavelength with non-zero intensity.

## Implementation Steps

### Step 1: `config.py` — `intensity_to_color()`
- Log-scale normalization by default (configurable via `log_scale`)
- User-configurable colormap (default `"inferno"`)
- Zero/near-zero intensity → very dark (log floor at `1e-30 * max_I`)

### Step 2: `api.py` — `view_with_analysis()` + `view()` params + `_aggregate_intensity()`
- `_aggregate_intensity(mon_data, aggregation)` — reduces 1D monitor data to a scalar.
  Aggregations operate on **axis values** (e.g. wavelength) weighted by intensity:
  - `"total"`: sum of all bins (default, equivalent to `total_I` in 0D mode)
  - `"min"`: lowest axis value with non-zero intensity
  - `"max"`: highest axis value with non-zero intensity
  - `"span"`: max_axis - min_axis with non-zero intensity
  - `"mean"` / `"average"`: intensity-weighted average of axis values
  - `"median"`: axis value at the median of the cumulative intensity
  - In 0D mode (`dimension == 0`), always returns `total_I` regardless of aggregation
- `view_with_analysis(instr, backend, variable, limits, cmap, log_scale, aggregation)` — runs `IntensityDiagnostics`, builds `intensity_map`, calls `view()`
- `view()` gains: `intensity_map`, `cmap`, `log_scale` params
- Source component (index 0) gets intensity = first monitor's reading (same aggregation)
- Forward params through `view_with_json()` and `view_with_guess()` to renderers

### Step 3: `renderer/pythreejs.py` — Intensity colormode
- `__init__`: accept `intensity_map`, `cmap`, `log_scale`; compute `min_I`/`max_I`
- `render_component()`: resolve `component.comp.name` → intensity → color
- `create_colormode_selector()`: add "Intensity" to dropdown
- `on_colormode_change`: handle intensity recoloring

### Step 4: `renderer/matplotlib.py` — Intensity colormode
- `__init__`: accept same params, compute `min_I`/`max_I`
- `render_component()`: resolve component name → intensity → color before super call
- Works for both 3D and 2D modes

### Step 5: `__init__.py` — Export `view_with_analysis`

### Step 6: Tests
- Unit tests for `intensity_to_color()` (log/linear, edge cases, zero intensity)
- Unit tests for `_aggregate_intensity()` (all aggregation modes, 0D/1D)
- Tests for intensity colormode in both renderers (mock intensity_map)

## Data Flow

```
view_with_analysis(instr, variable="l", aggregation="max")
    │
    ├─ IntensityDiagnostics(instr).run_general(variable="l")
    │       └─ runs McStas simulation with monitors, produces 1D data
    │       └─ mon_data.Intensity = [I1, I2, ...], mon_data.xaxis = [λ1, λ2, ...]
    │
    ├─ _aggregate_intensity(mon_data, "max") → highest λ with I > 0
    │       └─ Build intensity_map: {comp_name: scalar, ...}
    │
    └─ view(instr, intensity_map=..., colormode="intensity")
            │
            ├─ generate_json() → InstrumentModel
            │
            └─ Renderer.render_component(componentModel)
                    ├─ name = componentModel.comp.name
                    ├─ I = intensity_map[name]
                    ├─ color = intensity_to_color(I, min_I, max_I, cmap, log_scale)
                    └─ render shapes with that color
```

## Usage

```python
from mcstasscript.geometry_viewer import view_with_analysis

# 0D — total intensity per component
view_with_analysis(my_instr)

# 1D — color by highest wavelength reaching each component
view_with_analysis(my_instr, variable="l", limits=[0.5, 2.5], aggregation="max")

# 1D — color by lowest wavelength reaching each component
view_with_analysis(my_instr, variable="l", aggregation="min")

# 1D — color by intensity-weighted average wavelength
view_with_analysis(my_instr, variable="l", aggregation="average")

# 1D — color by median wavelength (cumulative intensity)
view_with_analysis(my_instr, variable="l", aggregation="median")

# 1D — color by wavelength span (highlights spectral bandwidth)
view_with_analysis(my_instr, variable="l", aggregation="span")

# Custom colormap and linear scale
view_with_analysis(my_instr, cmap="viridis", log_scale=False)
```

## Files Modified

| File | Purpose |
|------|---------|
| `config.py` | `intensity_to_color()` function |
| `api.py` | `view_with_analysis()`, `_aggregate_intensity()`, new params on `view()`/`view_with_json()` |
| `renderer/pythreejs.py` | Intensity colormode, dropdown extension |
| `renderer/matplotlib.py` | Intensity colormode |
| `__init__.py` | Export `view_with_analysis` |
| `tests/test_geometry_viewer.py` | Unit tests (100 total, all passing) |
