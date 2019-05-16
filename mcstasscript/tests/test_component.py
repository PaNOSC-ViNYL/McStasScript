import builtins
import unittest
import unittest.mock

from mcstasscript.helper.mcstas_objects import component

def setup_component_all_keywords():
    
    return component("test_component",
                     "Arm",
                     AT = [0.124, 183.9, 157],
                     AT_RELATIVE = "home",
                     ROTATED = [482, 1240.2, 0.185],
                     ROTATED_RELATIVE = "etc",
                     WHEN = "1==2",
                     EXTEND = "nscat = 8;",
                     GROUP = "developers",
                     JUMP = "myself 37",
                     comment = "test comment")
    
def setup_component_relative():
    
    return component("test_component",
                     "Arm",
                     AT = [0.124, 183.9, 157],
                     ROTATED = [482, 1240.2, 0.185],
                     RELATIVE = "source",
                     WHEN = "1==2",
                     EXTEND = "nscat = 8;",
                     GROUP = "developers",
                     JUMP = "myself 37",
                     comment = "test comment")
    

class Testcomponent(unittest.TestCase):
    """
    Components are the building blocks used to create an instrument in
    the McStas meta language. They describe spatially seperated parts
    of the neutron scattering instrument. Here the class component is 
    tested.
    """
    
    def test_component_basic_init(self):
        
        comp = component("test_component", "Arm")
        
        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")

    def test_component_basic_init_defaults(self):
        
        comp = component("test_component", "Arm")
        
        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")    
        self.assertEqual(comp.AT_data, [0,0,0])
        self.assertEqual(comp.AT_relative, "ABSOLUTE")
        self.assertEqual(comp.ROTATED_data, [0,0,0])
        self.assertEqual(comp.ROTATED_relative, "ABSOLUTE")
        self.assertEqual(comp.WHEN, "")
        self.assertEqual(comp.EXTEND, "")
        self.assertEqual(comp.GROUP, "")
        self.assertEqual(comp.JUMP, "")
        self.assertEqual(comp.comment, "")
        
    def test_component_init_complex_call(self):
        
        comp = setup_component_all_keywords()
        
        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")    
        self.assertEqual(comp.AT_data, [0.124, 183.9, 157])
        self.assertEqual(comp.AT_relative, "RELATIVE home")
        self.assertEqual(comp.ROTATED_data, [482, 1240.2, 0.185])
        self.assertEqual(comp.ROTATED_relative, "RELATIVE etc")
        self.assertEqual(comp.WHEN, "WHEN (1==2)\n")
        self.assertEqual(comp.EXTEND, "nscat = 8;\n")
        self.assertEqual(comp.GROUP, "developers")
        self.assertEqual(comp.JUMP, "myself 37")
        self.assertEqual(comp.comment, "test comment")

    def test_component_init_complex_call_relative(self):
        
        comp = setup_component_relative()

        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")    
        self.assertEqual(comp.AT_data, [0.124, 183.9, 157])
        self.assertEqual(comp.AT_relative, "RELATIVE source")
        self.assertEqual(comp.ROTATED_data, [482, 1240.2, 0.185])
        self.assertEqual(comp.ROTATED_relative, "RELATIVE source")
        self.assertEqual(comp.WHEN, "WHEN (1==2)\n")
        self.assertEqual(comp.EXTEND, "nscat = 8;\n")
        self.assertEqual(comp.GROUP, "developers")
        self.assertEqual(comp.JUMP, "myself 37")
        self.assertEqual(comp.comment, "test comment")

    def test_component_basic_init_set_AT(self):
        
        comp = component("test_component", "Arm")
        
        comp.set_AT([12.124, 214.0, 2], RELATIVE = "monochromator")
        
        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.AT_data, [12.124, 214.0, 2])
        self.assertEqual(comp.AT_relative, "RELATIVE monochromator")
        
    def test_component_basic_init_set_ROTATED(self):
        
        comp = component("test_component", "Arm")
        
        comp.set_ROTATED([1204.8, 8490.1, 129], RELATIVE = "analyzer")
        
        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.ROTATED_data, [1204.8, 8490.1, 129])
        self.assertEqual(comp.ROTATED_relative, "RELATIVE analyzer")
        
    def test_component_basic_init_set_RELATIVE(self):
        
        comp = component("test_component", "Arm")
        
        comp.set_RELATIVE("sample")
        
        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.AT_relative, "RELATIVE sample")
        self.assertEqual(comp.ROTATED_relative, "RELATIVE sample")
        
    def test_component_basic_init_set_parameters(self):
        
        comp = component("test_component", "Arm")
        
        # Need to add some parameters to this bare component
        # Parameters are usually added by McStas_Instr 
        comp._unfreeze()
        comp.new_par1 = 1
        comp.new_par2 = 3
        comp.this_par = 1492.2
        
        comp.set_parameters({"new_par1" : 37.0,
                             "new_par2" : 12.0,
                             "this_par" : 1}) 
        
        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.new_par1,37.0)
        self.assertEqual(comp.new_par2,12.0)
        self.assertEqual(comp.this_par,1)
        
        with self.assertRaises(NameError):
            comp.set_parameters({"new_par3" : 37.0})
        
    def test_component_basic_init_set_WHEN(self):
        
        comp = component("test_component", "Arm")
        
        comp.set_WHEN("1 != 2")
        
        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.WHEN, "WHEN (1 != 2)\n")
        
    def test_component_basic_init_set_GROUP(self):
        
        comp = component("test_component", "Arm")
        
        comp.set_GROUP("test group")
        
        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.GROUP, "test group")
        
    def test_component_basic_init_set_JUMP(self):
        
        comp = component("test_component", "Arm")
        
        comp.set_JUMP("test jump")
        
        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.JUMP, "test jump")
        
    def test_component_basic_init_set_EXTEND(self):
        
        comp = component("test_component", "Arm")
        
        comp.append_EXTEND("test code")
        
        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.EXTEND, "test code\n")
        
        comp.append_EXTEND("new code")
        
        self.assertEqual(comp.EXTEND, "test code\nnew code\n")
        
    def test_component_basic_init_set_comment(self):
        
        comp = component("test_component", "Arm")
        
        comp.set_comment("test comment")
        
        self.assertEqual(comp.name, "test_component")
        self.assertEqual(comp.component_name, "Arm")
        self.assertEqual(comp.comment, "test comment")

    def test_component_basic_new_attribute_error(self):
        """
        The component class is frozen after initialize in order to
        prevent the user accidentilly misspelling an attribute name,
        or at least be able to report an error when they do so.
        """
        
        comp = component("test_component", "Arm")
        with self.assertRaises(AttributeError):
            comp.new_attribute = 1
        
        # If unfreeze does not work, this would cause an error
        comp._unfreeze()
        comp.new_attribute = 1
        
        
    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable = unittest.mock.mock_open)    
    def test_component_write_to_file_simple(self, mock_f):
        """
        Testing that a component can be written to file with the
        expected output. Here with simple input.
        """

        comp = component("test_component", "Arm")

        comp._unfreeze()
        # need to set up attribute parameters
        # also need to categorize them as when created
        comp.parameter_names = []
        comp.parameter_defaults = {}
        comp.parameter_types = {}
        comp._freeze()

        with mock_f('test.txt', 'w') as m_fo:
            comp.write_component(m_fo)

        my_call = unittest.mock.call
        expected_writes = [my_call("COMPONENT test_component = Arm("),
                           my_call(")\n"),
                           my_call("AT (0,0,0)"),
                           my_call(" ABSOLUTE\n"),
                           my_call("ROTATED (0,0,0)"),
                           my_call(" ABSOLUTE\n")]

        mock_f.assert_called_with('test.txt', 'w')                                   
        handle = mock_f()
        handle.write.assert_has_calls(expected_writes, any_order=False)

    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable = unittest.mock.mock_open)    
    def test_component_write_to_file_complex(self, mock_f):
        """
        Testing that a component can be written to file with the
        expected output. Here with complex input.
        """
        
        comp = setup_component_all_keywords()
        
        comp._unfreeze()
        # need to set up attribute parameters
        comp.new_par1 = 1.5
        comp.new_par2 = 3
        comp.this_par = "test_val"
        comp.that_par = "\"txt_string\""
        # also need to categorize them as when created
        comp.parameter_names = ["new_par1", "new_par2", "this_par", "that_par"]
        comp.parameter_defaults = {"new_par1" : 5.1,
                                   "new_par2" : 9,
                                   "this_par" : "conga",
                                   "that_par" : "\"txt\""}
        comp.parameter_types = {"new_par1" : "double",
                                "new_par2" : "int",
                                "this_par" : "",
                                "that_par" : "string"}
        comp._freeze()
        
        with mock_f('test.txt', 'w') as m_fo:
            comp.write_component(m_fo)
        
        my_call = unittest.mock.call
        expected_writes = [my_call("COMPONENT test_component = Arm("),
                           my_call("\n"),
                           my_call(" new_par1 = 1.5"),
                           my_call(","),
                           my_call(" new_par2 = 3"),
                           my_call(","),
                           my_call("\n"),
                           my_call(" this_par = test_val"),
                           my_call(","),
                           my_call(" that_par = \"txt_string\""),
                           my_call(")\n"),
                           my_call("WHEN (1==2)\n"),
                           my_call("AT (0.124,183.9,157)"),
                           my_call(" RELATIVE home\n"),
                           my_call("ROTATED (482,1240.2,0.185)"),
                           my_call(" RELATIVE etc\n"),
                           my_call("GROUP developers\n"),
                           my_call("EXTEND %{\n"),
                           my_call("nscat = 8;\n"),
                           my_call("%}\n"),
                           my_call("JUMP myself 37\n"),
                           my_call("\n")]

        mock_f.assert_called_with('test.txt', 'w')                                   
        handle = mock_f()
        handle.write.assert_has_calls(expected_writes, any_order=False)  
    
    @unittest.mock.patch('__main__.__builtins__.open',
                         new_callable = unittest.mock.mock_open)
    def test_component_write_component_required_parameter_error(self, mock_f):
        """
        Test an error occurs if the component is asked to write to disk
        without a required parameter.
        """
        
        comp = setup_component_all_keywords()
        
        comp._unfreeze()
        # need to set up attribute parameters
        comp.new_par1 = None
        # also need to categorize them as when created
        comp.parameter_names = ["new_par1"]
        comp.parameter_defaults = {"new_par1" : None}
        
        with self.assertRaises(NameError):
            with mock_f('test.txt', 'w') as m_fo:
                comp.write_component(m_fo)
                
                
    # Print long (very similar to write component)
    # Print short (easier)
    # show_parameters (similar to write component, with formatting)
    # show_parameters_simple (similar to write component, without formatting)
    
    
    
    

if __name__ == '__main__':
    unittest.main()