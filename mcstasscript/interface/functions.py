import yaml
import os

from mcstasscript.data.data import McStasData
import mcstasscript.helper.managed_mcrun as managed_mcrun


def name_search(name, data_list):
    """"
    name_search returns McStasData instance with specific name if it is
    in the given data_list. If no match is found, a search for the data
    filename is performed. If several matches are found, a list of
    McStasData objects are returned.

    The index of certain datasets in the data_list can change if
    additional monitors are added so it is more convenient to access
    the data files using their names.

    Parameters
    ----------
    name : string
        Name of the dataset to be retrieved (component_name)

    data_list : List of McStasData instances
        List of datasets to search
    """
    if type(data_list) is not list:
        raise RuntimeError(
            "name_search function needs list of McStasData as input.")

    if len(data_list) == 0:
        raise RuntimeError("Given data list empty.")

    if not isinstance(data_list[0], McStasData):
        raise RuntimeError(
            "name_search function needs objects of type McStasData as input.")

    # Search by component name
    list_result = []
    for check in data_list:
        if check.name == name:
            list_result.append(check)

    if len(list_result) == 0:
        # Search by filename
        for check in data_list:
            if check.metadata.filename == name:
                list_result.append(check)

    if len(list_result) == 0:
        raise NameError("No dataset with name: \""
                        + name
                        + "\" found.")

    if len(list_result) == 1:
        return list_result[0]
    else:
        return list_result


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
    if type(object_to_modify) is not list:
        object_to_modify.set_plot_options(**kwargs)
    else:
        for data_object in object_to_modify:
            data_object.set_plot_options(**kwargs)

def load_data(foldername):
    """
    Loads data from a McStas data folder including mccode.sim

    Parameters
    ----------
        foldername : string
            Name of the folder from which to load data
    """
    if not os.path.isdir(foldername):
        raise RuntimeError("Could not find specified foldername for"
                           + "load_data:" + str(foldername))

    return managed_mcrun.load_results(foldername)

def load_metadata(data_folder_name):
    """
    Function that loads metadata from a mcstas simulation

    Returns list of metadata objects corresponding to each monitor, all
    information is taken from mccode.sim file.

    Parameters
    ----------

    first argument : str
        path to folder from which metadata should be loaded
    """
    return managed_mcrun.load_metadata(data_folder_name)

def load_monitor(metadata, data_folder_name):
    """
    Function that loads data given metadata and name of data folder

    Loads data for single monitor and returns a McStasData object

    Parameters
    ----------

    metadata : McStasMetaData object
        McStasMetaData object corresponding to the monitor to be loaded

    data_folder_name : str
        path to folder from which metadata should be loaded
    """
    return managed_mcrun.load_monitor(metadata, data_folder_name)


