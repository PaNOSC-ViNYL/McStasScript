import json
import warnings

import numpy as np

from mcstasscript.geometry_viewer.transform import Transform
from mcstasscript.geometry_viewer.transform import quaternion_from_vectors
from mcstasscript.geometry_viewer.transform import pos_rot_from_list
from mcstasscript.geometry_viewer.model.shapes import (
    LineSegmentsShape,
    BoxShape,
    CircleShape,
    CylinderShape,
    ConeShape,
    PolyhedronShape,
    SphereShape,
    triangulate_faces,
)
from mcstasscript.geometry_viewer.config import (
    DEFAULT_RADIAL_SEGMENTS,
    DEFAULT_CIRCLE_SEGMENTS,
)
from mcstasscript.geometry_viewer.rules import GeometryRule, GeometryRuleRegistry
from mcstasscript.geometry_viewer.expression import safe_eval
from mcstasscript.geometry_viewer.model.bounds import Bounds, component_bounds
from mcstasscript.geometry_viewer.model.style import default_style_for_shape


def _make_axis_transform(pos, rot, offset, default_axis, normal):
    """Create a Transform for a shape with an axis-aligned orientation."""
    quaternion = quaternion_from_vectors(default_axis, normal)
    return Transform(
        position=pos + np.array(offset) @ rot.T,
        quaternion=quaternion,
        rotation_matrix=rot,
    )


def _parse_multiline(drawcall, pos, rot):
    """Parse a multiline drawcall, returning segment points (not a shape)."""
    args = drawcall["args"]
    new_points = np.array(args, dtype=np.float32).reshape((-1, 3))

    if len(new_points) <= 2:
        return new_points

    segment_points = np.empty((2 * (len(new_points) - 1), 3), dtype=np.float32)
    segment_points[0::2] = new_points[:-1]
    segment_points[1::2] = new_points[1:]
    return segment_points


def _parse_box(drawcall, pos, rot):
    args = drawcall["args"]
    x, y, z = args[0], args[1], args[2]
    xwidth, yheight, zdepth = args[3], args[4], args[5]
    nx, ny, nz = args[7], args[8], args[9]
    transform = _make_axis_transform(pos, rot, (x, y, z), (0, 1, 0), (nx, ny, nz))
    return BoxShape(width=xwidth, height=yheight, depth=zdepth, transform=transform)


def _parse_cylinder(drawcall, pos, rot):
    args = drawcall["args"]
    x, y, z = args[0], args[1], args[2]
    radius, height = args[3], args[4]
    nx, ny, nz = args[6], args[7], args[8]
    transform = _make_axis_transform(pos, rot, (x, y, z), (0, 1, 0), (nx, ny, nz))
    return CylinderShape(
        radius=radius, height=height, radial_segments=DEFAULT_RADIAL_SEGMENTS, transform=transform
    )


def _parse_cone(drawcall, pos, rot):
    args = drawcall["args"]
    x, y, z = args[0], args[1], args[2]
    radius, height = args[3], args[4]
    nx, ny, nz = args[5], args[6], args[7]
    transform = _make_axis_transform(pos, rot, (x, y, z), (0, 1, 0), (nx, ny, nz))
    return ConeShape(
        radius=radius, height=height, radial_segments=DEFAULT_RADIAL_SEGMENTS, transform=transform
    )


def _parse_circle(drawcall, pos, rot):
    args = drawcall["args"]
    plane = args[0]
    x, y, z = args[1], args[2], args[3]
    radius = args[4]

    plane_normals = {
        "xy": (0, 0, 1),
        "xz": (0, 1, 0),
        "yz": (1, 0, 0),
    }
    normal = plane_normals.get(plane)
    if normal is None:
        print(f"unknown plane in circle: {plane}")
        return None

    transform = _make_axis_transform(pos, rot, (x, y, z), (0, 0, 1), normal)
    return CircleShape(radius=radius, segments=DEFAULT_CIRCLE_SEGMENTS, transform=transform)


def _parse_polyhedron(drawcall, transform):
    faces_vertices_json = drawcall["args"]
    if isinstance(faces_vertices_json, list):
        faces_vertices_json = faces_vertices_json[0]

    parsed = json.loads(faces_vertices_json)
    vertices = np.array(parsed["vertices"], dtype=np.float32)
    indices = triangulate_faces(parsed["faces"])
    return PolyhedronShape(vertices=vertices, indices=indices, transform=transform)


DRAWCALL_PARSERS = {
    "box": _parse_box,
    "cylinder": _parse_cylinder,
    "cone": _parse_cone,
    "circle": _parse_circle,
    "polyhedron": _parse_polyhedron,
}


# ---------------------------------------------------------------------------
# Geometry-guess factories
# ---------------------------------------------------------------------------

def _get_param(comp, name, instr_parameters=None):
    """Get a numeric parameter value, resolving expressions if needed."""
    val = getattr(comp, name, None)
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        return safe_eval(val, instr_parameters)
    return float(val)


