import copy

import numpy as np

from mcstasscript.interface import instr, functions, plotter, reader

# compare the contents of data and data_ref monitor for monitor using McStasScript

def visual_compare(data, data_ref):
    for data_set in data_ref:
        name = data_set.name
        py_data_set = functions.name_search(name, data)
        plotter.make_sub_plot([data_set, py_data_set])


def compare_1d(data, data_ref):
    for data_set in data_ref:
        # Check its a 1D dataset
        if not isinstance(data_set.metadata.dimension, int):
            continue
        
        name = data_set.name
        py_data_set = functions.name_search(name, data)

        # Make version that is subtracted
        if len(data_set.Intensity) != len(py_data_set.Intensity):
            raise ValueError("Somehow intensity length does not match!")
            
        diff = copy.deepcopy(data_set)
        
        diff.Intensity = data_set.Intensity - py_data_set.Intensity
        diff.Error = np.sqrt(data_set.Error**2 + py_data_set.Error**2)
        diff.set_title("Difference")
        diff.set_ylabel("Intensity difference")
        
        print("Intensity difference found:", np.sum(diff.Intensity))
        
        rel_diff = copy.deepcopy(diff)
        rel_diff.Intensity /= data_set.Error
        rel_diff.Error *= 0
        rel_diff.set_title("Relative difference")
        rel_diff.set_ylabel("Relative difference")

        plotter.make_sub_plot([data_set, py_data_set, diff, rel_diff])


class compare_engine:
    def __init__(self, show_all=False, show_different=False, name=None):
        
        self.show_all = show_all
        self.show_different = show_different
        self.name = name
        
        self.comparison_started = False
        self.comparison_done = False
        self.any_fail = False
        
        self.history = []
        self.log_string = ""
        self.n_mismatches = None
        
    def run_comparison(self, data, data_ref):
    
        self.comparison_started = True
        for data_set in data_ref:
        
            # find the data
            name = data_set.name
            py_data_set = functions.name_search(name, data)
        
            if isinstance(data_set.metadata.dimension, int):
                self.compare_1d(py_data_set, data_set)
            else:
                self.compare_2d(py_data_set, data_set)
    
        self.n_mismatches = 0
        for mon in self.history:
            if not mon[1]:
                self.n_mismatches += 1

        self.comparison_done = True

    def compare_1d(self, py_data_set, data_set):
    
        # Make version that is subtracted
        if len(data_set.Intensity) != len(py_data_set.Intensity):
            raise ValueError("Somehow intensity length does not match!")
        
        diff = copy.deepcopy(data_set)
        
        diff.Intensity = data_set.Intensity - py_data_set.Intensity
        diff.Error = np.sqrt(data_set.Error**2 + py_data_set.Error**2)
        diff.set_title("Difference")
        diff.set_ylabel("Intensity difference")
        
        total_difference = np.sum(diff.Intensity)
        
        success = total_difference == 0
        
        if not success:
            self.any_fail = True
        
        self.history.append((data_set.name, success))
        
        if self.show_all or (total_difference != 0 and self.show_different):
        
            rel_diff = copy.deepcopy(diff)
            rel_diff.Intensity /= data_set.Error
            rel_diff.Error *= 0
            rel_diff.set_title("Relative difference")
            rel_diff.set_ylabel("Relative difference")

            plotter.make_sub_plot([data_set, py_data_set, diff, rel_diff])


    def compare_2d(self, py_data_set, data_set):

        # Make version that is subtracted
        if data_set.Intensity.shape != py_data_set.Intensity.shape:
            raise ValueError("Somehow intensity shape does not match!")

        diff = copy.deepcopy(data_set)
        diff.Intensity = data_set.Intensity - py_data_set.Intensity
        diff.Error = np.sqrt(data_set.Error**2 + py_data_set.Error**2)
        diff.set_title("Difference")

        total_difference = np.sum(diff.Intensity)

        success = total_difference == 0
        
        if not success:
            self.any_fail = True
        
        self.history.append((data_set.name, success))

        if self.show_all or (total_difference != 0 and self.show_different):
        
            rel_diff = copy.deepcopy(diff)
            rel_diff.Intensity /= data_set.Error
            rel_diff.Error *= 0
            rel_diff.set_title("Relative difference")
            #rel_diff.set_ylabel("Relative difference")

            plotter.make_sub_plot([data_set, py_data_set, diff, rel_diff])

    def reset_log_string(self):
        self.log_string = ""
    
    def add_log(self, *args):
        for arg in args:
            self.log_string += str(arg)
        self.log_string += "\n"

    def history_string(self, show_all=False):
    
        self.reset_log_string()
        self.add_log("-"*71)
    
        if not self.comparison_started:
            self.add_log("No comparison performed for " + self.name)
            return
        
        if self.comparison_started and not self.comparison_done:
            self.add_log("Comparison did not end succesffully for " + self.name)
            print("- "*35 + "-")

        if not show_all and not self.any_fail:
            return

        if self.name is not None:
            self.add_log("  Results for " + self.name)

        longest_name = 40
        for history in self.history:
            if len(history[0]) > longest_name:
                longest_name = len(history[0])

        for history in self.history:
            name_length = len(history[0])
            spacing = (longest_name - name_length)*" "

            if not history[1] or show_all:
                if history[1]:
                    self.add_log("    ", history[0], spacing, "succeeded")
                else:
                    self.add_log("    ", history[0], spacing, "failed")

    def print_history(self, show_all=False):
        self.history_string(show_all=show_all)
        print(self.log_string)

    def write_history_to_file(self, filename, mode="w", show_all=False):
        self.history_string(show_all=show_all)
        with open(filename, mode) as file:
            file.write(self.log_string)




