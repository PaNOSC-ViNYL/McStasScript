from mcstasscript.instrument_diagram.connections import ConnectionList
from mcstasscript.instrument_diagram.arrow import Arrow


def generate_Union_arrows(components, component_box_dict, box_names, component_categories, color=None):
    """
    Generate Arrow objects related to use of Union components

    Currently supports processes, materials, geometries and master. Can be
    expanded to also support loggers, abs_loggers and conditionals.
    """
    connections = ConnectionList()

    process_names = []
    material_names = []
    geometry_names = []
    simulated_geometry_names = []
    abs_loggers = []
    loggers = []
    conditionals = []
    master_names = []
    geometry_activation_counters = {}
    for component in components:
        category = component_categories[component.component_name]
        if category == "union" or True:
            if "_process" in component.component_name:
                # Process component
                process_names.append(component.name)

            elif component.component_name == "Union_make_material":
                # Make material component
                material_names.append(component.name)

                process_string = component.process_string
                if not isinstance(process_string, str):
                    continue

                processes = process_string.strip('"').split(",")
                for process in processes:
                    if process not in process_names:
                        print("Didn't find process of name '" + process + "'")
                        print(process_names)
                    else:
                        origin = component_box_dict[process]
                        connections.add(origin, component_box_dict[component.name])

            elif "material_string" in component.parameter_names:
                # Geometry
                geometry_names.append(component.name)

                if component.number_of_activations is not None:
                    try:
                        # If a number is given, it can be used directly
                        number_of_activations = int(component.number_of_activations)
                    except:
                        # If a variable or parameter is used, it can't be known ahead of time, assume 1
                        number_of_activations = 1
                else:
                    number_of_activations = component.parameter_defaults["number_of_activations"]

                geometry_activation_counters[component.name] = number_of_activations

                if component.material_string is not None:
                    simulated_geometry_names.append(component.name)

                if isinstance(component.material_string, str):
                    material = component.material_string.strip('"')
                    if material not in material_names:
                        if material not in ["Vacuum", "vacuum", "Exit", "exit"]:
                            print("Didn't find material of name '" + material + "'")
                            print(material_names)
                    else:
                        origin = component_box_dict[material]
                        connections.add(origin, component_box_dict[component.name])

                if isinstance(component.mask_string, str):
                    masks = component.mask_string.strip('"').split(",")
                    for mask in masks:
                        if mask not in geometry_names:
                            print("Didn't find geometry target of name '" + mask + "'")
                            print(geometry_names)
                        else:
                            target = component_box_dict[mask]
                            connections.add(component_box_dict[component.name], target)

            elif "_logger" in component.component_name:

                if "_abs_logger" in component.component_name:
                    # Absoption logger
                    abs_loggers.append(component.name)
                    abs_logger = True
                else:
                    # Scattering logger
                    loggers.append(component.name)
                    abs_logger = False

                target_geometry = component.target_geometry
                if isinstance(target_geometry, str):
                    geometries = target_geometry.strip('"').split(",")
                    for geometry in geometries:
                        if geometry not in simulated_geometry_names:
                            print(component.name)
                            print("Didn't find geometry of name '" + geometry + "'")
                            print(simulated_geometry_names)
                        else:
                            origin = component_box_dict[geometry]
                            connections.add(origin, component_box_dict[component.name])

                if abs_logger:
                    # Abs loggers do not have target_process, as they target absorption
                    continue

                target_process = component.target_process
                if isinstance(target_process, str):
                    processes = target_process.strip('"').split(",")
                    for process in processes:
                        if process not in process_names:
                            print(component.name)
                            print("Didn't find process of name '" + process + "'")
                            print(process_names)
                        else:
                            origin = component_box_dict[process]
                            connections.add(origin, component_box_dict[component.name])

            elif "target_loggers" in component.parameter_names:
                # Conditional
                conditionals.append(component.name)

                target_loggers = component.target_loggers
                if isinstance(target_loggers, str):
                    loggers = target_loggers.strip('"').split(",")
                    for logger in loggers:
                        if logger not in loggers + abs_loggers:
                            print(component.name)
                            print("Didn't find logger with name '" + logger + "'")
                            print(loggers, abs_loggers)
                        else:
                            target = component_box_dict[logger]
                            connections.add(component_box_dict[component.name], target)

            elif component.component_name == "Union_master":
                # Master
                master_names.append(component.name)

                for geometry in simulated_geometry_names:
                    if geometry_activation_counters[geometry] > 0:  # May need to account for floating point precision
                        # Only include if activation counter for this geometry is still positive
                        geometry_activation_counters[geometry] -= 1

                        origin = component_box_dict[geometry]
                        connections.add(origin, component_box_dict[component.name])

    connections.distribute_lane_numbers(box_names=box_names)

    arrows = []
    for connection in connections.get_connections():
        origin = connection.origin
        target = connection.target
        lane = connection.lane_number

        arrow = Arrow(origin, target, lane=lane, kind="Union")
        arrow.set_sub_lane(2)

        if color is None:
            arrow.color = "green"
        else:
            arrow.color = color

        if target.name in master_names:
            arrow.set_linestyle("--")

        arrows.append(arrow)

    return arrows
