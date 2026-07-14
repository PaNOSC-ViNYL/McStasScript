import json

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
    triangulate_faces,
)
from mcstasscript.geometry_viewer.config import (
    DEFAULT_RADIAL_SEGMENTS,
    DEFAULT_CIRCLE_SEGMENTS,
)


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


class ComponentModel:
    def __init__(self, component_object):
        self.comp = component_object
        self.shape_list = []
        self.loaded = False
        self.global_position = None
        self.rotation_matrix = None

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

        self.loaded = True

    def guess_geometry_from_comp_object(self, instr_parameters=None):
        """
        Takes component object, attempts to guess geometry from parameters.
        Adds shape objects to shape_list.
        """
        if len(self.comp.parameter_names) == 0:
            axis_length = 1.0
            points = np.array([
                [0, 0, 0], [axis_length, 0, 0],
                [0, 0, 0], [0, axis_length, 0],
                [0, 0, 0], [0, 0, axis_length],
            ])
            shape = LineSegmentsShape(points=points)
            self.shape_list.append(shape)
            return True

        specified_pars = {}
        for par in self.comp.parameter_names:
            par_value = getattr(self.comp, par)
            if par_value == self.comp.parameter_defaults[par]:
                specified_pars[par] = par_value

        def check_conditions(conditions, parameter_names, specified_pars):
            for par_name, requirement in conditions["has_pars"].items():
                if par_name in parameter_names != requirement:
                    return False
            for par_name, requirement in conditions["used_pars"].items():
                if par_name in specified_pars != requirement:
                    return False
            return True

        def evaluate(expression, parameters):
            try:
                return float(expression)
            except ValueError:
                try:
                    return eval(expression)
                except NameError:
                    if isinstance(expression, str):
                        for par, value in parameters.items():
                            expression = expression.replace(par, str(value))
                        return eval(expression)
            except Exception:
                raise RuntimeError("Could not evaluate ", expression)

        conditions = dict(
            has_pars=dict(xwidth=True, yheight=True, zdepth=False, l=False, length=False),
            used_pars=dict(xwidth=True, yheight=True, radius=False),
        )

        if check_conditions(conditions, self.comp.parameter_names, specified_pars):
            xwidth = evaluate(specified_pars["xwidth"], instr_parameters or {})
            yheight = evaluate(specified_pars["yheight"], instr_parameters or {})

            points = np.array([
                [xwidth / 2, yheight / 2, 0], [xwidth / 2, -yheight / 2, 0],
                [xwidth / 2, -yheight / 2, 0], [-xwidth / 2, -yheight / 2, 0],
                [-xwidth / 2, -yheight / 2, 0], [-xwidth / 2, yheight / 2, 0],
                [-xwidth / 2, yheight / 2, 0], [xwidth / 2, yheight / 2, 0],
            ])

            shape = LineSegmentsShape(points=points)
            self.shape_list.append(shape)
            return True

        self.loaded = True
        return True
