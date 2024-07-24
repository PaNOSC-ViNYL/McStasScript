

def has_component(instrument, component_name=None, component_type=None):
    if component_name is None and component_type is None:
        raise ValueError("Specify component_name, component_type or both.")

    # Run through components in instrument
    for comp in instrument.component_list:
        if component_name is not None:
            if comp.name != component_name:
                continue

        if component_type is not None:
            if comp.component_name != component_type:
                continue

        # Found case where both component name and type matches
        return True

    # Did not find any such component
    return False