import numpy as np

from mcstasscript.geometry_viewer.shapes import LineShape
from mcstasscript.geometry_viewer.shapes import BoxShape
from mcstasscript.geometry_viewer.shapes import CylinderShape
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

        Adds shape objects to shape_list
        """

        pos, R  = pos_rot_from_list(json_dict["m4"])

        self.global_position = pos
        self.rotation_matrix = R

        self.shape_list = []

        shape = None
        for drawcall in json_dict["drawcalls"]:
            if drawcall["key"] == "multiline":
                args = drawcall["args"]

                points = np.array(args, dtype=np.float32).reshape((-1, 3))
                points = points @ self.rotation_matrix

                shape = LineShape(points)

            if drawcall["key"] == "box":
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

                shape = BoxShape(width=xwidth, height=yheight, depth=zdepth)

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

                shape = CylinderShape(radius=radius, height=height,
                                      radial_segments=32,
                                      align_axis=(nx, ny, nz))

            elif drawcall["key"] == "polyhedron":
                faces_vertices_json = drawcall["args"]

                PolyhedronShape(faces_vertices_json=faces_vertices_json)

            else:
                pass
                # Currently allow unknown drawcalls while writing

            if shape is not None:
                self.shape_list.append(shape)

        self.loaded = True

    def guess_geometry_from_comp_object(self):
        """
        Takes component object

        Adds shape objects to shape_list
        """

        self.shape_list = []

        self.loaded = True