def _factory_sphere(comp, instr_parameters=None):
    """Create a SphereShape from a 'radius' parameter."""
    radius = _get_param(comp, "radius", instr_parameters)
    if radius is None or radius <= 0:
        return None
    return SphereShape(radius=radius)


def _factory_cylinder(comp, instr_parameters=None):
    """Create a CylinderShape from radius + yheight."""
    radius = _get_param(comp, "radius", instr_parameters)
    height = _get_param(comp, "yheight", instr_parameters)
    if radius is None or radius <= 0 or height is None or height <= 0:
        return None
    return CylinderShape(radius=radius, height=height, radial_segments=DEFAULT_RADIAL_SEGMENTS)


def _factory_solid_box(comp, instr_parameters=None):
    """Create a solid BoxShape from xwidth, yheight, zdepth."""
    xwidth = _get_param(comp, "xwidth", instr_parameters)
    yheight = _get_param(comp, "yheight", instr_parameters)
    zdepth = _get_param(comp, "zdepth", instr_parameters)
    if xwidth is None or xwidth <= 0:
        return None
    if yheight is None or yheight <= 0:
        return None
    if zdepth is None or zdepth <= 0:
        return None
    return BoxShape(width=xwidth, height=yheight, depth=zdepth)


def _factory_rectangle_outline_xy(comp, instr_parameters=None):
    """Create a rectangle outline (LineSegmentsShape) from xwidth + yheight."""
    xwidth = _get_param(comp, "xwidth", instr_parameters)
    yheight = _get_param(comp, "yheight", instr_parameters)
    if xwidth is None or xwidth <= 0 or yheight is None or yheight <= 0:
        return None
    hw, hh = xwidth / 2, yheight / 2
    points = np.array([
        [hw, hh, 0], [hw, -hh, 0],
        [hw, -hh, 0], [-hw, -hh, 0],
        [-hw, -hh, 0], [-hw, hh, 0],
        [-hw, hh, 0], [hw, hh, 0],
    ], dtype=np.float32)
    return LineSegmentsShape(points=points)
    
def _factory_rectangle_outline_zy(comp, instr_parameters=None):
    """Create a rectangle outline (LineSegmentsShape) from xwidth + yheight."""
    zdepth = _get_param(comp, "zdepth", instr_parameters)
    yheight = _get_param(comp, "yheight", instr_parameters)
    if zpdeth is None or zdepth <= 0 or yheight is None or yheight <= 0:
        return None
    hw, hh = zdepth / 2, yheight / 2
    points = np.array([
        [0, hh, hw], [0, -hh, hw],
        [0, -hh, hw], [0, -hh, -hw],
        [0, -hh, -hw], [0, hh, -hw],
        [0, hh, -hw], [0, hh, hw],
    ], dtype=np.float32)
    return LineSegmentsShape(points=points)


def _factory_axis_triad(comp, instr_parameters=None):
    """Create an axis triad for parameterless components."""
    axis_length = 1.0
    points = np.array([
        [0, 0, 0], [axis_length, 0, 0],
        [0, 0, 0], [0, axis_length, 0],
        [0, 0, 0], [0, 0, axis_length],
    ], dtype=np.float32)
    return LineSegmentsShape(points=points)


# ---------------------------------------------------------------------------
# Built-in rule registry
# ---------------------------------------------------------------------------

def _make_builtin_registry() -> GeometryRuleRegistry:
    """Build the default registry of geometry-guess rules."""
    reg = GeometryRuleRegistry()

    # 1. Sphere: must have 'radius', must NOT have xwidth/yheight/zdepth
    reg.register(GeometryRule(
        must_have={"radius": True},
        must_not_have={"xwidth": False, "yheight": False, "zdepth": False},
        must_be_set={"radius": True},
        priority=10,
        factory=_factory_sphere,
    ))

    # 2. Cylinder: radius + yheight set; optional xwidth/zdepth are not set
    reg.register(GeometryRule(
        must_have={"radius": True, "yheight": True},
        must_be_set={"radius": True, "yheight": True},
        must_not_be_set={"xwidth": False, "zdepth": False},
        priority=20,
        factory=_factory_cylinder,
    ))

    # 3. Solid box: must have xwidth, yheight, zdepth all set
    reg.register(GeometryRule(
        must_have={"xwidth": True, "yheight": True, "zdepth": True},
        must_be_set={"xwidth": True, "yheight": True, "zdepth": True},
        priority=30,
        factory=_factory_solid_box,
    ))

    # 4. Rectangle outline: must have xwidth and yheight set, zdepth not set
    reg.register(GeometryRule(
        must_have={"xwidth": True, "yheight": True},
        must_be_set={"xwidth": True, "yheight": True},
        must_not_be_set={"zdepth": False},
        priority=40,
        factory=_factory_rectangle_outline_xy,
    ))
    
    # 5. Rectangle outline: must have xwidth and yheight set, zdepth not set
    reg.register(GeometryRule(
        must_have={"zdepth": True, "yheight": True},
        must_be_set={"zdepth": True, "yheight": True},
        must_not_be_set={"xwidth": False},
        priority=50,
        factory=_factory_rectangle_outline_zy,
    ))

    # 6. Axis triad: no parameters at all
    reg.register(GeometryRule(
        require_empty_params=True,
        priority=900,
        factory=_factory_axis_triad,
    ))

    return reg


