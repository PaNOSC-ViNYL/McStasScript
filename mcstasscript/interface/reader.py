import os
from mcstasscript.instr_reader.control import InstrumentReader
from mcstasscript.interface.instr import McStas_instr

class McStas_file:
    """
    Reader of McStas files, can add to an existing McStasScript
    instrument instance or create a corresponding McStasScript python
    file.
    
    
    Methods
    -------
    
    add_to_instr(Instr)
        Add information from McStas file to McStasScript Instr instance
        
    write_python_file(filename)
        Write python file named filename that reproduce the McStas instr 
    
    """
    
    def __init__(self, filename):
        """
        Initialization of McStas_file class, needs McStas instr filename

        Parameters
        ----------
            filename (str)
                Name of McStas instrument file to be read
        """

        # Check filename
        if not os.path.isfile(filename):
            raise ValueError("Given filename, \"" + filename
                             + "\" could not be found.")

        self.Reader = InstrumentReader(filename)

    def add_to_instr(self, Instr):
        """
        Adds information from the McStas file to McStasScript instr

        Parameters
        ----------
            Instr (McStasScript McStas_instr instance)
                McStas_instr instance to add instrument information to    
        """

        # Check Instr
        if not isinstance(Instr, McStas_instr):
            raise TypeError("Given object is not of type McStas_instr!")
        
        self.Reader.add_to_instr(Instr)

    def write_python_file(self, filename, **kwargs):
        """
        Writes python file that reproduces McStas instrument file

        Parameters
        ----------
            filename (str)
                Filename of python file to be written    
        """

        if "force" in kwargs:
            force = kwargs["force"]
        else:
            force = False

        # Check product_filename is available
        if os.path.isfile(filename):
            if force:
                os.remove(filename)
            else:
                raise ValueError("Filename \"" + filename 
                                 + "\" already exists, you can overwrite with "
                                 + "force=True")

        self.Reader.generate_py_version(filename)
        
