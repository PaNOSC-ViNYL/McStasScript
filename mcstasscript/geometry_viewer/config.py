import io

import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize, LogNorm
from matplotlib.ticker import MaxNLocator
import numpy as np

DEFAULT_COLORS = [
    "#ff0000", "#808080", "#00ff00", "#ffff00", "#0000ff",
    "#ff00ff", "#00ffff", "#ffa500", "#444444", "#cccccc",
]

DEFAULT_CAMERA_POSITION = [5, 3, 10]
DEFAULT_CAMERA_TARGET = [0, 0, 2]
DEFAULT_FOV = 50
DEFAULT_NEAR = 0.01
DEFAULT_FAR = 2000
DEFAULT_RENDERER_SIZE = (900, 600)

DEFAULT_RADIAL_SEGMENTS = 32
DEFAULT_CIRCLE_SEGMENTS = 64

DEFAULT_NAVIGATOR_DISTANCE = 2.0


def index_to_color(index: int, num_components: int) -> str:
    """Map a component index to an RGB hex color using the viridis colormap."""
    import matplotlib.cm as cm
    if num_components <= 1:
        t = 0.5
    else:
        t = index / (num_components - 1)
    rgba = cm.viridis(t)
    r, g, b = int(round(rgba[0] * 255)), int(round(rgba[1] * 255)), int(round(rgba[2] * 255))
    return f"#{r:02x}{g:02x}{b:02x}"


def intensity_to_color(intensity: float, min_I: float, max_I: float,
                       cmap: str = "inferno", log_scale: bool = True) -> str:
    """Map an intensity value to an RGB hex color using a matplotlib colormap."""
    import matplotlib.cm as cm
    if max_I <= 0 or intensity <= 0:
        t = 0.0
    elif log_scale:
        log_min = 0.0 if min_I <= 0 else np.log10(min_I)
        log_max = np.log10(max_I)
        if log_max == log_min:
            t = 1.0
        else:
            log_val = np.log10(max(intensity, 1e-30 * max_I))
            t = (log_val - log_min) / (log_max - log_min)
    else:
        if max_I == min_I:
            t = 1.0
        else:
            t = (intensity - min_I) / (max_I - min_I)
    t = max(0.0, min(1.0, t))
    rgba = plt.get_cmap(cmap)(t)
    r, g, b = int(round(rgba[0] * 255)), int(round(rgba[1] * 255)), int(round(rgba[2] * 255))
    return f"#{r:02x}{g:02x}{b:02x}"


def create_colorbar_image(cmap: str, vmin: float, vmax: float,
                          label: str, log_scale: bool = True,
                          num_ticks: int = 5) -> bytes:
    """Create a colorbar as a PNG image.

    Renders a small matplotlib figure with a vertical colorbar using the
    given colormap, limits, label, and normalization. Returns PNG bytes.
    """
    if log_scale and vmax > 0 and vmin > 0:
        norm = LogNorm(vmin=vmin, vmax=vmax)
    else:
        norm = Normalize(vmin=max(vmin, 0), vmax=vmax)

    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])

    fig, ax = plt.subplots(figsize=(0.6, 3.5))
    cbar = fig.colorbar(sm, cax=ax, label=label)
    cbar.locator = MaxNLocator(nbins=num_ticks)
    cbar.update_ticks()
    cbar.ax.tick_params(labelsize=8)
    cbar.ax.set_ylabel(label, fontsize=9, rotation=0, labelpad=8)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', pad_inches=0.1)
    buf.seek(0)
    png_bytes = buf.getvalue()
    plt.close(fig)
    return png_bytes
