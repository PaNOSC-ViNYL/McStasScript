import pythreejs as p3
import ipywidgets as ipw
import json
import os
import copy

from mcstasscript.geometry_viewer.component_model import ComponentModel
from mcstasscript.geometry_viewer.pythree_specific import PyThreeGeometryModel
from mcstasscript.geometry_viewer.mcdisplay_runner import generate_json


class InstrumentModel:
    def __init__(self, instrument_object=None, json_dict=None):
        self.component_models = []

        if json_dict is not None and instrument_object is not None:
            for json_component in json_dict["components"]:
                name = json_component["name"]
                component_object = instrument_object.get_component(name)
                component_model = ComponentModel(component_object)
                component_model.load_geometry_from_mcdisplay_dict(json_component)
                self.component_models.append(component_model)

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
                py3_model.add_component_model(component_model)
                py3_model.next_component()

                unique_class_names = {obj.__class__.__name__ for obj in component_model.shape_list}
                shape_classes = shape_classes.union(unique_class_names)

        #print("materials in cache", len(py3_model.material_library._cache))
        #print("shapes:", shape_classes)

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

    instrument_model = InstrumentModel(instrument_object=instrument_object, json_dict=json_dict)

    p3_model = instrument_model.make_PyThreeGeometry_model(index_min=index_min,
                                                           index_max=index_max)

    renderer = p3_model.make_renderer()

    navigator = p3_model.create_component_navigator(renderer)

    return ipw.VBox([navigator, renderer])


def view(instrument_object, json_dict=None, json_file=None,
         index_min=None, index_max=None):
    """
    Plots quick geometry if possible, runs mcdisplay if necessary
    """

    if json_file is None:

        json_folder = generate_json(instrument_object)
        json_file = os.path.join(json_folder, "instrument.json")

        if json_file is None:
            return RuntimeError("Generating json file failed.")

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

