# Colorbar for Intensity/Component Coloring

## Overview

Add a colorbar to the geometry_viewer so the meaning of component colors is interpretable. Shows in `"component"` and `"intensity"` colormodes, hidden in `"default"`.

## Design Decisions

- **Label auto-detection**: `view_with_analysis()` extracts label from monitor metadata
- **PyThreejs layout**: Colorbar as a narrow vertical strip beside the 3D scene in an `HBox`
- **Matplotlib**: Native `fig.colorbar()` with `ScalarMappable`
- **Visibility**: Shown for `"component"` and `"intensity"`, hidden for `"default"`

### Label Sources

| Mode | Label |
|------|-------|
| `"component"` | `"Component index"` |
| `"intensity"` + 0D | `"Intensity [n/s]"` |
| `"intensity"` + 1D | `mon_data.metadata.xlabel` (e.g. `"Wavelength [Å]"`) |

### PyThreejs Layout

```
VBox([
  navigator dropdown,
  colormode selector,
  HBox([scene (3D renderer), colorbar image])
])
```

## Implementation Steps

### Step 1: `config.py` — `create_colorbar_image()`

```python
def create_colorbar_image(cmap: str, vmin: float, vmax: float,
                          label: str, log_scale: bool = True,
                          num_ticks: int = 5) -> bytes:
    """Create a colorbar as a PNG image.

    Renders a small matplotlib figure with a vertical colorbar using the
    given colormap, limits, label, and normalization. Returns PNG bytes.
    """
```

- Creates a small figure (~1x3 inches)
- `ScalarMappable` with the colormap and `LogNorm` / `Normalize`
- `fig.colorbar()` with label, ticks, and formatting
- Saves to `io.BytesIO` as PNG, returns bytes

### Step 2: `api.py` — Extract and forward `colorbar_label`

In `view_with_analysis()`, after building `intensity_map`, extract the label:

```python
# Extract colorbar label from first monitor's metadata
colorbar_label = None
if diag.monitors:
    first_mon_name = diag.monitors[0][0]
    try:
        first_mon_data = name_search(first_mon_name, diag.data)
        if diag.data_dim == 1 and first_mon_data.metadata.xlabel:
            colorbar_label = first_mon_data.metadata.xlabel
        else:
            colorbar_label = "Intensity [n/s]"
    except Exception:
        pass
```

Pass `colorbar_label` through `view()` → `view_with_json()` → renderer.

In `view()`, add `colorbar_label: str | None = None` parameter.

In `view_with_json()`, forward `colorbar_label` to renderer via kwargs.

### Step 3: `renderer/pythreejs.py` — Colorbar widget

**`__init__`**: Accept `colorbar_label`. Store `colorbar_label`.

**`create_colorbar()`**: Returns `ipywidgets.Image` with PNG from `create_colorbar_image()`, or an empty `ipywidgets.Label` when colorbar should be hidden.

```python
def create_colorbar(self) -> Any:
    """Create a colorbar widget for the current colormode."""
    if self.colormode == "default":
        return ipw.Label()  # invisible placeholder
    import matplotlib.pyplot as plt
    import io
    if self.colormode == "intensity" and self.intensity_map is not None:
        label = self.colorbar_label or "Value"
        img = create_colorbar_image(self.cmap, self._min_I, self._max_I,
                                     label, self.log_scale)
    else:
        label = self.colorbar_label or "Component index"
        img = create_colorbar_image("viridis", 0, self.num_components - 1,
                                     label, log_scale=False)
    return ipw.Image(value=img, format='png', layout=ipw.Layout(width='60px'))
```

**`view_with_json()`** (in `api.py`): Wrap scene + colorbar in `HBox`:

```python
if isinstance(renderer, PyThreejsRenderer):
    import ipywidgets as ipw
    navigator = renderer.create_component_navigator(scene)
    colormode_selector = renderer.create_colormode_selector()
    colorbar = renderer.create_colorbar()
    return ipw.VBox([navigator, colormode_selector, ipw.HBox([scene, colorbar])])
```

**Colormode change callback**: Update colorbar when switching modes. The simplest approach is to rebuild the VBox with a new colorbar. Since `create_colorbar()` returns a new widget, store a reference and update its content:

In `create_colormode_selector()`, the callback should also update the colorbar. Pass the colorbar widget reference into the callback (or store it on the renderer after `create_colorbar()` is called).

### Step 4: `renderer/matplotlib.py` — Colorbar axis

In `make_scene()` (both `_make_3d_scene` and `_make_2d_scene`), when colormode ≠ `"default"`:

```python
if self.colormode != "default":
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize, LogNorm
    if self.colormode == "intensity" and self.intensity_map is not None:
        norm = LogNorm(vmax=self._max_I) if self.log_scale else Normalize(vmin=self._min_I, vmax=self._max_I)
        sm = ScalarMappable(cmap=self.cmap, norm=norm)
        label = self.colorbar_label or "Value"
    else:
        norm = Normalize(vmin=0, vmax=self.num_components - 1)
        sm = ScalarMappable(cmap="viridis", norm=norm)
        label = self.colorbar_label or "Component index"
    sm.set_array([])
    cbar_ax = fig.add_axes([0.92, 0.15, 0.02, 0.7])
    fig.colorbar(sm, cax=cbar_ax, label=label)
```

Adjust subplot layout to leave room for the colorbar (e.g., `fig.subplots_adjust(right=0.88)`).

### Step 5: Tests

- `TestColorbarImage`: `create_colorbar_image()` returns valid PNG bytes, handles log/linear, different colormaps
- `TestPyThreejsColorbar`: `create_colorbar()` returns `Image` for intensity/component, `Label` for default
- `TestMatplotlibColorbar`: Colorbar axis exists in figure for intensity/component modes

## Files Modified

| File | Changes |
|------|---------|
| `config.py` | `create_colorbar_image()` — renders a small matplotlib figure with a vertical colorbar, returns PNG bytes |
| `api.py` | Extract `colorbar_label` from monitor metadata in `view_with_analysis()`, forward through `view()`/`view_with_json()`, HBox layout for pythreejs |
| `renderer/pythreejs.py` | `create_colorbar()`, `_make_colorbar_image()`, `_update_colorbar()`, `colorbar_label` param, colormode callback updates colorbar |
| `renderer/matplotlib.py` | `_add_colorbar()` — adds colorbar axis in `make_scene()` for both 3D and 2D |
| `tests/test_geometry_viewer.py` | `TestColorbarImage` (4), `TestPyThreejsColorbar` (4), `TestMatplotlibColorbar` (3) — 117 total tests, all passing |

## Usage

```python
from mcstasscript.geometry_viewer import view_with_analysis

# Colorbar auto-labels from monitor metadata
view_with_analysis(my_instr)  # label: "Intensity [n/s]"
view_with_analysis(my_instr, variable="l")  # label: "Wavelength [Å]"
view_with_analysis(my_instr, variable="t")  # label: "Time [ns]"
```
