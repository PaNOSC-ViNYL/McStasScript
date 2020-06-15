import subprocess
import sys
import os
import multiprocessing
import time

import compare_data

from mcstasscript.interface import instr, functions, plotter, reader

# TODO LIST
# Make sure all folders are created if they are not
# Problems with process version:
#   Failures in run in log, but not outside
#   All comparisons fail, even though they should succeed?

class from_reference:
    def __init__(self, instrument_path, log_path, input_path=".",
                 data_folder="data_folder", debug_folder="debug",
                 name=None, mcrun_options=None, show_different=False,
                 timeout=None):
        """
        Class for testing the McStasScript python reader tool which
        can read .instr files and create a python file or object
        which corresponds to the original. A reference run is made
        with the standard parameters of the original instr file, this
        is then used in comparing the results from the McStasScript
        versions.
        Possible to see comparison plots when a difference is detected
        in order to aid in debugging, but this pauses execution.
        
        Parameters
        ----------
        
        instrument_path : str
            Path of instrument to reproduce
            
        log_path : str
            Path to directory in which to write log files
            
        Keyword parameters
        ------------------
            
        input_path : str
            Path to directory which McStas runs are performed in
            
        data_folder : str
            Path to directory which data will be saved to
            
        debug_folder : str
            Path to directory where debug scripts will be placed
            
        name : str
            Change name of instrument, otherwise filename is used
            
        mcrun_options : dictionary
            options for mcrun in format used by McStasScript
            
        show_different : bool
            if True will plot whenever data comparison does not match
        """

        self.instrument_path = instrument_path
        self.log_path = log_path
        self.cwd = os.getcwd()

        self.instrument_name = os.path.splitext(os.path.basename(instrument_path))[0]
        if name is None:
            self.name = self.instrument_name
        else:
            self.name = name
        
        if mcrun_options is None:
            mcrun_options = {"ncount" : 1E6, "mpi" : 2, "seed" : 37}
        else:
            if "ncount" not in mcrun_options:
                mcrun_options["ncount"] = 1E6

        self.mcrun_options = mcrun_options
        self.show_different = show_different

        self.base_foldername = data_folder
        if not os.path.isdir(self.base_foldername):
            if not os.path.isfile(self.base_foldername):
                os.mkdir(self.base_foldername)
            else:
                raise ValueError("Given data_folder path is a file!")
                
        self.debug_folder = debug_folder
        if not os.path.isdir(self.debug_folder):
            if not os.path.isfile(self.debug_folder):
                os.mkdir(self.debug_folder)
            else:
                raise ValueError("Given debug_folder path is a file!")
                
        self.input_path = input_path
        if not os.path.isdir(self.input_path):
            if not os.path.isfile(self.input_path):
                os.mkdir(self.input_path)
            else:
                raise ValueError("Given input_path path is a file!")
                
        self.timeout = timeout

        self.python_filename = os.path.join(self.input_path, self.name + "_generated.py")
        
        self.generate_python_file_filename = os.path.join(self.debug_folder, self.name + "_py_file_generator.py")
        self.generate_python_object_filename = os.path.join(self.debug_folder, self.name + "_py_object_generator.py")

        self.instrument_object = None

        # Status parameters
        self.performed_read_instrument = False
        self.could_start_reader = False
        self.could_write_python_file = False
        self.could_make_instr_object = False
        
        self.started_reference_run = False
        self.completed_reference_run = False
        
        self.started_file_run = False
        self.completed_file_run = False
        
        self.started_object_run = False
        self.completed_object_run = False
        
        self.timeout_status = False
        
        self.log_initialized = False
        
        
        
        # Status parameters for process
        self.queue = multiprocessing.Queue() # Queue for comparison data
        
        self.performed_read_instrument_p = multiprocessing.Value('i', 0)
        self.could_start_reader_p = multiprocessing.Value('i', 0)
        self.could_write_python_file_p = multiprocessing.Value('i', 0)
        self.could_make_instr_object_p = multiprocessing.Value('i', 0)
        
        self.started_reference_run_p = multiprocessing.Value('i', 0)
        self.completed_reference_run_p = multiprocessing.Value('i', 0)
        
        self.started_file_run_p = multiprocessing.Value('i', 0)
        self.completed_file_run_p = multiprocessing.Value('i', 0)
        
        self.started_object_run_p = multiprocessing.Value('i', 0)
        self.completed_object_run_p = multiprocessing.Value('i', 0)
        
        self.timeout_status_p = multiprocessing.Value('i', 0)
        
        self.log_initialized_p = multiprocessing.Value('i', 0)
        
        self.queue_used_p = multiprocessing.Value('i', 0)

        
        self.read_log_filename = os.path.join(self.log_path, self.name + "_read.log")
        self.run_log_ref_filename = os.path.join(self.log_path, self.name + "_ref_run.log")
        self.run_log_file_filename = os.path.join(self.log_path, self.name + "_file_run.log")
        self.run_log_object_filename = os.path.join(self.log_path, self.name + "_object_run.log")
        self.result_log_file_filename = os.path.join(self.log_path, self.name + "_file_result.log")
        self.result_log_object_filename = os.path.join(self.log_path, self.name + "_object_result.log")
        
        # Comparisons
        self.object_comparison = None # Not object, but just histories loaded from file
        self.object_mismatches = None
        self.file_comparison = None # comparison object
        self.file_mismatches = None
        
    def run_all(self):
        """
        Main method that performs all inidivual tasks, with timeout
        """
    
        if self.timeout is None:
            self._run_all()
        else:
            process = multiprocessing.Process(target=self._run_all)
            process.start()

            process.join(self.timeout)
            if process.is_alive():
                print(" - - --X Run timed out (exceeded runtime of: " + str(self.timeout) + " s)\n")
                self.timeout_status = True

                process.terminate()
                process.join()

                if self.could_write_python_file_p.value == 1:
                    self.read_file_log()
            
            
        # Have to extract logical information from shared process memory
        if self.performed_read_instrument_p.value == 1:
            self.performed_read_instrument = True
        else:
            self.performed_read_instrument = False
    
        if self.could_start_reader_p.value == 1:
            self.could_start_reader = True
        else:
            self.could_start_reader = False
        
        if self.could_write_python_file_p.value == 1:
            self.could_write_python_file = True
        else:
            self.could_write_python_file = False
        
        if self.could_make_instr_object_p.value == 1:
            self.could_make_instr_object = True
        else:
            self.could_make_instr_object = False
        
        if self.started_reference_run_p.value == 1:
            self.started_reference_run = True
        else:
            self.started_reference_run = False
        
        if self.completed_reference_run_p.value == 1:
            self.completed_reference_run = True
        else:
            self.completed_reference_run = False

        if self.started_file_run_p.value == 1:
            self.started_file_run = True
        else:
            self.started_file_run = False
        
        if self.completed_file_run_p.value == 1:
            self.completed_file_run = True
        else:
            self.completed_file_run = False
        
        if self.started_object_run_p.value == 1:
            self.started_object_run = True
        else:
            self.started_object_run = False
        
        if self.completed_object_run_p.value == 1:
            self.completed_object_run = True
        else:
            self.completed_object_run = False

        if self.queue_used_p.value == 1:
            self.object_comparison, self.object_mismatches, self.file_comparison, self.file_mismatches = self.queue.get()

        self.write_read_instrument_file()
        self.write_read_instrument_object()

        #print("obj comp", self.object_comparison)
        #print("obj mis", self.object_mismatches)
        #print("file comp", self.file_comparison)
        #print("file mis", self.file_mismatches)
        
        self.print_result_short()
        self.logging()

        self.queue.close()
        process.terminate()

    def _run_all(self):
        """
        Main method that performs all inidivual tasks
        """
        
        print("-"*10, " Running ", self.name, " ", "-"*12)
        self.initialize_logging()
        self.read_instrument()
        self.run_reference()
        if self.could_write_python_file_p.value == 1:
            self.run_file_version()
        if self.could_make_instr_object_p.value == 1:
            self.run_object_version()
        if self.could_write_python_file_p.value == 1:
            self.read_file_log()
        
        if self.timeout is not None:
            self.queue.put((self.object_comparison, self.object_mismatches, self.file_comparison, self.file_mismatches))
            self.queue_used_p.value = 1
        
    def initialize_logging(self):
        """
        Initialize logging files, they are later appended to
        """
    
        # check if log_path is a directory.
        if not os.path.isdir(self.log_path):
            if not os.path.isfile(self.log_path):
                os.mkdir(self.log_path)
            else:
                raise ValueError("Given log_path is a file!")
    
        with open(self.read_log_filename, "w") as file:
            file.write("Start of log for " + self.name + ", python print for reading instrument file.\n\n")
        
        with open(self.run_log_ref_filename, "w") as file:
            file.write("Start of run log for " + self.name + ", which was run from original instr file.\n\n")
    
        with open(self.run_log_file_filename, "w") as file:
            file.write("Start of run log for " + self.name + ", which was run from py file.\n\n")
        
        with open(self.run_log_object_filename, "w") as file:
            file.write("Start of run log for " + self.name + ", which was run as py object.\n\n")
            
        with open(self.result_log_file_filename, "w") as file:
            file.write("Start of result log for " + self.name + ", which was run from py file.\n\n")

        with open(self.result_log_object_filename, "w") as file:
            file.write("Start of result log for " + self.name + ", which was run from py object.\n\n")

        self.log_initialized_p.value = 1

    def read_instrument(self):
        """
        Attempts to read the reference instrument and create McStasScript
        file and object versions. Try blocks are used to record when
        failures occur, and this status is saved for later overview.
        """
    
        self.performed_read_instrument_p.value = 1
        
        # Initializing the reader object
        try:
            InstrReader = reader.McStas_file(self.instrument_path)
            
            self.could_start_reader_p.value = 1
        except:
            self.could_start_reader_p.value = 0
        
        # Using the reader object to write a python file
        try:
            InstrReader.write_python_file(self.python_filename, force=True)

            self.could_write_python_file_p.value = 1
        except:
            self.could_write_python_file_p.value = 0

        # Using the reader object to make a python instrument object
        try:
            self.instrument_object = instr.McStas_instr(self.name + "_object", input_path=self.input_path)
            InstrReader.add_to_instr(self.instrument_object)
            
            self.could_make_instr_object_p.value = 1
        except:
            self.could_make_instr_object_p.value = 0

        
        if self.could_write_python_file_p.value == 1:
            # The python file itself only contains the code for building
            # the corresponding instrument. Here code is added to:
            #  Run a simulation with same parameters / options as reference
            #  Compare the resulting data with the reference
            
            with open(self.python_filename, "r") as file:
                written_file = file.read()
        
            # Import compare_data module
            string =  "import os\n"
            string += "import compare_data\n"
            string += "os.chdir(\"" + self.input_path + "\")\n"
            string += written_file
        
            # Write the run command
            this_instrument_name = InstrReader.Reader.instr_name
            string += "\n"
            string += "data = " + this_instrument_name + ".run_full_instrument("
            string += "foldername=\"py_data_" + this_instrument_name + "\","
            string += "ncount=" + str(self.mcrun_options["ncount"]) + ","
            if "seed" in self.mcrun_options:
                string += "seed=" + str(self.mcrun_options["seed"]) + ","
            if "mpi" in self.mcrun_options:
                string += "mpi=" + str(self.mcrun_options["mpi"]) + ","
            string += "increment_folder_name=True)\n"
            string += "\n"
            
            # Load reference data
            ref_filename = os.path.join("..", self.base_foldername, "ref_data_" + self.name)
            string += "ref_data = functions.load_data(\"" + ref_filename + "\")\n"
            string += "\n"
            
            # Run comparison between produced data and loaedd reference data
            if self.show_different:
                string += "co = compare_data.compare_engine(show_different=True, name=\"" + self.name + "\")\n"
            else:
                string += "co = compare_data.compare_engine(name=\"" + self.name + "\")\n"
            string += "co.run_comparison(data, ref_data)\n"
            string += "co.print_history(show_all=True)\n"
            string += 'filename="../' + self.result_log_file_filename + '"\n'
            string += "co.write_history_to_file(filename=filename, mode='a', show_all=True)\n"

            # This file is overwriting the original py file created by the reader
            with open(self.python_filename, "w") as file:
                file.write(string)
                
    def write_read_instrument_file(self):
        """
        In case the reader completely fails to recreate an instrument,
        it is not possible to record the error message. This method
        creates a minimal python file that attempts to write the python
        file, and thus would recreate the problem in a minimal environemnt.
        This file is placed in the debug folder.
        """
        
        string = "\n"
        string += "from mcstasscript.interface import instr, functions, plotter, reader\n"
        string += "InstrReader = reader.McStas_file(\"" + self.instrument_path + "\")\n"
        string += "InstrReader.write_python_file(\"" + self.name + "_file_debug\", force=True)\n"
    
        with open(self.generate_python_file_filename, "w") as file:
            file.write("# Reads McStas instrument file and creates python version\n")
            file.write(string)
    
    def write_read_instrument_object(self):
        """
        In case the reader completely fails to recreate an instrument,
        it is not possible to record the error message. This method
        creates a minimal python file that attempts to make the python
        object, and thus would recreate the problem in a minimal
        environemnt. This file is placed in the debug folder.
        """
    
        string = "\n"
        string += "from mcstasscript.interface import instr, functions, plotter, reader\n"
        string += "InstrReader = reader.McStas_file(\"" + self.instrument_path + "\")\n"
        string += "instrument_object = instr.McStas_instr(\"" + self.name + "_object_debug\")"
        string += "InstrReader.add_to_instr(instrument_object)"
        
        with open(self.generate_python_object_filename, "w") as file:
            file.write("# Reads McStas instrument file and creates python object\n")
            file.write(string)

    def run_reference(self):
        """
        Runs reference simulation using given McStas instrument file path.
        The simulation is performed in the input_path folder to ensure
        the same component versions as the McStasScript versions are used.
        It is important same ncount, mpi and seed is used for exact comparisons.
        A single parameter is loaded to avoid mcrun asking for parameter values.
        """
        
        filename = os.path.join("..", self.base_foldername, "ref_data_" + self.instrument_name)
        option_string = "-n " + str(self.mcrun_options["ncount"]) # Set ncount
        option_string += " -d " + filename
        if "mpi" in self.mcrun_options:
            option_string += " --mpi=" + str(self.mcrun_options["mpi"]) # Set mpi
        if "seed" in self.mcrun_options:
            option_string += " --seed=" + str(self.mcrun_options["seed"]) # Set seed
        
        mcrun_path = "/Applications/McStas-2.5.app/Contents/Resources/mcstas/2.5/bin/"

        command = mcrun_path + "mcrun " + option_string + " " + self.instrument_path

        # Extract a single parameter
        if len(self.instrument_object.parameter_list) > 0:
            name = self.instrument_object.parameter_list[0].name
            value = self.instrument_object.parameter_list[0].value
            command += " " + name + "=" + str(value)
        
        self.started_reference_run_p.value = 1
        print(command)
        try:
            os.chdir(self.input_path)
            process = subprocess.run(command, shell=True,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     universal_newlines=True)
            
            #print(process.stderr)
            #print(process.stdout)
            
            os.chdir(self.cwd)
            
            if self.run_log_ref_filename is not None and self.log_initialized_p.value == 1:
                with open(self.run_log_ref_filename, "a") as file:
                    file.write(process.stderr)
                    file.write(process.stdout)
        
            self.completed_reference_run_p.value = 1
        
        except:
            os.chdir(self.cwd)
            self.completed_reference_run_p.value = 0

    def run_file_version(self):
        """
        Running the McStasScript produced file version of reference
        McStas instrument. Performed in input_path directory.
        """
        # Running file version
        command = "python3 " + os.path.join(self.input_path, self.instrument_name + "_generated.py")

        self.started_file_run_p.value = 1
        print(command)
        try:
            process = subprocess.run(command, shell=True,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,
                                     universal_newlines=True)
                                     
            #print(process.stderr)
            #print(process.stdout)
            if self.run_log_file_filename is not None and self.log_initialized_p.value == 1:
                with open(self.run_log_file_filename, "a") as file:
                    file.write(process.stderr)
                    file.write(process.stdout)
        
            self.completed_file_run_p.value = 1
    
        except:
            self.completed_file_run_p.value = 0

    def read_file_log(self):
        """
        The McStasScript python file generates a log file of a comparison
        between the file version and the reference, this log file is read
        here to include the status in the metadata of this class.
        
        self.file_mismatches contain the number of monitors with different
        data
        """
        comparison_data = []
        data_mode = False
        with open(self.result_log_file_filename, mode="r") as file:
            line = file.readline()
            while line:
                if not data_mode:
                    if line.count("Results") > 0:
                        data_mode = True
                else:
                    if len(line) > 2:
                        data = line.strip().split(" ")
                        monitor_name = data[0]
                        if data[-1] == "succeeded":
                            comparison_data.append((monitor_name, True))
                        elif data[-1] == "failed":
                            comparison_data.append((monitor_name, False))
                        
                line = file.readline()

        self.file_comparison = comparison_data
        
        # Count number of failures
        if len(comparison_data) == 0:
            # Somehow no data loaded
            self.file_mismatches = None
        else:
            self.file_mismatches = 0
            for test in self.file_comparison:
                if not test[1]:
                    self.file_mismatches += 1

    def run_object_version(self):
        """
        Running the McStasScript object version of the reference instrument.
        Print output is stored in a log file and a comparison to reference
        data is made.
        """

        self.object_comparison = compare_data.compare_engine(show_different=self.show_different, name=self.name + " object_version")

        print("Running object version of", self.instrument_name)
        orig_stdout = sys.stdout
        try:
            self.started_object_run_p.value = 1
            
            with open(self.run_log_object_filename, "a") as file:
                sys.stdout = file
        
                print("Given mcrun_options:", self.mcrun_options)
        
                foldername = os.path.join(self.base_foldername, self.instrument_name + "_object_data")
                object_data = self.instrument_object.run_full_instrument(**self.mcrun_options,
                                                                         foldername=foldername,
                                                                         increment_folder_name=True)
                
                print("Internalized input_path:", self.instrument_object.input_path)
                
                ref_data = functions.load_data(os.path.join(self.base_foldername, "ref_data_" + self.instrument_name))

                self.object_comparison.run_comparison(object_data, ref_data)
                self.object_mismatches = self.object_comparison.n_mismatches
        
            sys.stdout = orig_stdout
            self.completed_object_run_p.value = 1

        except:
            sys.stdout = orig_stdout
            self.completed_object_run_p.value = 0


    def logging(self):
        """
        Writes logging data and an overall summary to the log directory.
        """
    
        if self.completed_object_run_p.value == 1:
            self.object_comparison.write_history_to_file(self.result_log_object_filename, mode="a", show_all=True)

        with open(self.read_log_filename, "a") as file:
            file.write(self.status_string())

    def status_string(self):
        """
        Produces a string that describes status of reproduce task.
        The first two tasks from the left are related to the reader,
        which then forks into a file (F) and object (O) version.
        The reference run uses the parameters read in the object, and
        so depends on that being performed. An R indicates running.
        If any step fails, an X is printed instead. An example is shown
        below where everything succeeds.
        
                 F - R - File success
                /
         - R - R
                \
                 O - Ref success
                  \
                   O - R - Object success
        """

        lines = []
        lines.append("         ")
        if self.could_write_python_file:
            lines[0] += "F -"
        else:
            lines[0] += "X -"
        
        if self.started_file_run:
            lines[0] += " R -"
        else:
            lines[0] += " X -"
        
        if self.completed_file_run:
            lines[0] += " File success"
        else:
            lines[0] += " File failure"
        
        lines.append("        /")
        
        lines.append("")
        if self.performed_read_instrument:
            lines[2] += " - S -"
        else:
            lines[2] += " - O -"

        if self.could_start_reader:
            lines[2] += " S"
        else:
            lines[2] += " X"

        lines.append("        \\")

        lines.append("         ")

        if self.could_make_instr_object:
            lines[4] += "O -"
        else:
            lines[4] += "X -"

        if self.started_reference_run:
            lines[4] += " R -"
        else:
            lines[4] += " X -"

        if self.completed_reference_run:
            lines[4] += " Ref success"
        else:
            lines[4] += " Ref failure"

        lines.append("          \\")

        lines.append("           ")

        if self.started_object_run:
            lines[6] += "R -"
        else:
            lines[6] += "X -"

        if self.completed_object_run:
            lines[6] += " Obj success"
        else:
            lines[6] += " Obj failure"

        string = "\n"
        for line in lines:
            string += line + "\n"

        return string

    def print_status(self):
        """
        Prints the status to terminal
        """
    
        print(self.status_string())

    def print_result_verbal(self):
        """
        Prints an overview including a verbal message on the number
        of sucessful data comparisons for file and object versions.
        """
        print(self.name)
        print(self.status_string())

        if self.file_comparison is None:
            print("File run failed.")
        else:
            if self.file_mismatches == 0:
                print("File results matched reference in all cases")
            else:
                print("File results did not match reference in " + str(self.file_mismatches) + " cases.")

        if self.object_comparison is None:
            print("Object run failed.")
        else:
            if self.object_mismatches == 0:
                print("Object results matched reference in all cases")
            else:
                print("Object results did not match reference in " + str(self.object_mismatches) + " cases.")

    def print_result_short(self):
        """
        Prints an overview including a short message on the number
        of sucessful data comparisons for file and object versions.
        """
        print("-"*10, " ", self.name, " ", "-"*20)
        print(self.status_string())

        if self.file_comparison is None:
            print("File run failed.")
        else:
            print("File   comparisons: ", end="")
            for mon in self.file_comparison:
                if mon[1]:
                    print(".", end="")
                else:
                    print("X", end="")
            print()
    
        if self.object_comparison is None:
            print("Object run failed.")
        else:
            print("Object comparisons: ", end="")
            for mon in self.object_comparison.history:
                if mon[1]:
                    print(".", end="")
                else:
                    print("X", end="")
            print()

        print()

def list_from_instr_file_list(filename):
    """
    Function for making a list of instrument names from a list
    of instrument files. Such a file can be made with:
    ls *.instr > file_list.txt
    """
    
    instruments = []
    with open(filename, mode="r") as file:
        line = file.readline()
        while line:
            instrument_name = os.path.splitext(os.path.basename(line))[0]
            instruments.append(instrument_name)
            
            line = file.readline()

    return instruments

def instr_from_folder(foldername):
    """
    Function for making a list of instrument names contained
    in given directory
    """
    
    files = os.listdir(foldername)
    
    instruments = []
    for file in files:
        name = os.path.splitext(os.path.basename(file))[0]
        suffix = os.path.splitext(os.path.basename(file))[1]
        if suffix == ".instr":
            instruments.append(name)

    return instruments

def list_to_string(list, max=10, pad=0):
    """
    Function for formatting large number of str list elements
    into terminal print. Max is max number per line, pad is
    whitespaces before the next line.
    """

    string = ""
    cnt = 0
    for name in list:
        string += name + "  "
        cnt += 1
        if cnt == max and name != list[-1]:
            string += "\n" + " "*pad
            cnt = 0
    return string