class Configurator:
    """
    Class for setting the configuration file for McStasScript.

    Attributes
    ----------
    configuration_file_name : str
        absolute path of configuration file

    Methods
    -------
    set_mcstas_path(string)
        sets mcstas path

    set_mcrun_path(string)
        sets mcrun path

    set_mcxtrace_path(string)
        sets mcxtrace path

    set_mxrun_path(string)
        sets mxrun path

    set_line_length(int)
        sets maximum line length to given int

    _write_yaml(dict)
        internal method, writes a configuration yaml file with dict content

    _read_yaml()
        internal method, reads a configuration yaml file and returns a dict

    _create_new_config_file()
        internal method, creates default configuration file

    """

    def __init__(self, *args):
        """
        Initialization of configurator, checks that the configuration file
        actually exists, and if it does not, creates a default configuration
        file.

        Parameters
        ----------
        (optional) custom name : str
            Custom name for configuration file for testing purposes
        """

        if len(args) == 1:
            name = args[0]
        else:
            name = "configuration"

        # check configuration file exists
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        conf_file = os.path.join(THIS_DIR, "..", name + ".yaml")
        self.configuration_file_name = conf_file
        if not os.path.isfile(self.configuration_file_name):
            # no config file found, write default config file
            self._create_new_config_file()

    def _write_yaml(self, dictionary):
        """
        Writes a dictionary as the new configuration file
        """
        with open(self.configuration_file_name, 'w') as yaml_file:
            yaml.dump(dictionary, yaml_file, default_flow_style=False)

    def _read_yaml(self):
        """
        Reads yaml configuration file
        """
        with open(self.configuration_file_name, 'r') as ymlfile:
            return yaml.safe_load(ymlfile)

    def _create_new_config_file(self):
        """
        Writes a default configuration file to the package root directory
        """

        run = "/Applications/McStas-2.5.app/Contents/Resources/mcstas/2.5/bin/"
        mcstas = "/Applications/McStas-2.5.app/Contents/Resources/mcstas/2.5/"

        mxrun = "/Applications/McXtrace-1.5.app" \
                + "/Contents/Resources/mcxtrace/1.5/mxrun"
        mcxtrace = "/Applications/McXtrace-1.5.app" \
                   + "/Contents/Resources/mcxtrace/1.5/"

        default_paths = {"mcrun_path": run,
                         "mcstas_path": mcstas,
                         "mxrun_path": mxrun,
                         "mcxtrace_path": mcxtrace}

        default_other = {"characters_per_line": 85}

        default_config = {"paths": default_paths, "other": default_other}

        self._write_yaml(default_config)

    def set_mcstas_path(self, path):
        """
        Sets the path to McStas

        Parameters
        ----------
        path : str
            Path to the mcstas directory containing "sources", "optics", ...
        """

        if not os.path.isdir(path):
            raise RuntimeError("Invalid path given to set_mcstas_path:"
                               + str(path))

        # read entire configuration file
        config = self._read_yaml()

        # update mcstas_path
        config["paths"]["mcstas_path"] = path

        # write new configuration file
        self._write_yaml(config)

    def set_mcrun_path(self, path):
        """
        Sets the path to mcrun

        Parameters
        ----------
        path : str
            Path to the mcrun executable
        """

        if not os.path.isdir(path):
            raise RuntimeError("Invalid path given to set_mcrun_path:"
                               + str(path))

        # read entire configuration file
        config = self._read_yaml()

        # update mcstas_path
        config["paths"]["mcrun_path"] = path

        # write new configuration file
        self._write_yaml(config)

    def set_mcxtrace_path(self, path):
        """
        Sets the path to McXtrace

        Parameters
        ----------
        path : str
            Path to the mcxtrace directory containing "sources", "optics", ...
        """

        if not os.path.isdir(path):
            raise RuntimeError("Invalid path given to set_mcxtrace_path:"
                               + str(path))

        # read entire configuration file
        config = self._read_yaml()

        # update mcxtrace_path
        config["paths"]["mcxtrace_path"] = path

        # write new configuration file
        self._write_yaml(config)

    def set_mxrun_path(self, path):
        """
        Sets the path to mxrun

        Parameters
        ----------
        path : str
            Path to the mxrun executable
        """

        if not os.path.isdir(path):
            raise RuntimeError("Invalid path given to set_mxrun_path: "
                               + str(path))

        # read entire configuration file
        config = self._read_yaml()

        # update mxrun_path
        config["paths"]["mxrun_path"] = path

        # write new configuration file
        self._write_yaml(config)

    def set_line_length(self, line_length):
        """
        Sets maximum line length for output

        Parameters
        ----------
        line_length : int
            maximum line length for output
        """

        if not isinstance(line_length, int):
            raise ValueError("Given line length in set_line_length not an "
                             + "integer.")

        if line_length < 1:
            raise ValueError("Line length specified in set_line_length must"
                             + " be positve, given length: "
                             + str(line_length))

        # read entire configuration file
        config = self._read_yaml()

        # update mcstas_path
        config["other"]["characters_per_line"] = int(line_length)

        # write new configuration file
        self._write_yaml(config)

    def __repr__(self):
        string = "Configurator:\n"
        config = self._read_yaml()
        if "paths" in config:
            string += " paths:\n"
            for key, value in config["paths"].items():
                string += "  " + str(key) + ": " + str(value) + "\n"

        if "other" in config:
            string += " other:\n"
            for key, value in config["other"].items():
                string += "  " + str(key) + ": " + str(value) + "\n"

        return string
