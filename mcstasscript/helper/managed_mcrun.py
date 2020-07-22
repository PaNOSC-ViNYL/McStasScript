import os
import numpy as np
import subprocess

from mcstasscript.data.data import McStasMetaData
from mcstasscript.data.data import McStasData


class ManagedMcrun:
    """
    A class for performing a mcstas simulation and organizing the data
    into python objects

    ManagedMcrun is usually called by the instrument class of
    McStasScript but can be used independently.  It runs the mcrun
    command using the system command, and if this is not in the path,
    the absolute path can be given in a keyword argument mcrun_path.

    Attributes
    ----------
    name_of_instrumentfile : str
        Name of instrument file to be executed

    data_folder_name : str
        Name of datafolder mcrun writes to disk

    ncount : int
        Number of rays to simulate

    mpi : int
        Number of mpi threads to run

    parameters : dict
        Dictionary of parameter names and values for this simulation

    custom_flags : string
        Custom flags that are passed to the mcrun command

    mcrun_path : string
        Path to the mcrun command (can be empty if already in path)

    Methods
    -------
    run_simulation()
        Runs simulation, returns list of McStasData instances

    """

    def __init__(self, instr_name, **kwargs):
        """
        Parameters
        ----------
        instr_name : str
            Name of instrument file to be simulated

        kwargs : keyword arguments
            foldername : str
                Sets data_folder_name
            ncount : int
                Sets ncount
            mpi : int
                Sets thread count
            parameters : dict
                Sets parameters
            custom_flags : str
                Sets custom_flags passed to mcrun
            mcrun_path : str
                Path to mcrun command, "" if already in path
            increment_folder_name : bool
                If True, automaticaly appends foldername to make it unique
            force_compile : bool
                If True, forces compile, default is True
            run_folder : str
                Path to folder in which to run McStas

        """

        self.name_of_instrumentfile = instr_name

        self.data_folder_name = ""
        self.ncount = int(1E6)
        self.mpi = None
        self.parameters = {}
        self.custom_flags = ""
        self.mcrun_path = ""
        self.increment_folder_name = False
        self.compile = True
        self.run_path = "."
        # mcrun_path always in kwargs
        if "mcrun_path" in kwargs:
            self.mcrun_path = kwargs["mcrun_path"]

        if "foldername" in kwargs:
            self.data_folder_name = kwargs["foldername"]
        else:
            raise NameError(
                "ManagedMcrun needs foldername to load data, add "
                + "with keyword argument.")

        if "ncount" in kwargs:
            self.ncount = int(kwargs["ncount"])

        if "mpi" in kwargs:
            self.mpi = kwargs["mpi"]

        if "parameters" in kwargs:
            self.parameters = kwargs["parameters"]

        if "custom_flags" in kwargs:
            self.custom_flags = kwargs["custom_flags"]

        if "increment_folder_name" in kwargs:
            self.increment_folder_name = kwargs["increment_folder_name"]

        if "force_compile" in kwargs:
            self.compile = kwargs["force_compile"]

        if "run_path" in kwargs:
            self.run_path = kwargs["run_path"]

    def run_simulation(self, **kwargs):
        """
        Runs McStas simulation described by initializing the object
        """

        # get relevant paths
        current_directory = os.getcwd()

        if not os.path.isabs(self.data_folder_name):
            self.data_folder_name = os.path.join(current_directory,
                                                 self.data_folder_name)

        if not os.path.isabs(self.run_path):
            self.run_path = os.path.join(current_directory, self.run_path)

        if not os.path.isdir(self.run_path):
            raise ValueError("Given run_path for McStas not a directory!")

        # construct command to run
        options_string = ""
        if self.compile:
            options_string = "-c "

        if self.mpi is not None:
            mpi_string = " --mpi=" + str(self.mpi) + " " # Set mpi
        else:
            mpi_string = " "

        option_string = (options_string
                         + "-n " + str(self.ncount)  # Set ncount
                         + mpi_string)

        if self.increment_folder_name and os.path.isdir(self.data_folder_name):
            counter = 0
            new_name = self.data_folder_name + "_" + str(counter)
            while os.path.isdir(new_name):
                counter = counter + 1
                new_name = self.data_folder_name + "_" + str(counter)

            self.data_folder_name = new_name

        if len(self.data_folder_name) > 0:
            option_string = (option_string
                             + "-d "
                             + self.data_folder_name)

        # add parameters to command
        parameter_string = ""
        for key, val in self.parameters.items():
            parameter_string = (parameter_string + " "
                                + str(key)  # parameter name
                                + "="
                                + str(val))  # parameter value

        mcrun_full_path = self.mcrun_path + "mcrun"
        if len(self.mcrun_path) > 1:
            if not (self.mcrun_path[-1] == "\\"
                    or self.mcrun_path[-1] == "/"):
                mcrun_full_path = os.path.join(self.mcrun_path, "mcrun")

        # Run the mcrun command on the system
        full_command = (mcrun_full_path + " "
                  + option_string + " "
                  + self.custom_flags + " "
                  + self.name_of_instrumentfile
                  + parameter_string)

        try:
            os.chdir(self.run_path)

            process = subprocess.run(full_command, shell=True,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     universal_newlines=True)

            os.chdir(current_directory)

        except:
            os.chdir(current_directory)
            raise RuntimeError("Could not run McStas command.")

        if "suppress_output" in kwargs:
            if kwargs["suppress_output"] is False:
                print(process.stderr)
                print(process.stdout)
        else:
            print(process.stderr)
            print(process.stdout)


    def load_results(self, *args):

        if len(args) == 0:
            data_folder_name = self.data_folder_name
        elif len(args) == 1:
            data_folder_name = args[0]
        else:
            raise InputError("load_results can be called with 0 or 1 arguments")

        if not os.path.isdir(data_folder_name):
            raise NameError("Given data directory does not exist.")

        # Find all data files in generated folder
        files_in_folder = os.listdir(data_folder_name)

        # Raise an error if mccode.sim is not available
        if "mccode.sim" not in files_in_folder:
            raise NameError("No mccode.sim in data folder.")

        # Open mccode to read metadata for all datasets written to disk
        f = open(os.path.join(data_folder_name, "mccode.sim"), "r")

        # Loop that reads mccode.sim sections
        metadata_list = []
        in_data = False
        for lines in f:
            # Could read other details about run

            if lines == "end data\n":
                # No more data for this metadata object
                # Extract the information
                current_object.extract_info()
                # Add to metadata list
                if current_object.filename != "":
                    metadata_list.append(current_object)
                # Stop reading data
                in_data = False

            if in_data:
                # This line contains info to be added to metadata
                colon_index = lines.index(":")
                key = lines[2:colon_index]
                value = lines[colon_index+2:]
                current_object.add_info(key, value)

            if lines == "begin data\n":
                # Found data section, create new metadata object
                current_object = McStasMetaData()
                # Start recording data to metadata object
                in_data = True

        # Close mccode.sim
        f.close()

        # Create a list for McStasData instances to return
        results = []

        # Load datasets described in metadata list individually
        for metadata in metadata_list:
            # Load data with numpy
            data = np.loadtxt(os.path.join(data_folder_name,
                              metadata.filename.rstrip()))

            # Split data into intensity, error and ncount
            if type(metadata.dimension) == int:
                xaxis = data.T[0, :]
                Intensity = data.T[1, :]
                Error = data.T[2, :]
                Ncount = data.T[3, :]

            elif len(metadata.dimension) == 2:
                xaxis = []  # Assume evenly binned in 2d
                data_lines = metadata.dimension[1]

                Intensity = data[0:data_lines, :]
                Error = data[data_lines:2*data_lines, :]
                Ncount = data[2*data_lines:3*data_lines, :]
            else:
                raise NameError(
                    "Dimension not read correctly in data set "
                    + "connected to monitor named "
                    + metadata.component_name)

            # The data is saved as a McStasData object
            result = McStasData(metadata, Intensity,
                                Error, Ncount,
                                xaxis=xaxis)

            # Add this result to the results list
            results.append(result)

            # Close the current datafile
            f.close()

        # Return list of McStasData objects
        return results
