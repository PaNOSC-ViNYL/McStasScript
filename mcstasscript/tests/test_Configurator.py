import os
import unittest

from mcstasscript.interface.functions import Configurator

def setup_expected_file(test_name):
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    expected_file = os.path.join(THIS_DIR, "..", test_name + ".yaml")
    
    if os.path.isfile(expected_file):
        os.remove(expected_file)
    return expected_file

def setup_configurator(test_name):
    
    setup_expected_file(test_name)
    
    return Configurator(test_name)
            

class TestConfigurator(unittest.TestCase):
    """
    Tests for configurator class that handles yaml configuration file
    """
    
    def test_simple_initialize(self):
        """
        Tests that initialization happens, new configuration file should be
        written.
        """
        
        test_name = "test_configuration"
        expected_file = setup_expected_file(test_name)
        
        # check the file did not exist before testing
        self.assertFalse(os.path.isfile(expected_file))

        # initialize the configurator
        my_configurator = Configurator(test_name)
        
        # check a new configuration file was made
        self.assertTrue(os.path.isfile(expected_file))
        
        # remove the testing configuration file
        if os.path.isfile(expected_file):
            os.remove(expected_file)
    
    def test_default_config(self):
        """
        This tests confirms the content of the default configuration file
        """

        test_name = "test_configuration"
        expected_file = setup_expected_file(test_name)
        
        # check the file did not exist before testing
        self.assertFalse(os.path.isfile(expected_file))
        
        my_configurator = Configurator(test_name)
        
        default_config = my_configurator._read_yaml()
        
        run = "/Applications/McStas-2.5.app/Contents/Resources/mcstas/2.5/bin/"
        mcstas = "/Applications/McStas-2.5.app/Contents/Resources/mcstas/2.5/"

        self.assertEqual(default_config["paths"]["mcrun_path"], run)
        self.assertEqual(default_config["paths"]["mcstas_path"], mcstas)
        self.assertEqual(default_config["other"]["characters_per_line"], 85)
        
        # remove the testing configuration file
        if os.path.isfile(expected_file): 
            os.remove(expected_file)
    
    def test_yaml_write(self):
        """
        This test checks that writing to the configuration file works
        """
        test_name = "test_configuration"
        my_configurator = setup_configurator(test_name)
        
        config = my_configurator._read_yaml()
        
        config["new_field"] = 123
        config["paths"]["new_path"] = "/test/path/" 
        
        my_configurator._write_yaml(config)
        
        new_config = my_configurator._read_yaml()
        
        self.assertEqual(new_config["other"]["characters_per_line"], 85)
        self.assertEqual(new_config["new_field"], 123)
        self.assertEqual(new_config["paths"]["new_path"], "/test/path/")
        
        # remove the testing configuration file
        setup_expected_file(test_name)
        
    def test_set_mcrun_path(self):
        """
        This test checks that setting the mcrun path works
        """
        test_name = "test_configuration"
        my_configurator = setup_configurator(test_name) 

        my_configurator.set_mcrun_path("/new/mcrun_path/")

        new_config = my_configurator._read_yaml()

        self.assertEqual(new_config["paths"]["mcrun_path"], "/new/mcrun_path/")

        # remove the testing configuration file
        setup_expected_file(test_name)

    def test_set_mcstas_path(self):
        """
        This test checks that setting the mcstas path works
        """
        test_name = "test_configuration"
        my_configurator = setup_configurator(test_name) 

        my_configurator.set_mcstas_path("/new/mcstas_path/")

        new_config = my_configurator._read_yaml()

        self.assertEqual(new_config["paths"]["mcstas_path"],
                         "/new/mcstas_path/")

        # remove the testing configuration file
        setup_expected_file(test_name)

    def test_set_line_length(self):
        """
        This test checks that setting the line length works
        """
        test_name = "test_configuration"
        my_configurator = setup_configurator(test_name) 
        
        my_configurator.set_line_length(123)
        
        new_config = my_configurator._read_yaml()
        
        self.assertEqual(new_config["other"]["characters_per_line"],123)

        # remove the testing configuration file
        setup_expected_file(test_name)


if __name__ == '__main__':
    unittest.main()
