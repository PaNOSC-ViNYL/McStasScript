from mcstasscript.instrument_diagram.connections import ConnectionList
from mcstasscript.instrument_diagram.arrow import Arrow


def generate_ROTATED_arrows(components, component_box_dict, box_names, color=None):
    """
    Generate Arrow objects related to the ROTATED relationship of components
    """
    connections = ConnectionList()
    lane_numbers = {}
    for component in components:
        if not component.ROTATED_specified:
            continue

        origin = component_box_dict[component.name]
        if component.ROTATED_reference is None:
            target = component_box_dict["ABSOLUTE"]
        elif component.ROTATED_reference == "PREVIOUS":
            origin_index = box_names.index(component.name)
            target_index = origin_index - 1
            target = component_box_dict[box_names[target_index]]
        else:
            target = component_box_dict[component.ROTATED_reference]

        connections.add(origin, target)

    connections.distribute_lane_numbers(box_names=box_names)

    arrows = []
    for connection in connections.get_connections():
        origin = connection.origin
        target = connection.target
        lane = connection.lane_number

        arrow = Arrow(origin, target, lane=lane, kind="ROTATED")

        arrow.set_sub_lane(1)
        arrow.set_box_offset_origin(0.16)
        arrow.set_box_offset_target(-0.05)
        if color is None:
            arrow.color = "red"
        else:
            arrow.color = color

        arrows.append(arrow)

    return arrows
