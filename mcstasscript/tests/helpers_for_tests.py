import os

class WorkInTestDir:
    """
    Simple class that enables working in test directory
    """
    def __enter__(self):
        self.current_work_dir = os.getcwd()
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.current_work_dir)