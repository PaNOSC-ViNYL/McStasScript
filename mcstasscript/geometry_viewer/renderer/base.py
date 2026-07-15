from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from mcstasscript.geometry_viewer.model.shapes import Shape
from mcstasscript.geometry_viewer.transform import Transform


class RendererBackend(ABC):
    @abstractmethod
    def render_shape(self, shape: Shape) -> Any:
        """Convert a Shape to backend-specific visual object(s)."""

    @abstractmethod
    def apply_transform(self, visual_obj: Any, transform: Transform) -> Any:
        """Apply position/rotation to a visual object."""

    @abstractmethod
    def create_material(self, style: Any, color: str, **kwargs) -> Any:
        """Create a material/artist for the backend."""

    @abstractmethod
    def make_scene(self, children: list[Any], **kwargs) -> Any:
        """Assemble final viewable widget/figure."""

    def render_component(self, component: Any) -> list[Any]:
        """Render all shapes in a component's shape_list."""
        return [self.render_shape(s) for s in component.shape_list]

    def render_instrument(self, instrument: Any, **kwargs) -> Any:
        """Render all components in an instrument model."""
        all_children = []
        for component in instrument.component_models:
            all_children.extend(self.render_component(component))
        return self.make_scene(all_children, **kwargs)
