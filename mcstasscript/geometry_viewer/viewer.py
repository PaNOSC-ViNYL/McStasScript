import pythreejs as p3
import json

from mcstasscript.geometry_viewer.component_model import ComponentModel
from mcstasscript.geometry_viewer.pythree_materials import MaterialLibrary


class PyThreeGeometryModel:
    def __init__(self):
        self.mesh_objects = [] # Holds the mesh objects that are added to the scene

        default_colors = ["#ff0000", "#808080", "#00ff00", "#ffff00", "#0000ff",
                          "#ff00ff", "#00ffff", "#ffa500", "#444444", "#cccccc"]
        self.material_library = MaterialLibrary(colors=default_colors)

    def next_component(self):
        self.material_library.next()

    def add_meshs_from_model(self, model):
        """
        for shape in model.shape_list:
            self.group.add(shape.make_mesh(self.material_library))
        """
        children = [
            shape.make_mesh(self.material_library)
            for shape in model.shape_list
        ]

        self.mesh_objects += children

    def make_renderer(self, show_axes=True, width=900, height=600):
        scene = p3.Scene(children=[])
        ambient = p3.AmbientLight(intensity=1.0)
        scene.add(ambient)

        if show_axes:
            axes = p3.AxesHelper(size=1)
            scene.add(axes)

        scene.add(p3.Group(children=self.mesh_objects))

        camera = p3.PerspectiveCamera(
            position=[5, 3, 10], aspect=width / height, fov=50, near=0.01, far=2000
        )
        camera.lookAt([0, 0, 2])

        # Create renderer with orbit controls
        controls = p3.OrbitControls(controlling=camera)
        renderer = p3.Renderer(
            camera=camera, scene=scene, controls=[controls], width=width, height=height
        )

        return renderer

class InstrumentModel:
    def __init__(self):
        self.component_models = []

    def add_model(self, model):
        self.component_models.append(model)

    def make_PyThreeGeometry_model(self, index_min=None, index_max=None):

        if index_min is None:
            index_min = 0

        if index_max is None:
            index_max = len(self.component_models)

        py3_model = PyThreeGeometryModel()

        shape_classes = set()

        for index, component_model in enumerate(self.component_models):

            if index_min <= index < index_max:
                py3_model.add_meshs_from_model(component_model)
                py3_model.next_component()

                unique_class_names = {obj.__class__.__name__ for obj in component_model.shape_list}
                shape_classes = shape_classes.union(unique_class_names)


            """
            #print(component_model.comp.name)
            color = py3_model.color_cycler.get_color()
            material = p3.MeshBasicMaterial(
                color=color,
                transparent=True,
                opacity=0.8,
                depthWrite=False,
                side="DoubleSide",
                # depthTest=False
            )
            unique_class_names = {obj.__class__.__name__ for obj in component_model.shape_list}
            #print("n shapes", len(component_model.shape_list), unique_class_names)
            """

        print("materials in cache", len(py3_model.material_library._cache))
        print("shapes:", shape_classes)

        return py3_model


def view_with_guess(instrument_object):
    """
    Plots instrument geometry with best guesses of geometry

    Fail if location of a component can not be determined:
    - If non trivial declared variables used in AT / ROTATED
    - If non_trivial calculations are made in AT / ROTATED
    """

    instrument_model = InstrumentModel()
    for component in instrument_object.compnent_list:
        component_model = ComponentModel(component)
        component_model.guess_geometry_from_comp_object()

        instrument_model.add_model(component_model)

    p3_model = instrument_model.make_PyThreeGeometry_model()

    return p3_model.make_renderer()


def view_with_json(instrument_object, json_dict, index_min=None, index_max=None):
    """
    Plots instrument geometry with json input
    """

    instrument_model = InstrumentModel()

    for json_component in json_dict["components"]:
        name = json_component["name"]

        #if name not in  ["source", "sample"]:
        #    continue

        component_object = None
        for comp in instrument_object.component_list:
            if comp.name == name:
                component_object = comp
                break

        if component_object is None:
            raise ValueError(f"Component {name} not found in instrument object.")

        component_model = ComponentModel(component_object)
        component_model.load_geometry_from_mcdisplay_dict(json_component)

        instrument_model.add_model(component_model)

    p3_model = instrument_model.make_PyThreeGeometry_model(index_min=index_min,
                                                           index_max=index_max)

    return p3_model.make_renderer()


def view(instrument_object, json_dict=None, json_file=None,
         index_min=None, index_max=None):
    """
    Plots quick geometry if possible, runs mcdisplay if necessary
    """

    if json_file is not None:
        with open(json_file, "r") as f:
            json_dict = json.load(f)

        return view_with_json(instrument_object, json_dict,
                              index_min=index_min, index_max=index_max)


    """
    try:
        view_with_guess(instrument_object)
    except:
        view_with_json(instrument_object, json_dict)
    """

