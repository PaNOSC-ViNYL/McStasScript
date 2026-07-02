from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Hashable

import pythreejs as p3


@dataclass
class MaterialLibrary:
    colors: list[str]
    material_class: type = p3.MeshBasicMaterial # Default
    color_index: int = 0
    _cache: dict[tuple[type, str, tuple[tuple[str, Hashable], ...]], Any] = field(default_factory=dict)

    @property
    def color(self) -> str:
        return self.colors[self.color_index]

    def next(self) -> str:
        """Advance to the next color and return it."""
        self.color_index = (self.color_index + 1) % len(self.colors)
        return self.color

    def get_material(self, material_class: type | None = None, **kwargs: Any):
        """
        Return a cached material for the current color + material options.

        Example:
            mat = lib.get_material(p3.LineBasicMaterial, linewidth=1)
            mat = lib.get_material(p3.MeshPhongMaterial, transparent=True, opacity=0.4)
        """
        cls = material_class or self.material_class

        # Unless explicitly overridden, use the current library color.
        kwargs = {"color": self.color, **kwargs}

        key = self._make_key(cls, kwargs)

        if key not in self._cache:
            self._cache[key] = cls(**kwargs)

        return self._cache[key]

    def _make_key(self, cls: type, kwargs: dict[str, Any]):
        """
        Convert material parameters into a stable cache key.
        Assumes kwargs are simple hashable values: strings, numbers, bools, None.
        """
        try:
            frozen_kwargs = tuple(sorted(kwargs.items()))
            hash(frozen_kwargs)
        except TypeError as exc:
            raise TypeError(
                "MaterialLibrary cache keys require hashable material arguments. "
                "For textures, arrays, or other objects, you may need to pass a stable name/id instead."
            ) from exc

        return cls, kwargs["color"], frozen_kwargs