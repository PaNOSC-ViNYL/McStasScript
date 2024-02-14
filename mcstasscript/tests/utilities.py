import os


def work_dir_test(func):
    def wrapper():
        THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        current_work_dir = os.getcwd()

        os.chdir(THIS_DIR)  # Set work directory to test folder

        func()

        os.chdir(current_work_dir)  # Return to previous workdir

    return wrapper
