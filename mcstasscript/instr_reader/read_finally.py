from mcstasscript.instr_reader.util import SectionReader

class FinallyReader(SectionReader):
    
    def __init__(self, Instr, write_file, product_filename, get_next_line, return_line):
        
        super().__init__(Instr, write_file, product_filename, get_next_line, return_line)
        
    def read_finally_line(self, line):
        
        continue_finally = True
        
        # Remove comments
        if "//" in line:
            line = line.split("//", 1)[0].strip()
            
        if line.startswith("FINALLY"):
            line = line.split("FINALLY", 1)[1].strip()
            
        # Remove block opening
        if "%{" in line:
            line = line.split("%{", 1)[1].strip()
            
        if "%}" in line:
            line = line.split("%}", 1)[0].strip()
            continue_finally = False
            
        # If the line is just a new line quit
        if line is "\n" or line is "":
            return continue_finally
        
        # Remove newline at the end of the line
        if line.endswith("\n"):
            line = line[:-1]
            
        self.Instr.append_finally(line)
        
        if self.write_file:
            # Cant get both \n and " to work in written string
            write_line = line.replace("\\n","\\\\n")
            #write_line = line.replace("\\n","test")
            write_line = write_line.replace("\\t","\\\\t")
            # May need to expand to more cases
            
            write_line = write_line.replace('"', '\\\"')
            
            write_string = []
            write_string.append(self.instr_name)
            write_string.append(".append_finally(")
            write_string.append("\"" + write_line + "\"") 
            write_string.append(")\n")
            
            self._write_to_file(write_string)
        
        return continue_finally