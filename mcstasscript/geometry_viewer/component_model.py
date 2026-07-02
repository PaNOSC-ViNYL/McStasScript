import numpy as np

from mcstasscript.geometry_viewer.helpers import Transform
from mcstasscript.geometry_viewer.helpers import quaternion_from_vectors

from mcstasscript.geometry_viewer.shapes import LineShape
from mcstasscript.geometry_viewer.shapes import LineSegmentsShape
from mcstasscript.geometry_viewer.shapes import BoxShape
from mcstasscript.geometry_viewer.shapes import CircleShape
from mcstasscript.geometry_viewer.shapes import CylinderShape
from mcstasscript.geometry_viewer.shapes import ConeShape
from mcstasscript.geometry_viewer.shapes import PolyhedronShape
from mcstasscript.geometry_viewer.helpers import pos_rot_from_list

class ComponentModel:
    def __init__(self, component_object):
        """
        Holds geometry model of a group
        """
        self.comp = component_object

        self.shape_list = []
        self.loaded = False

        self.global_position = None
        self.rotation_matrix = None

    def load_geometry_from_mcdisplay_dict(self, json_dict):
        """
        Takes component dict from mcdisplay-webgl json output

        Adds shape objects to shape_list.
        Lines are added as line segments, so p1->p2->p3 is stored as
        p1->p2 - p2->p3 which plays well with PyThreejs LineSegments.
        """

        pos, rot  = pos_rot_from_list(json_dict["m4"])

        self.global_position = pos
        self.rotation_matrix = rot

        self.shape_list = []

        transform = Transform(position=pos, rotation_matrix=rot)

        points = None
        shape = None
        for drawcall in json_dict["drawcalls"]:
            if drawcall["key"] == "multiline":
                args = drawcall["args"]

                new_points = np.array(args, dtype=np.float32).reshape((-1, 3))

                if len(new_points) <= 2:
                    segment_points = new_points
                else:
                    segment_points = np.empty((2 * (len(new_points) - 1), 3), dtype=np.float32)
                    segment_points[0::2] = new_points[:-1]
                    segment_points[1::2] = new_points[1:]

                if points is None:
                    points = segment_points
                else:
                    points = np.vstack((points, segment_points))

                shape = None

            elif drawcall["key"] == "box":
                args = drawcall["args"]

                x = args[0]
                y = args[1]
                z = args[2]
                xwidth = args[3]
                yheight = args[4]
                zdepth = args[5]
                thickness = args[6]
                nx = args[7]
                ny = args[8]
                nz = args[9]

                quaternion = quaternion_from_vectors(
                    (0, 1, 0),  # default box axis
                    (nx, ny, nz),
                )

                this_transform = Transform(position=pos + np.array([x, y, z]) @ rot.T,
                                           quaternion=quaternion, rotation_matrix=rot)

                shape = BoxShape(width=xwidth, height=yheight, depth=zdepth,
                                 transform=this_transform)

            elif drawcall["key"] == "cylinder":
                args = drawcall["args"]

                x = args[0]
                y = args[1]
                z = args[2]
                radius = args[3]
                height = args[4]
                thickness = args[5]
                nx = args[6]
                ny = args[7]
                nz = args[8]

                quaternion = quaternion_from_vectors(
                    (0, 1, 0),  # default cylinder axis
                    (nx, ny, nz),
                )

                this_transform = Transform(position=pos + np.array([x, y, z]) @ rot.T,
                                           quaternion=quaternion, rotation_matrix=rot)

                shape = CylinderShape(radius=radius, height=height,
                                      radial_segments=32,
                                      transform=this_transform)

            elif drawcall["key"] == "cone":
                args = drawcall["args"]

                x = args[0]
                y = args[1]
                z = args[2]
                radius = args[3]
                height = args[4]
                nx = args[5]
                ny = args[6]
                nz = args[7]

                quaternion = quaternion_from_vectors(
                    (0, 1, 0),  # default cone axis
                    (nx, ny, nz),
                )

                this_transform = Transform(position=pos + np.array([x, y, z]) @ rot.T,
                                           quaternion=quaternion, rotation_matrix=rot)

                shape = ConeShape(radius=radius, height=height,
                                  radial_segments=32,
                                  transform=this_transform)

            elif drawcall["key"] == "circle":
                args = drawcall["args"]

                plane = args[0]
                x = args[1]
                y = args[2]
                z = args[3]
                radius = args[4]

                nx = 0
                ny = 0
                nz = 0
                if plane == "xy":
                    nz = 1
                elif plane == "xz":
                    ny = 1
                elif plane == "yz":
                    nx = 1
                else:
                    print("unknown plane in circle")

                quaternion = quaternion_from_vectors(
                    (0, 0, 1),  # default circle axis
                    (nx, ny, nz),
                )

                this_transform = Transform(position=pos + np.array([x,y,z]) @ rot.T,
                                           quaternion=quaternion, rotation_matrix=rot)

                shape = CircleShape(radius=radius,
                                    segments=64,
                                    transform=this_transform)

            elif drawcall["key"] == "polyhedron":
                faces_vertices_json = drawcall["args"]

                shape = PolyhedronShape(faces_vertices_json=faces_vertices_json,
                                        transform=transform)

            else:
                print("didn't know this drawclass: ", drawcall["key"])
                # Currently allow unknown drawcalls while writing

            if shape is not None:
                self.shape_list.append(shape)

        if points is not None:
            shape = LineSegmentsShape(transform=transform, points=points)
            self.shape_list.append(shape)

        self.loaded = True

    def guess_geometry_from_comp_object(self):
        """
        Takes component object

        Adds shape objects to shape_list
        """

        self.shape_list = []

        self.loaded = True
