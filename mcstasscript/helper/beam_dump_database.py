import os
from datetime import datetime
import time
import json

TIME_FORMAT = "%d/%m/%Y %H:%M:%S" # Time format used for database

class BeamDumpDatabase:
    def __init__(self, name, path):
        """
        Database over location and run properties of beam dumps

        name : str
            Name of instrument for which this database is connected

        path : str
            input_path for instrument, database is placed there
        """
        self.name = name
        self.path = path

        self.data = {}

        self.database_path = os.path.join(self.path, self.name + "_db")
        if os.path.isdir(self.database_path):
            self.load_database(self.database_path)
        else:
            self.create_new_database(self.database_path)

    def create_new_database(self, path):
        """
        Creates directory for database, may be expanded in future
        """
        os.mkdir(path)

    def load_database(self, path):
        """
        Loads an existing database from disk

        path : str
            Path for the database to be loaded
        """
        dump_points = os.listdir(path)

        # Each dump point is a folder in the database root
        for dump_point in dump_points:
            dump_point_path = os.path.join(path, dump_point)
            if not os.path.isdir(dump_point_path):
                continue

            if dump_point not in self.data:
                self.data[dump_point] = {}

            # Each run is a json file in the dump_point folder
            runs = os.listdir(dump_point_path)
            for run in runs:
                if run.endswith(".json"):
                    run_path = os.path.join(dump_point_path, run)
                    dump = BeamDump.dump_from_JSON(run_path)

                    run_name = dump.data["run_name"]
                    if run_name not in self.data[dump_point]:
                        self.data[dump_point][run_name] = {}

                    tag = dump.data["tag"]
                    self.data[dump_point][run_name][tag] = dump

    def create_folder_for_dump_point(self, dump_point):
        """
        Adds folder to database for dump_point if it hasn't been made yet

        Returns path to the folder whether it was created here or existed
        """
        dump_point_path = os.path.join(self.database_path, dump_point)
        if not os.path.isdir(dump_point_path):
            os.mkdir(dump_point_path)

        return dump_point_path

    def load_data(self, expected_filename, data_folder_path, parameters, run_name, dump_point, comment):
        """
        Include MCPL file into database with given metadata

        Attempts to load MCPL file from McStas output. If the file does not
        exists, the method will return without adding anything to the database.

        expected_filename : str
            Filename given as McStas parameter, can include explicit double quotes

        data_folder_path : str
            Path to the data folder that contains the MCPL file

        parameters: dict
            dict with parameter names and values for this run

        run_name : str
            Specified run name for this run

        dump_point : str
            Name of component where MCPL cut ended, can start from here later

        comment : str
            Comment on the run that can be included in metadata
        """
        if not os.path.isdir(data_folder_path):
            # If the folder doesn't exist, skip search
            return

        # Sanitize expected_filename
        expected_filename = expected_filename.strip('"')
        expected_filename = os.path.split(expected_filename)[-1]
        expected_filename = expected_filename.split(".gz")[0]
        expected_filename = expected_filename.split(".mcpl")[0]

        # The system might or might not be able to compress the data, search for both
        possible_endings = [".mcpl", ".mcpl.gz"]

        for ending in possible_endings:
            file_path = os.path.join(data_folder_path, expected_filename + ending)
            if not os.path.isfile(file_path):
                continue

            if dump_point not in self.data:
                self.data[dump_point] = {}

            if run_name not in self.data[dump_point]:
                self.data[dump_point][run_name] = {}

            n_tags = len(self.data[dump_point][run_name])
            # Find relative path
            db_path = self.path
            rel_path = os.path.relpath(file_path, start=db_path)

            # Create dump with given metadata
            dump = BeamDump(data_path=rel_path, parameters=parameters,
                            dump_point=dump_point, run_name=run_name,
                            comment=comment, tag=n_tags)
            # Write to disk
            dump_path = self.create_folder_for_dump_point(dump_point)
            dump.dump_to_JSON(dump_path)

            self.data[dump_point][run_name][n_tags] = dump
            return dump

    def get_dump(self, point, run_name=None, tag=None):
        """
        Getter for dumps with specified point, run_name and tag
        """
        if point not in self.data:
            raise KeyError("The dump point '" + point + "' wasn't in the database.")

        if run_name is None and tag is None:
            return self.newest_at_point(point)

        if run_name not in self.data[point]:
            raise KeyError("The run_name '" + run_name + "' wasn't in the database "
                           + "at the dump_point '" + point + "'.")

        if tag is None:
            return self.newest_at_point(point, run=run_name)

        tag = int(tag) # Ensure tag is an integer for database lookup

        if tag not in self.data[point][run_name]:
            raise KeyError("The tag '" + str(tag) + "' was not in the database for"
                           + "run_name '" + run_name
                           + "at the dump_point '" + point + "'.")

        dump = self.data[point][run_name][tag]
        if not dump.file_present(self.path):
            raise RuntimeError("The dump datafile was not found in the expected location.")

        return dump

    def newest_at_point(self, point, run=None):
        """
        Gets newest dump at a given point and optionally a run_name

        point : str
            String with component name matching the dump point

        run : str
            String matching the run_name desired
        """

        if point not in self.data:
            raise KeyError("The dump point '" + point + "' wasn't in the database.")

        if run is None:
            # Collect all runs at the point for sort_by_time
            runs = self.data[point]
        else:
            # If a run name is specified, check it exists
            if run not in self.data[point]:
                raise KeyError("The run_name '" + run + "' wasn't in the database "
                               + "at the dump_point '" + point + "'.")

            # Collect all the runs in a dict for sort_by_time
            runs = {run: self.data[point][run]}

        return self.sort_by_time(runs, return_latest=True)

    def sort_by_time(self, runs, return_latest=False):
        """
        Sorts a given dict of runs and returns a list or the latest if return_latest is true

        The input data is given as a dictionary of runs matching the database structure
        with all the individual tags underneath the runs. It is usually used with all runs
        being from the same point, but not necessary for the method to work.

        runs : dict
            Dictionary with runs containing dictionary of tags pointing to dumps

        return_latest : bool
            If True only latest dump is returned, otherwise sorted list
        """
        time_to_run = {}
        for run in runs:
            for tag in runs[run]:
                dump = runs[run][tag]
                time_loaded = dump.data["time_loaded"]
                time_to_run[time_loaded] = dump

        sorted_times = sorted((time.strptime(d, TIME_FORMAT) for d in time_to_run.keys()), reverse=True)

        return_list = []
        for sorted_time in sorted_times:
            return_list.append(time_to_run[time.strftime(TIME_FORMAT, sorted_time)])

        if return_latest:
            for dump in return_list:
                if dump.file_present(self.path):
                    return dump
                else:
                    point = dump.data["dump_point"]
                    run_name = dump.data["run_name"]
                    tag = dump.data["tag"]
                    data_path = dump.data["data_path"]

                    print(f"Latest file had run_name '{run_name}' and tag '{tag}', but the file was "
                          f"not found in the expected location, and thus skipped.")
                    print("Expected path: ", data_path)

            raise RuntimeError("No beam dumps available.")

        return return_list

    def show_in_order(self, component_names):
        """
        Method to print content of database in order of component_names

        component_names : list
            List of strings for component names in the instrument
        """

        if len(self.data) == 0:
            print("No data in dump database yet. Use run_to method to create dump.")
            return

        print("Run point:")
        print(" ", "run_name".ljust(12), ":", "tag", ":", "time".ljust(20), ":", "comment")
        print("-"*60, "--- -- -")

        for name in component_names:
            if name in self.data:
                print(name + ":")
                dumps = self.sort_by_time(self.data[name])
                for dump in dumps:
                    if len(dump.data["parameters"]) < 2:
                        par_string = ": " + str(dump.data["parameters"])
                    else:
                        par_string = ""

                    print(" ", dump.data["run_name"].ljust(12), ":",
                          str(dump.data["tag"]).ljust(3), ":",
                          dump.data["time_loaded"].ljust(20), ":",
                          dump.data["comment"], par_string)

    def __repr__(self):
        """
        Basic repr of the data included in the database.
        """
        string = ""
        for point in self.data:
            string += point + ":\n"
            for run in self.data[point]:
                for tag in self.data[point][run]:
                    string += "  " + self.data[point][run][tag].data["run_name"] + "\n:"
                    string += "    " + str(self.data[point][run][tag]) + ":\n"

        return string


