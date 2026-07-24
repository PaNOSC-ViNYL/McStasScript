from mcstasscript.geometry_viewer.model.component import ComponentModel
from mcstasscript.geometry_viewer.model.bounds import Bounds


class InstrumentModel:
    def __init__(self, instrument_object=None, json_dict=None, index_max=None, verbose=True):
        self.component_models = []
        self.bounds = Bounds()

        if json_dict is not None and instrument_object is not None:
            components = json_dict["components"]
            if index_max is not None:
                components = components[:index_max]
            for json_component in components:
                name = json_component["name"]
                component_object = instrument_object.get_component(name)
                component_model = ComponentModel(component_object)
                component_model.load_geometry_from_mcdisplay_dict(json_component, verbose=verbose)
                self.add_model(component_model)

    def add_model(self, model):
        model.refresh_metadata()
        self.component_models.append(model)
        self.refresh_metadata()

    def refresh_metadata(self):
        self.bounds = Bounds()
        for component in self.component_models:
            component.refresh_metadata()
            if not component.bounds.is_empty:
                self.bounds.include(component.bounds.minimum)
                self.bounds.include(component.bounds.maximum)
