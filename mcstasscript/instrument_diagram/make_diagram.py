import copy

from mcstasscript.instrument_diagram.box import ComponentBox
from mcstasscript.instrument_diagram.generate_AT import generate_AT_arrows
from mcstasscript.instrument_diagram.generate_ROTATED import generate_ROTATED_arrows
from mcstasscript.instrument_diagram.generate_JUMP import generate_JUMP_arrows
from mcstasscript.instrument_diagram.generate_target_index import generate_target_index_arrows
from mcstasscript.instrument_diagram.generate_GROUP import generate_GROUP_arrows
from mcstasscript.instrument_diagram.generate_Union import generate_Union_arrows
from mcstasscript.instrument_diagram.canvas import DiagramCanvas
from mcstasscript.instrument_diagnostics.intensity_diagnostics import IntensityDiagnostics


def instrument_diagram(instrument, analysis=False, variable=None, limits=None):
    """
    Plots diagram of components in instrument with RELATIVE connections

    All components in the instrument are shown as text fields and arrows are
    drawn showing the AT RELATIVE and ROTATED RELATIVE connections between
    components. When more advanced features are used, these are displayed
    with arrows on the right side of the diagram, currently JUMP, GROUP and
    use of Union components are visualized.

    Parameters
    ----------

    instrument : McCode_instr
        Instrument object from which the component list is taken
    """

    # Grab components from instrument file and make text box objects
    components = instrument.make_component_subset()

    # Prepare legend
    component_reader = instrument.component_reader
    component_categories = copy.deepcopy(component_reader.component_category)

    absolute_box = ComponentBox("ABSOLUTE")
    component_boxes = [absolute_box]
    component_box_dict = {"ABSOLUTE": absolute_box}
    for component in components:
        box = ComponentBox(component)
        component_boxes.append(box)
        component_box_dict[component.name] = box

    box_names = [x.name for x in component_boxes]

    color_choices = {"AT": "blue", "ROTATED": "red", "JUMP": "black", "GROUP": [0.4, 0.4, 0.4], "Union": "green"}

    # Arrows for the left side of the diagram
    AT_arrows = generate_AT_arrows(components, component_box_dict, box_names, color=color_choices["AT"])
    ROTATED_arrows = generate_ROTATED_arrows(components, component_box_dict, box_names, color=color_choices["ROTATED"])

    # Arrow for the right side of the diagram
    try:
        JUMP_arrows = generate_JUMP_arrows(components, component_box_dict, box_names, color=color_choices["JUMP"])
    except:
        JUMP_arrows = []
        print("Generation of JUMP arrows failed, please send bug report.")

    try:
        target_index_arrows = generate_target_index_arrows(components, component_box_dict,
                                                           box_names, color=color_choices["JUMP"])
    except:
        target_index_arrows = []
        print("Generation of target_index arrows failed, please send bug report.")

    try:
        GROUP_arrows = generate_GROUP_arrows(components, component_box_dict, box_names, color=color_choices["GROUP"])
    except:
        GROUP_arrows = []
        print("Generation of GROUP arrows failed, please send bug report.")

    try:
        Union_arrows = generate_Union_arrows(components, component_box_dict, box_names,
                                             component_categories, color=color_choices["Union"])
    except:
        Union_arrows = []
        print("Generation of Union arrows failed, please send bug report.")

    intensity_diagnostics=None
    if analysis or variable is not None:
        intensity_diagnostics = IntensityDiagnostics(instrument)
        intensity_diagnostics.settings(suppress_output=True)

    # Create canvas
    canvas = DiagramCanvas(AT_arrows + ROTATED_arrows, component_boxes,
                           JUMP_arrows + target_index_arrows + GROUP_arrows + Union_arrows,
                           component_categories=component_categories, colors=color_choices,
                           intensity_diagnostics=intensity_diagnostics, variable=variable,
                           limits=limits)

    # Plot diagram
    canvas.plot()