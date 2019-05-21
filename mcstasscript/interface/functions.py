from mcstasscript.data.data import McStasData

def name_search(name, data_list):
    """"
    name_search returns McStasData instance with specific name if it is
    in the given data_list

    The index of certain datasets in the data_list can change if
    additional monitors are added so it is more convinient to access
    the data files using their names.

    Parameters
    ----------
    name : string
        Name of the dataset to be retrived (component_name)

    data_list : List of McStasData instances
        List of datasets to search
    """
    
    if type(data_list) is not list:
        raise InputError(
            "name_search function needs list of McStasData as input")

    if not type(data_list[0]) == McStasData:
        raise InputError(
            "name_search function needs objects of type McStasData as input.")

    list_result = []
    for check in data_list:
        if check.metadata.component_name == name:
            list_result.append(check)

    if len(list_result) == 1:
        return list_result[0]
    else:
        raise NameError("More than one match for the name search")

def name_plot_options(name, data_list, **kwargs):
    """"
    name_plot_options passes keyword arguments to dataset with certain
    name in given data list

    Function for quickly setting plotting options on a certain dataset
    n a larger list of datasets

    Parameters
    ----------
    name : string
        Name of the dataset to be modified (component_name)

    data_list : List of McStasData instances
        List of datasets to search

    kwargs : keyword arguments
        Keyword arguments passed to set_plot_options in
        McStasPlotOptions
    """

    object_to_modify = name_search(name, data_list)
    object_to_modify.set_plot_options(**kwargs)