# Module-level default registry
_builtin_registry = _make_builtin_registry()


class ComponentModel:
    def __init__(self, component_object):
        self.comp = component_object
        self.shape_list = []
        self.loaded = False
        self.global_position = None
        self.rotation_matrix = None
        self.bounds = Bounds()
        self.size = self.bounds.extents
        self.center = self.bounds.center
        self.bounding_radius = self.bounds.radius

    def refresh_metadata(self):
        """Finalize model-owned styles and world-space geometry metadata."""
        for shape in self.shape_list:
            if shape.style is None:
                shape.style = default_style_for_shape(shape)

        self.bounds = component_bounds(self.shape_list)
        self.size = self.bounds.extents
        self.center = self.bounds.center
        self.bounding_radius = self.bounds.radius

    def load_geometry_from_mcdisplay_dict(self, json_dict):
        """
        Takes component dict from mcdisplay-webgl json output.
        Adds shape objects to shape_list.
        Lines are added as line segments: p1->p2->p3 is stored as p1->p2, p2->p3.
        """
        pos, rot = pos_rot_from_list(json_dict["m4"])
        self.global_position = pos
        self.rotation_matrix = rot
        self.shape_list = []

        transform = Transform(position=pos, rotation_matrix=rot)

        line_points = None
        for drawcall in json_dict["drawcalls"]:
            key = drawcall["key"]

            if key == "multiline":
                segment_points = _parse_multiline(drawcall, pos, rot)
                if line_points is None:
                    line_points = segment_points
                else:
                    line_points = np.vstack((line_points, segment_points))
                continue

            parser = DRAWCALL_PARSERS.get(key)
            if parser is None:
                print(f"didn't know this drawclass: {key}")
                continue

            if key == "polyhedron":
                shape = parser(drawcall, transform)
            else:
                shape = parser(drawcall, pos, rot)

            if shape is not None:
                self.shape_list.append(shape)

        if line_points is not None:
            self.shape_list.append(LineSegmentsShape(transform=transform, points=line_points))

        self.refresh_metadata()
        self.loaded = True

    def set_global_transform(self, transform):
        """Set the global transform and apply it to all guessed shapes."""
        self.global_position = transform.position
        self.rotation_matrix = transform.rotation_matrix
        for shape in self.shape_list:
            shape.transform = transform
        self.refresh_metadata()

    def guess_geometry_from_comp_object(
        self,
        instr_parameters: dict | None = None,
        registry: GeometryRuleRegistry | None = None,
    ) -> bool:
        """
        Takes component object, attempts to guess geometry from parameters.
        Adds shape objects to shape_list.

        Uses the rule-based system: iterates through registered GeometryRule
        instances in priority order, and uses the first matching rule's factory
        to create a shape.

        Parameters
        ----------
        instr_parameters : dict, optional
            Instrument-level parameter values for expression resolution.
        registry : GeometryRuleRegistry, optional
            Custom rule registry.  Uses the built-in registry if not given.

        Returns
        -------
        bool
            True if a shape was successfully created, False otherwise.

        Raises
        ------
        ValueError
            If the component has parameters but no rule matches (unknown
            parameterized component).
        """
        if registry is None:
            registry = _builtin_registry

        self.shape_list = []
        parameter_names = getattr(self.comp, "parameter_names", []) or []

        # Try to find a matching rule
        rule = registry.match(self.comp)

        if rule is not None and rule.factory is not None:
            shape = rule.factory(self.comp, instr_parameters)
            if shape is not None:
                self.shape_list.extend(shape if isinstance(shape, (list, tuple)) else [shape])
                if self.global_position is not None or self.rotation_matrix is not None:
                    self.set_global_transform(Transform(
                        position=self.global_position,
                        rotation_matrix=self.rotation_matrix,
                    ))
                else:
                    self.refresh_metadata()
                self.loaded = True
                return True

        # No rule matched — check if this is a parameterized component
        if parameter_names:
            # Component has parameters but no rule matched -> report failure
            raise ValueError(
                f"Cannot guess geometry for component '{self.comp.name}' "
                f"(type '{getattr(self.comp, 'component_name', 'unknown')}'): "
                f"no matching geometry rule for parameters {parameter_names}"
            )

        # No parameters and no rule matched — fall back to axis triad
        axis_length = 1.0
        points = np.array([
            [0, 0, 0], [axis_length, 0, 0],
            [0, 0, 0], [0, axis_length, 0],
            [0, 0, 0], [0, 0, axis_length],
        ], dtype=np.float32)
        shape = LineSegmentsShape(points=points)
        self.shape_list.append(shape)
        self.refresh_metadata()
        self.loaded = True
        return True
