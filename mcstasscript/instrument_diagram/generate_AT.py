from mcstasscript.instrument_diagram.connections import ConnectionList
from mcstasscript.instrument_diagram.arrow import Arrow


def generate_AT_arrows(components, component_box_dict, box_names, color=None):
    """
    Generate Arrow objects related to the AT relationship of components
    """
    connections = ConnectionList()
    for component in components:
        origin = component_box_dict[component.name]
        if component.AT_reference is None:
            target = component_box_dict["ABSOLUTE"]
        elif component.AT_reference == "PREVIOUS":
            origin_index = box_names.index(component.name)
            target_index = origin_index - 1
            target = component_box_dict[box_names[target_index]]
        else:
            target = component_box_dict[component.AT_reference]

        connections.add(origin, target)

    connections.distribute_lane_numbers(box_names=box_names)

    arrows = []
    for connection in connections.get_connections():
        origin = connection.origin
        target = connection.target
        lane = connection.lane_number

        arrow = Arrow(origin, target, lane=lane, kind="AT")

        arrow.set_box_offset_origin(0.24)
        arrow.set_box_offset_target(-0.2)
        if color is None:
            arrow.color = "blue"
        else:
            arrow.color = color
        # arrow.set_linestyle("--")

        arrows.append(arrow)

    return arrows
