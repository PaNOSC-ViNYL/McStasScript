from mcstasscript.instr_reader.util import SectionReader

class InitializeReader(SectionReader):
    """
    Reads the initialize section of a McStas instrument file.
    The initialize lines are added to the McStasScript instrument, and 
    are sent to the function writing the lines to the python file.
    """
    
    def __init__(self, Instr, write_file, product_filename, get_next_line, return_line):
        super().__init__(Instr, write_file, product_filename, get_next_line, return_line)
        
    def read_initialize_line(self, line):
        """
        Reads lines from INITIALIZE file and returns True as long as
        the stop characters has not been encountered. Comments are
        ignored with typical c syntax.
        """
        
        continue_initialize = True
        
        # Remove comments
        if "//" in line:
            line = line.split("//", 1)[0].strip()
            
        if line.startswith("INITIALIZE"):
            line = line.split("INITIALIZE", 1)[1].strip()
            
        if line.startswith("INITIALISE"):
            line = line.split("INITIALISE", 1)[1].strip()
            
        # Remove block opening
        if "%{" in line:
            line = line.split("%{", 1)[1].strip()
            
        if "%}" in line:
            line = line.split("%}", 1)[0].strip()
            continue_initialize = False
            
        # If the line is just a new line quit
        if line is "\n" or line is "":
            return continue_initialize
        
        # Remove newline at the end of the line
        if line.endswith("\n"):
            line = line[:-1]
            
        self.Instr.append_initialize(line)
        
        # Need to prepare string for being written again
        write_line = line.replace("\\n","\\\\n")
        write_line = write_line.replace("\\t","\\\\t")
        write_line = write_line.replace('"', '\\\"')
        # May need to expand to more cases
        
        # Write line to Python file
        write_string = []
        write_string.append(self.instr_name)
        write_string.append(".append_initialize(")
        write_string.append("\"" + write_line + " \"") 
        write_string.append(")\n")
        
        self._write_to_file(write_string)
        
        return continue_initialize