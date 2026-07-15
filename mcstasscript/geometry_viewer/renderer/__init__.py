from mcstasscript.geometry_viewer.renderer.base import RendererBackend
from mcstasscript.geometry_viewer.renderer.matplotlib import MatplotlibRenderer

def __getattr__(name):
    if name == "PyThreejsRenderer":
        from mcstasscript.geometry_viewer.renderer.pythreejs import PyThreejsRenderer
        return PyThreejsRenderer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["RendererBackend", "PyThreejsRenderer", "MatplotlibRenderer"]
