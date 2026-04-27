import pythreejs as p3

from mcstasscript.geometry_viewer.component_model import ComponentModel



class PyThreeGeometryModel:
    def __init__(self):
        self.group = p3.Group()

    def add_mesh(self, mesh):
        self.group.add(mesh)

    def make_renderer(self, show_axes, width=900, height=600):
        scene = p3.Scene(children=[])
        ambient = p3.AmbientLight(intensity=1.0)
        scene.add(ambient)

        if show_axes:
            axes = p3.AxesHelper(size=1)
            scene.add(axes)

        scene.add(self.group)

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

    def make_PyThreeGeometry_model(self):

        py3_model = PyThreeGeometryModel()
        for component_model in self.component_models:
            for shape in component_model.shape_list:
                py3_model.add_mesh(shape.make_mesh())

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


def view_with_json(instrument_object, json_dict):
    """
    Plots instrument geometry with json input
    """

    instrument_model = InstrumentModel()

    for json_component in json_dict["components"]:
        name = json_component["name"]

        component_object = None
        for comp in instrument_object.compnent_list:
            if comp.name == name:
                component_object = comp
                break

        if component_object is None:
            raise ValueError(f"Component {name} not found in instrument object.")

        component_model = ComponentModel(component_object)
        component_model.load_geometry_from_mcdisplay_dict(json_component)

        instrument_model.add_model(component_model)
        p3_model = instrument_model.make_PyThreeGeometry_model()

        return p3_model.make_renderer()

    for component in instrument_object.compnent_list:
        component_model = ComponentModel(component)
        component_model.guess_geometry_from_comp_object()

        instrument_model.add_model(component_model)

    p3_model = instrument_model.make_PyThreeGeometry_model()

    return p3_model.make_renderer()


def view(instrument_object, json_dict=None):
    """
    Plots quick geometry if possible, runs mcdisplay if necessary
    """

    try:
        view_with_guess(instrument_object)
    except:
        view_with_json(instrument_object, json_dict)

