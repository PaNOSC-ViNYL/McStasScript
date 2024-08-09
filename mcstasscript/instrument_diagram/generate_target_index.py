from mcstasscript.instrument_diagram.connections import ConnectionList
from mcstasscript.instrument_diagram.arrow import Arrow


def generate_target_index_arrows(components, component_box_dict, box_names, color=None):
    """
    Generate Arrow objects related to the target_index
    """
    connections = ConnectionList()
    component_names = [x.name for x in components]

    for component in components:
        if not hasattr(component, "target_index"):
            # Component doesnt have the target_index setting
            continue
        if component.target_index is None:
            # A value has not been specified for target_index setting
            continue
        if component.target_index == 0:
            # target_index is disabled
            continue

        try:
            int(component.target_index)
        except:
            # Skip cases where target_index is not an integer
            continue

        this_component_index = component_names.index(component.name)
        target_component_index = this_component_index + int(component.target_index)
        target_component_reference = component_names[target_component_index]

        if target_component_reference not in component_box_dict:
            raise ValueError("target_index reference: "
                             + str(target_component_reference)
                             + " not found.")

        origin = component_box_dict[component.name]
        connections.add(origin, component_box_dict[target_component_reference])

    connections.distribute_lane_numbers(box_names=box_names)

    arrows = []
    for connection in connections.get_connections():
        origin = connection.origin
        target = connection.target
        lane = connection.lane_number + 3  # Make room for target_index

        arrow = Arrow(origin, target, lane=lane, kind="target_index", description="target_index")
        arrow.set_sub_lane(2)
        if color is None:
            arrow.color = "black"
        else:
            arrow.color = color

        arrows.append(arrow)

    return arrows
