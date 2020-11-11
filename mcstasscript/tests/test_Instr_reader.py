import os
import sys
import unittest

from mcstasscript.interface import instr
from mcstasscript.instr_reader import control
from mcstasscript.instr_reader import util


# Disable print
def blockPrint():
    sys.stdout = open(os.devnull, 'w')

# Restore print
def enablePrint():
    sys.stdout = sys.__stdout__


def set_dummy_dir():
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(os.path.join(THIS_DIR, "dummy_instrument_folder"))

def setup_standard(Instr):
    set_dummy_dir()
    filename = "Union_demonstration_test.instr"
    InstrReader = control.InstrumentReader(filename)
    InstrReader.add_to_instr(Instr)
    
    return InstrReader

def setup_standard_auto_instr():
    set_dummy_dir()
    
    blockPrint()
    Instr = instr.McStas_instr("test_instrument")
    enablePrint()

    return setup_standard(Instr)

class TestInstrReader(unittest.TestCase):
    
    def test_read_instrument_name(self):
        """
        Check if the instrument name is read correctly
        """

        set_dummy_dir()
        
        blockPrint()
        Instr = instr.McStas_instr("test_instrument")
        enablePrint()

        filename = "Union_demonstration_test.instr"
        InstrReader = control.InstrumentReader(filename)
        InstrReader.add_to_instr(Instr)

        self.assertEqual(InstrReader.instr_name, "Union_demonstration")

    def test_read_input_parameter(self):
    
        set_dummy_dir()
        
        blockPrint()
        Instr = instr.McStas_instr("test_instrument")
        enablePrint()
        InstrReader = setup_standard(Instr)
        
        self.assertEqual(Instr.parameter_list[0].name, "stick_displacement")
        # space in type inserted for easier writing by McStas_Instr class
        self.assertEqual(Instr.parameter_list[0].type, "double ")
        self.assertEqual(Instr.parameter_list[0].value, 0)
        
        self.assertEqual(Instr.parameter_list[1].name, "test_int")
        # space in type inserted for easier writing by McStas_Instr class
        self.assertEqual(Instr.parameter_list[1].type, "int ")
        self.assertEqual(Instr.parameter_list[1].value, 3)
        
        self.assertEqual(Instr.parameter_list[2].name, "test_str")
        # space in type inserted for easier writing by McStas_Instr class
        self.assertEqual(Instr.parameter_list[2].type, "string ")
        self.assertEqual(Instr.parameter_list[2].value, "\"\\\"hurray\\\"\"")

    def test_read_declare_parameter(self):
        
        set_dummy_dir()
        
        blockPrint()
        Instr = instr.McStas_instr("test_instrument")
        enablePrint()
        InstrReader = setup_standard(Instr)
        
        self.assertEqual(Instr.declare_list[0].name, "sample_1_index")
        self.assertEqual(Instr.declare_list[0].type, "int")
        self.assertEqual(Instr.declare_list[0].value, 27)
        
        self.assertEqual(Instr.declare_list[8].name, "array")
        self.assertEqual(Instr.declare_list[8].type, "double")
        self.assertEqual(Instr.declare_list[8].vector, 3)
        self.assertEqual(Instr.declare_list[8].value, [0.1, 0.2, 0.3])
        
        self.assertEqual(Instr.declare_list[9].name, "I_array")
        self.assertEqual(Instr.declare_list[9].type, "int")
        self.assertEqual(Instr.declare_list[9].vector, 4)
        
        self.assertEqual(Instr.declare_list[10].name, "T_array")
        self.assertEqual(Instr.declare_list[10].type, "int")
        self.assertEqual(Instr.declare_list[10].vector, 5)
        self.assertEqual(Instr.declare_list[10].value, [1, 2, 3, 4, 5])
        
        self.assertEqual(Instr.declare_list[11].name, "home")
        self.assertEqual(Instr.declare_list[11].type, "char")
        self.assertEqual(Instr.declare_list[11].vector, 20)
        self.assertEqual(Instr.declare_list[11].value, "\"\\\"test_string\\\"\"")
        
    def test_read_initialize_line(self):
    
        set_dummy_dir()
        
        blockPrint()
        Instr = instr.McStas_instr("test_instrument")
        enablePrint()
        InstrReader = setup_standard(Instr)
        
        self.assertEqual(Instr.initialize_section,
                         "// Start of initialize for generated test_instrument\n"
                         + "I_array[2] = 8;\n"
                         + "printf(\"Hello world\\n\");\n")
        
    # Check a few components are read correctly
    def test_read_component_1(self):
        
        set_dummy_dir()
        
        blockPrint()
        Instr = instr.McStas_instr("test_instrument")
        enablePrint()
        InstrReader = setup_standard(Instr)
        
        components = Instr.component_list
        
        test_component = None
        
        for component in components:
            if component.name == "Al":
                test_component = component
        
        self.assertEqual(test_component.component_name, "Union_make_material")
        
        val = getattr(test_component, "my_absorption")
        #self.assertEqual(val, "\"100*4*0.231/66.4\"")
        self.assertEqual(val, "100*4*0.231/66.4")
        
        val = getattr(test_component, "process_string")
        self.assertEqual(val, "\"Al_incoherent,Al_powder\"")
        
        self.assertEqual(test_component.AT_data, ["0", "0", "0"])
        self.assertEqual(test_component.AT_relative, "ABSOLUTE")
        
        self.assertEqual(test_component.ROTATED_data, [0, 0, 0])
        self.assertEqual(test_component.ROTATED_relative, "ABSOLUTE")
        
    def test_read_component_2(self):
        
        set_dummy_dir()
        
        blockPrint()
        Instr = instr.McStas_instr("test_instrument")
        enablePrint()
        InstrReader = setup_standard(Instr)
        
        components = Instr.component_list
        
        test_component = None
        
        for component in components:
            if component.name == "sample_holder3":
                test_component = component
        
        self.assertEqual(test_component.component_name, "Union_box")
        
        val = getattr(test_component, "xwidth")
        self.assertEqual(val, "0.0098")
        
        val = getattr(test_component, "priority")
        self.assertEqual(val, "52")
        
        self.assertEqual(test_component.AT_data, ["0", "-0.03", "-0.03*0.35-0.004"])
        self.assertEqual(test_component.AT_relative, "RELATIVE sample_rod_bottom")
        
        self.assertEqual(test_component.ROTATED_data, ["-25", "0", "0"])
        self.assertEqual(test_component.ROTATED_relative, "RELATIVE sample_rod_bottom")

    def test_read_component_WHEN(self):
    
        set_dummy_dir()
        
        blockPrint()
        Instr = instr.McStas_instr("test_instrument")
        enablePrint()
        InstrReader = setup_standard(Instr)
        
        components = Instr.component_list
        
        test_component = None
        
        for component in components:
            if component.name == "outer_cryostat_vacuum":
                test_component = component
        
        self.assertEqual(test_component.component_name, "Union_cylinder")
        
        val = getattr(test_component, "radius")
        self.assertEqual(val, "0.09")
        
        val = getattr(test_component, "priority")
        self.assertEqual(val, "11")
        
        self.assertEqual(test_component.WHEN, "WHEN (necessary == 1 )")
        
        self.assertEqual(test_component.AT_data, ["0", "0.01", "0"])
        self.assertEqual(test_component.AT_relative, "RELATIVE beam_center")
        
        self.assertEqual(test_component.ROTATED_data, ["0", "0", "0"])
        self.assertEqual(test_component.ROTATED_relative, "RELATIVE beam_center")
        
    def test_read_component_EXTEND(self):
        
        set_dummy_dir()
        
        blockPrint()
        Instr = instr.McStas_instr("test_instrument")
        enablePrint()
        InstrReader = setup_standard(Instr)
        
        components = Instr.component_list
        
        test_component = None
        
        for component in components:
            if component.name == "test_sample":
                test_component = component
        
        self.assertEqual(test_component.component_name, "Union_master")
        
        val = getattr(test_component, "history_limit")
        self.assertEqual(val, "1000000")
        
        lines = test_component.EXTEND.split("\n")
        line0 = ("if (scattered_flag[sample_1_index] > 0) scattered_1 = 1;"
                 +" else scattered_1 = 0;")
        line1 = ("if (scattered_flag[sample_2_index] > 0) scattered_2 = 1;"
                 +" else scattered_2 = 0;")
        line2 = ("if (scattered_flag[sample_3_index] > 0) scattered_3 = 1;"
                 +" else scattered_3 = 0;")
        line3 = ("if (scattered_flag[sample_4_index] > 0) scattered_4 = 1;"
                 +" else scattered_4 = 0;")
        
        self.assertEqual(lines[0], line0)
        self.assertEqual(lines[1], line1)
        self.assertEqual(lines[2], line2)
        self.assertEqual(lines[3], line3)
        
        self.assertEqual(test_component.AT_data, ["0", "0", "0"])
        self.assertEqual(test_component.AT_relative, "RELATIVE beam_center")
        
        self.assertEqual(test_component.ROTATED_data, ["0", "0", "0"])
        self.assertEqual(test_component.ROTATED_relative, "RELATIVE beam_center")
        
    def test_read_component_GROUP(self):
        
        set_dummy_dir()
        
        blockPrint()
        Instr = instr.McStas_instr("test_instrument")
        enablePrint()
        InstrReader = setup_standard(Instr)
        
        components = Instr.component_list
        
        test_component = None
        
        for component in components:
            if component.name == "armA":
                test_component = component
        
        self.assertEqual(test_component.component_name, "Arm")
        
        self.assertEqual(test_component.GROUP, "arms")
        
        self.assertEqual(test_component.AT_data, ["0", "0", "0"])
        self.assertEqual(test_component.AT_relative, "ABSOLUTE")
        
    def test_read_component_SPLIT(self):
        
        set_dummy_dir()
        
        blockPrint()
        Instr = instr.McStas_instr("test_instrument")
        enablePrint()
        InstrReader = setup_standard(Instr)
        
        components = Instr.component_list
        
        test_component = None
        
        for component in components:
            if component.name == "sample_4_container":
                test_component = component
        
        self.assertEqual(test_component.component_name, "Union_cylinder")
        
        self.assertEqual(test_component.AT_data, ["0", "0", "0"])
        self.assertEqual(test_component.AT_relative, "RELATIVE sample_4")     
    
    def test_read_component_JUMP(self):
        """
        Check a JUMP and GROUP statement is read correctly
        """
        
        set_dummy_dir()
        
        blockPrint()
        Instr = instr.McStas_instr("test_instrument")
        enablePrint()
        InstrReader = setup_standard(Instr)
        
        components = Instr.component_list
        
        test_component = None
        
        for component in components:
            if component.name == "armB":
                test_component = component
        
        self.assertEqual(test_component.component_name, "Arm")
        
        self.assertEqual(test_component.GROUP, "arms")
        self.assertEqual(test_component.JUMP, "myself 2")
        
        self.assertEqual(test_component.AT_data, ["0", "0", "0"])
        self.assertEqual(test_component.AT_relative, "ABSOLUTE")

    def test_comma_split(self):
        """
        Test the Tracer_reader._split_func
        """
        
        InstrReader = setup_standard_auto_instr()
        
        test_string = "A,B,C,D(a,b),E"
        
        result = InstrReader.Trace_reader._split_func(test_string, ",")
        
        self.assertEqual(result[0],"A")
        self.assertEqual(result[1],"B")
        self.assertEqual(result[2],"C")
        self.assertEqual(result[3],"D(a,b)")
        self.assertEqual(result[4],"E")
    
    def test_comma_split_limited(self):
        """
        Test the Tracer_reader._split_func
        """
        
        InstrReader = setup_standard_auto_instr()
        
        test_string = "A,B,C,D(a,b),E"
        
        result = InstrReader.Trace_reader._split_func(test_string, ",",  2)
        
        self.assertEqual(result[0],"A")
        self.assertEqual(result[1],"B")
        self.assertEqual(result[2],"C,D(a,b),E")
    
        
    def test_parenthesis_split(self):
        """
        Test the Tracer_reader._split_func
        """
        
        InstrReader = setup_standard_auto_instr()
        
        test_string = "A)B)C)D(a,b))E"
        
        result = InstrReader.Trace_reader._split_func(test_string, ")")
        
        self.assertEqual(result[0],"A")
        self.assertEqual(result[1],"B")
        self.assertEqual(result[2],"C")
        self.assertEqual(result[3],"D(a,b)")
        self.assertEqual(result[4],"E")
        
    def test_comma_split_brack(self):
        """
        Test the Tracer_reader._split_func
        """

        InstrReader = setup_standard_auto_instr()
        
        test_string = "A,B{C,D(a,b)},E"
        
        result = InstrReader.Trace_reader._split_func_brack(test_string, ",")
        
        self.assertEqual(result[0],"A")
        self.assertEqual(result[1],"B{C,D(a,b)}")
        self.assertEqual(result[2],"E")    

    
if __name__ == '__main__':
    unittest.main()
