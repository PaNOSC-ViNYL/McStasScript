
import os
import sys
import random
import getopt
from datetime import datetime

import reproduce

from mcstasscript.interface import instr, functions, plotter, reader

def main(argv):
    """
    Terminal tool for testing McStasScript conversion from instrument files
    into python objects and python files.
    """
    
    try:
        opts, args = getopt.getopt(argv, "hf:t:n:s",["folder=", "tests=", "ncount=", "seed=", "mpi=", "different", "timeout="])
    except getopt.GetoptError:
        print("Error in input, use -h for more information.")
        print("reproduce_examples.py -f <foldername> -t <n tests> -n <ncount> -s <seed> --mpi <n cores> --different")
        sys.exit(2)

    # Set defaults
    foldername = None
    n_tests = None
    show_different = False
    mcrun_options = {}
    timeout = 300
    
    for opt, arg in opts:
        if opt == "-h":
            print("-"*5 + " HELP " + "-"*66)
            print("This utility tries to recreate all instruments in given folder with McStasScript")
            print("reproduce_examples.py -f <foldername> -t <n tests> -n <ncount> -s <seed> --mpi <n cores> --timeout <time in s> --different")
            print("long options: --folder --tests --ncount --seed --mpi")
            print("-f --folder: The folder from which insturments are grabed, default McStas examples")
            print("-t --tests : Number of tests performed (randomly selected from folder), default all")
            print("-n --ncount: Number of rays to use in McStas")
            print("-s --seed  : Seed to use for McStas simulation")
            print("--mpi      : Number of cores to use for McStas simulation")
            print("--timeout  : Time in seconds before timeout of a task (3 McStas runs), default: 300 s")
            print("--different: Will show plot of data and differences when discrepencies found, stops run")
            print("")
            sys.exit()
        elif opt in ("-f", "--folder"):
            foldername = arg
        elif opt in ("-t", "--tests"):
            n_tests = int(arg)
        elif opt in ("-n", "--ncount"):
            mcrun_options["ncount"] = int(float(arg))
        elif opt in ("-s", "--seed"):
            mcrun_options["seed"] = arg
        elif opt == "--mpi":
            mcrun_options["mpi"] = int(arg)
        elif opt == "--different":
            show_different = True
        elif opt == "--timeout":
            timeout = float(arg)

    if foldername is None:
        configurator = functions.Configurator()
        config = configurator._read_yaml()
        mcstas_path = config["paths"]["mcstas_path"]
        foldername = os.path.join(mcstas_path, "examples")
    else:
        # check given folder exists
        if not os.path.isdir(foldername):
            print("Could not find given foldername, " + foldername + ", aborting.")
            sys.exit(2)

        # find absolute path
        if not os.path.isabs(foldername):
            foldername = os.path.abspath(foldername)
        
    instrument_names = reproduce.instr_from_folder(foldername)
    if n_tests is not None and n_tests < len(instrument_names):
        instrument_names = random.choices(instrument_names, k=n_tests)

    instrument_paths = []
    for instrument_name in instrument_names:
        instrument_paths.append(os.path.join(foldername, instrument_name + ".instr"))

    if not os.path.isdir("logs"):
        if not os.path.isfile("logs"):
            os.mkdir("logs")
        else:
            raise ValueError("Needed to make 'logs' directory, but a logs file already exist!")

    today = datetime.now()
    log_path = os.path.join("logs", today.strftime('%Y%m%d_%H%M%S'))
    os.mkdir(log_path)

    N_instruments = len(instrument_names)

    print("Will attempt to reproduce the following instruments: ")
    print(" "*10 + reproduce.list_to_string(instrument_names, max=5, pad=10))
    print("Performing runs!")


    write_file_fails = []
    file_fails = []
    file_match = []
    file_mismatch = []

    make_object_fails = []
    object_fails = []
    object_match = []
    object_mismatch = []

    run_timeouts = []

    progress_cnt = 0
    for instrument_path in instrument_paths:
        
        print("Progress: ", progress_cnt, "of", N_instruments)
        progress_cnt += 1
        
        rep = reproduce.from_reference(instrument_path, log_path, input_path="input_folder",
                                       mcrun_options=mcrun_options, show_different=show_different,
                                       timeout=timeout)
        rep.run_all()
        
        if not rep.could_write_python_file:
            write_file_fails.append(rep.name)
        else:
            if not rep.completed_file_run:
                file_fails.append(rep.name)
            else:
                if rep.file_mismatches == 0:
                    file_match.append(rep.name)
                else:
                    file_mismatch.append(rep.name)


        if not rep.could_make_instr_object:
            make_object_fails.append(rep.name)
        else:
            if not rep.completed_object_run:
                object_fails.append(rep.name)
            else:
                if rep.object_mismatches == 0:
                    object_match.append(rep.name)
                else:
                    object_mismatch.append(rep.name)

        if rep.timeout_status:
            run_timeouts.append(rep.name)


    max_per_line = 8
    format_pad = 41

    result_string = ""
    result_string = "-- File results " + "-"*40 + " - - -" + "\n"

    result_string += "   Couldn't write file for:              "
    result_string += reproduce.list_to_string(write_file_fails, max=max_per_line, pad=format_pad)
    result_string += "\n"

    result_string += "   Run didn't complete for:              "
    result_string += reproduce.list_to_string(file_fails, max=max_per_line, pad=format_pad)
    result_string += "\n"

    result_string += "   File run did not match reference:     "
    result_string += reproduce.list_to_string(file_mismatch, max=max_per_line, pad=format_pad)
    result_string += "\n"

    result_string += "   File run matches reference:           "
    result_string += reproduce.list_to_string(file_match, max=max_per_line, pad=format_pad)
    result_string += "\n\n"

    N_file_success = len(file_match)
    success_float = 100*N_file_success/N_instruments
    success_percentage = '%.2f' % success_float
    result_string += "   Of " + str(N_instruments) + " instruments, " + str(N_file_success) + " succeeded. "
    result_string += str(success_percentage) + "%\n\n"

    result_string += "-- Object results " + "-"*38 + " - - -" + "\n"

    result_string += "   Couldn't make object for:             "
    result_string += reproduce.list_to_string(make_object_fails, max=max_per_line, pad=format_pad)
    result_string += "\n"

    result_string += "   Run didn't complete for:              "
    result_string += reproduce.list_to_string(object_fails, max=max_per_line, pad=format_pad)
    result_string += "\n"

    result_string += "   Object run did not match reference:   "
    result_string += reproduce.list_to_string(object_mismatch, max=max_per_line, pad=format_pad)
    result_string += "\n"

    result_string += "   Object run matches reference:         "
    result_string += reproduce.list_to_string(object_match, max=max_per_line, pad=format_pad)
    result_string += "\n\n"

    N_object_success = len(object_match)
    success_float = 100*N_object_success/N_instruments
    success_percentage = "%.2f" % success_float
    result_string += "   Of " + str(N_instruments) + " instruments, " + str(N_object_success) + " succeeded. "
    result_string += str(success_percentage) + "%\n\n"

    result_string += "-- End notes      " + "-"*38 + " - - -" + "\n"

    result_string += "   Runs which timed out:                 "
    result_string += reproduce.list_to_string(run_timeouts, max=max_per_line, pad=format_pad)
    result_string += "\n\n"

    N_timeouts = len(run_timeouts)
    timeout_float = 100*N_timeouts/N_instruments

    timeout_percentage = "%.2f" % timeout_float
    result_string += "   Of " + str(N_instruments) + " instruments, " + str(N_timeouts) + " timed out. "
    result_string += str(timeout_percentage) + "%\n\n"

    print(result_string)

    with open(os.path.join(log_path, "summary.log"), "w") as file:
        file.write(result_string)

if __name__ == "__main__":
    main(sys.argv[1:]) # drop script name from arguments

