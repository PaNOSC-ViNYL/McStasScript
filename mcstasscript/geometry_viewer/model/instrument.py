from mcstasscript.geometry_viewer.model.component import ComponentModel


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