class BeamDump:
    def __init__(self, data_path, parameters, dump_point, run_name,
                 time_loaded=None, comment="", tag=0, record_name=""):
        """
        Class describing a beamdump made somewhere in an instrument

        Inputs for class matches what can be read from json file describing
        dump to facilitate easy recreation from file. Strips complex parameters
        into simple dict with par name and value for easy storage.

        data_path : str
            Path of MCPL datafile

        parameters : dict
            Parameters used to run simulation

        dump_point : str
            Name of component where beam was dumped

        run_name : str
            Specified run name for this dump

        time_loaded : str
            Optional, usually generated at first load, timestamp

        comment : str
            Comment for this beamdump

        tag : integer
            Tag for this beamdump to differentiate similar dumps

        record_name : str
            Unique filename combining run_name and tag
        """
        simple_parameters = {}
        # Convert complex parameter objects to simple key - value pairs
        for parameter in parameters:
            if hasattr(parameters[parameter], "value"):
                # The full parameter objects store their value in value attribute
                simple_parameters[parameter] = parameters[parameter].value
            else:
                simple_parameters[parameter] = parameters[parameter]

        # The fields in data must correspond to the input of the class
        self.data = {"data_path": data_path,
                     "dump_point": dump_point,
                     "parameters": simple_parameters,
                     "run_name": run_name,
                     "comment": comment,
                     "tag": tag,
                     "record_name": record_name}

        if time_loaded is None:
            self.data["time_loaded"] = datetime.now().strftime(TIME_FORMAT)
        else:
            self.data["time_loaded"] = time_loaded

    @classmethod
    def dump_from_JSON(cls, filepath):
        """
        Load dump from json file

        filepath : str
            Path to json file for load
        """
        with open(filepath, "r") as f:
            data = json.loads(f.read())

        return cls(**data) # Since the data fields correspond to class input

    def dump_to_JSON(self, folder_path):
        """
        Writes representation of the object to file

        folder_path : str
            Folder in which the dump will be placed
        """

        self.data["record_name"] = self.data["run_name"] + "_" + str(self.data["tag"])

        filepath = os.path.join(folder_path, self.data["record_name"] + ".json")
        if os.path.isfile(filepath):
            raise RuntimeError("Run with this destination and run_name: '"
                               + self.data["record_name"]
                               + "' already exists in BeamDumpDatabase.")

        with open(filepath, "w") as outfile:
            json.dump(self.data, outfile)

    def file_present(self, origin_path):
        """
        Checks whether the file is present and returns bool
        """
        return os.path.isfile(os.path.join(origin_path,self.data["data_path"]))

    def print_all(self):
        """
        Print all entries in data for dump
        """
        for key in self.data:
            print(key, ":",  self.data[key])

    def __repr__(self):
        """
        Simple representation of data in object
        """
        return str(self.data)

