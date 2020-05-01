import io
import os
from decimal import Decimal

from mcstasscript.interface.instr import McStas_instr
from mcstasscript.instr_reader.read_definition import DefinitionReader
from mcstasscript.instr_reader.read_declare import DeclareReader
from mcstasscript.instr_reader.read_initialize import InitializeReader
from mcstasscript.instr_reader.read_trace import TraceReader
from mcstasscript.instr_reader.read_finally import FinallyReader

class InstrumentReader:
    """
    This class controls loading of a McStas file as a McStasScript object.
    
    This is done by reading the McStas file line by line while using the
    McStasScript API to load the information into the Instr object.
    
    Optionally a Python file with the McStasScript commands required to 
    replicate the McStas instrument can be written to disk.
    
    
    
    Methods
    -------
    __init__(filename)
        Initializes reading of McStas instrument with given filename
    
    generate_py_version(product_filename)
        Generates a file named product_filename.py that recreates instr
        
    add_to_instr(Instr)
        Inserts information from instr file into McStasScript Instr instance
    
    """
    
    def __init__(self, filename):
        """
        Initialize the InstrumentReader with a target McStas instrument
        file. Use generate_py_version method for writing an eqvivalent
        McStasScript python file or the add_to_instr method to load this
        instrument file onto a Instr McStasScript object.
        """
    
        self.filename = filename
        self.Instr = None # could set it up to create Instr
        self.write_file = False
        self.product_filename = "mc_script.py"
        self.instr_name = ""
        self.file_data = None
        self.line_index = 0
        self.file_length = 0
                
    def generate_py_version(self, product_filename):
        """
        Generate a McStasScript version of the instrument file used for 
        initialize of the InstrumentReader object. The filename given is
        for the generated file.
        
        One should use this feature with some caution. Look through the
        generated McStasScript file and compare some output with the
        original insturment file to ensure everything was loaded correctly.
        """

        # Generate dummy instr object
        self.Instr = McStas_instr("dummy_object_for_generating_file")
        
        self.product_filename = product_filename
        self.write_file = True
        
        if os.path.isfile(self.product_filename):
            os.remove(self.product_filename)
        
        self._read_file()
        
    def add_to_instr(self, Instr):
        """
        Add contents of McStas instrument file selected in initialize
        to an McStasScript instrument object.
        """
        
        self.Instr = Instr
        self.write_file = False
        
        self._read_file()
        
    def _open_file(self):
        """
        Internal method that opens the instrument file to be read
        """
        
        with open(self.filename) as file:
            self.file_data = file.readlines()
            
        self.file_length = len(self.file_data)
        self.line_index = 0
            
    def _get_next_line(self):
        """
        Internalmethod that gets the next line to be read
        """
        
        line = self.file_data[self.line_index]
        self.line_index += 1
        return line
        
    def _return_line(self):
        """
        Internal method that puts line back into stack
        """
        
        self.line_index -= 1
        
    def _read_file(self):
        """
        Master method for reading the instrument file.  It goes through 
        the file line by line, and checks which part of the instrument 
        file it is currently reading. There are separate methods for 
        reading the individual parts of the instrument file to reduce
        clutter.
        """
        
        # Initialize readers of the different McStas instrument sections
        args = [self.Instr, self.write_file, self.product_filename, self._get_next_line, self._return_line]
        self.Definition_reader = DefinitionReader(*args)
        self.Declare_reader = DeclareReader(*args)
        self.Initialize_reader = InitializeReader(*args)
        self.Trace_reader = TraceReader(*args)
        self.Finally_reader = TraceReader(*args)

        # A mode for each type that activates the correct reader function
        definition_mode = False
        declare_mode = False
        initialize_mode = False
        trace_mode = False
        finally_mode = False
        comment_mode = False
        any_mode = False
        
        # check if insturment name has be read from file yet
        instr_name_read = False
        
        self._open_file()
        
        #for line in self.file_data:
        while self.line_index < self.file_length:
            
            line = self._get_next_line()

            # Find appropriate mode
            if line.strip().startswith("DEFINE INSTRUMENT") and not any_mode:
                definition_mode = True
                any_mode = True

            if line.strip().startswith("DECLARE") and not any_mode:
                declare_mode = True
                any_mode = True

            if (line.strip().startswith("INITIALIZE") or
                line.strip().startswith("INITIALISE")) and not any_mode:
                initialize_mode = True
                any_mode = True

            if line.strip().startswith("TRACE") and not any_mode:
                trace_mode = True
                any_mode = True

            if line.strip().startswith("FINALLY") and not any_mode:
                finally_mode = True
                any_mode = True

            if line.strip().startswith("/*"):
                comment_mode = True        

            # Read with appropriate reader
            if definition_mode and not comment_mode:
                # Get instrument name
                if not instr_name_read:
                    self.instr_name = line.split("(")[0].strip().split(" ")[-1]
                    instr_name_read = True
                    self.update_file_name()

                # Read line from definition
                definition_mode = self.Definition_reader.read_definition_line(line)
                # When read_definition finds the end, it will return False
                any_mode = definition_mode

            if declare_mode and not comment_mode:
                # Read line from definition
                declare_mode = self.Declare_reader.read_declare_line(line)
                # When read_declare finds the end, it will return False
                any_mode = declare_mode

            if initialize_mode and not comment_mode:
                # Read line from initialize
                initialize_mode = self.Initialize_reader.read_initialize_line(line)
                # When read_initialize finds the end, it will return False
                any_mode = initialize_mode

            if trace_mode and not comment_mode:
                # Read line from initialize
                trace_mode = self.Trace_reader.read_trace_line(line)
                # When read_initialize finds the end, it will return False
                any_mode = trace_mode

            if finally_mode and not comment_mode:
                # Read line from finally
                finally_mode = self.Finally_reader.read_finally_line(line)
                # When read_finallyfinds the end, it will return False
                any_mode = finally_mode

            # Stop comment mode when end of comment block reached
            if "*/" in line.strip():
                comment_mode = False
        
    def update_file_name(self):
        """
        Updates filename for reader subclasses
        """
            
        self.Definition_reader.set_instr_name(self.instr_name)
        self.Declare_reader.set_instr_name(self.instr_name)
        self.Initialize_reader.set_instr_name(self.instr_name)
        self.Trace_reader.set_instr_name(self.instr_name)
        self.Finally_reader.set_instr_name(self.instr_name)
        
