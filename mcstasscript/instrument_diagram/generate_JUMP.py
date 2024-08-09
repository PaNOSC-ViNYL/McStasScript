from mcstasscript.instrument_diagram.connections import ConnectionList
from mcstasscript.instrument_diagram.arrow import Arrow


def generate_JUMP_arrows(components, component_box_dict, box_names, color=None):
    """
    Generate Arrow objects related to the JUMP keyword
    """
    connections = ConnectionList()

    for component in components:
        if component.JUMP != "":
            jump_reference = component.JUMP.split(" ")[0]
            if jump_reference not in component_box_dict:
                raise ValueError("JUMP reference: " + str(jump_reference)
                                 + " not found.")

            origin = component_box_dict[component.name]
            connections.add(origin, component_box_dict[jump_reference])

    connections.distribute_lane_numbers(box_names=box_names)

    arrows = []
    for connection in connections.get_connections():
        origin = connection.origin
        target = connection.target
        lane = connection.lane_number + 2  # Make room for group name

        arrow = Arrow(origin, target, lane=lane, kind="JUMP", description="JUMP")
        arrow.set_sub_lane(1)
        if color is None:
            arrow.color = "black"
        else:
            arrow.color = color

        arrows.append(arrow)

    return arrows
