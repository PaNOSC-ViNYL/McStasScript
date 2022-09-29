import os
from datetime import datetime
import time
import json

TIME_FORMAT = "%d/%m/%Y %H:%M:%S"

class BeamDumpDatabase:
    def __init__(self, name, path):
        self.name = name
        self.path = path

        self.data = {}

        self.database_path = os.path.join(self.path, self.name + "_db")
        if os.path.isdir(self.database_path):
            self.load_database(self.database_path)
        else:
            self.create_new_database(self.database_path)

    def create_new_database(self, path):
        os.mkdir(path)

    def load_database(self, path):
        dump_points = os.listdir(path)

        for dump_point in dump_points:
            dump_point_path = os.path.join(path, dump_point)
            if not os.path.isdir(dump_point_path):
                continue

            if dump_point not in self.data:
                self.data[dump_point] = {}

            runs = os.listdir(dump_point_path)
            for run in runs:
                if run.endswith(".json"):
                    run_path = os.path.join(dump_point_path, run)
                    dump = BeamDump.dump_from_JSON(run_path)
                    self.data[dump_point][dump.data["run_name"]] = dump

    def create_folder_for_dump_point(self, dump_point):
        dump_point_path = os.path.join(self.database_path, dump_point)
        if not os.path.isdir(dump_point_path):
            os.mkdir(dump_point_path)

        return dump_point_path

    def load_data(self, data_path, parameters, run_name, dump_point, comment):
        files = os.listdir(data_path)

        for file in files:
            file = os.path.join(data_path, file) # Get full path
            if os.path.isdir(file):
                continue

            if file.endswith((".mcpl", ".mcpl.gz")):
                file_path = os.path.abspath(file)
                dump = BeamDump(data_path=file_path, parameters=parameters,
                                dump_point=dump_point, run_name=run_name,
                                comment=comment)
                dump_path = self.create_folder_for_dump_point(dump_point)
                dump.dump_to_JSON(dump_path)

                if dump_point not in self.data:
                    self.data[dump_point] = {}

                run = dump.data["run_name"]
                self.data[dump_point][run] = dump

    def newest_at_point(self, point):
        if point not in self.data:
            raise KeyError("This dump point wasn't in the database.")

        runs = self.data[point]
        return self.sort_by_time(runs, return_latest=True)

    def sort_by_time(self, runs, return_latest=False):
        time_to_run = {}
        for run in runs:
            dump = runs[run]
            time_loaded = dump.data["time_loaded"]
            time_to_run[time_loaded] = dump

        sorted_times = sorted((time.strptime(d, TIME_FORMAT) for d in time_to_run.keys()), reverse=True)

        if return_latest:
            latest = time.strftime(TIME_FORMAT, sorted_times[0])
            return time_to_run[latest]

        return_list = []
        for sorted_time in sorted_times:
            return_list.append(time_to_run[time.strftime(TIME_FORMAT, sorted_time)])

        return return_list

    def show_in_order(self, component_names):
        if len(self.data) == 0:
            print("No data in dump database yet. Use run_to method to create dump.")

        for name in component_names:
            if name in self.data:
                print(name + ":")
                dumps = self.sort_by_time(self.data[name])
                for dump in dumps:
                    if len(dump.data["parameters"]) < 4:
                        par_string = ": " + str(dump.data["parameters"])
                    else:
                        par_string = ""

                    print(" ", dump.data["run_name"].ljust(10), ":",
                          dump.data["time_loaded"].ljust(16), ":",
                          dump.data["comment"], par_string)

    def __repr__(self):

        string = ""
        for point in self.data:
            string += point + ":\n"
            for run in self.data[point]:
                string += "  " + str(self.data[point][run]) + ":\n"

        return string

class BeamDump:
    def __init__(self, data_path, parameters, dump_point, run_name=None, time_loaded=None, comment=""):

        simple_parameters = {}
        for parameter in parameters:
            if hasattr(parameters[parameter], "value"):
                simple_parameters[parameter] = parameters[parameter].value
            else:
                simple_parameters[parameter] = parameters[parameter]

        self.data = {"data_path": data_path,
                     "dump_point": dump_point,
                     "parameters": simple_parameters,
                     "run_name": run_name,
                     "comment": comment}

        if time_loaded is None:
            self.data["time_loaded"] = datetime.now().strftime(TIME_FORMAT)
        else:
            self.data["time_loaded"] = time_loaded

        """
        self.data_path = data_path
        self.dump_point = dump_point
        self.parameters = parameters
        self.time_loaded = datetime.now().strftime("%H:%M:%S")
        """

    @classmethod
    def dump_from_JSON(cls, filepath):
        with open(filepath, "r") as f:
            data = json.loads(f.read())

        return cls(**data)

    def dump_to_JSON(self, folder_path):

        if self.data["run_name"] is None:
            base_name = "run"
        else:
            base_name = self.data["run_name"]

        index = 0
        proposed_name = base_name
        while os.path.isfile(os.path.join(folder_path, proposed_name + ".json")):
            proposed_name = base_name + "_" + str(index)
            index += 1

        self.data["run_name"] = proposed_name

        filepath = os.path.join(folder_path, self.data["run_name"] + ".json")
        if os.path.isfile(filepath):
            raise RuntimeError("Run with this destination and run_name: '"
                               + self.data["run_name"]
                               + "' already exists in BeamDumpDatabase.")

        with open(filepath, "w") as outfile:
            json.dump(self.data, outfile)

    def __repr__(self):
        return str(self.data)

