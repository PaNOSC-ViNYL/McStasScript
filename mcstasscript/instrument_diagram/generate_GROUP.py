from mcstasscript.instrument_diagram.connections import ConnectionList
from mcstasscript.instrument_diagram.arrow import Arrow


def generate_GROUP_arrows(components, component_box_dict, box_names, color=None):
    """
    Generate Arrow objects related to the GROUP keyword
    """
    connections = ConnectionList()

    groups = {}
    for component in components:
        if component.GROUP != "":
            group_reference = component.GROUP
            if group_reference not in groups:
                groups[group_reference] = [component_box_dict[component.name]]
            else:
                groups[group_reference].append(component_box_dict[component.name])

    for group_name, group_members in groups.items():
        if len(group_members) == 1:
            # Meaningless group
            continue
        base = group_members[0]
        connected_list = group_members[1:]

        for connected in connected_list:
            connections.add(connected, base, info=group_name)

    connections.distribute_lane_numbers(box_names=box_names)

    arrows = []
    for connection in connections.get_connections():
        origin = connection.origin
        target = connection.target
        lane = connection.lane_number + 2  # Make room for group name
        group_name = connection.info

        arrow = Arrow(origin, target, lane=lane, kind="GROUP", description=group_name)
        arrow.set_connection(True)
        if color is None:
            arrow.color = [0.4, 0.4, 0.4]
        else:
            arrow.color = color

        arrows.append(arrow)

    return arrows
