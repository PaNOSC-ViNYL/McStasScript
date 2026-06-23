import os
import os.path
import io
import unittest
import unittest.mock

from mcstasscript.interface.instr import McStas_instr
from mcstasscript.tests.helpers_for_tests import WorkInTestDir
from mcstasscript.helper.mcstas_objects import DeclareVariable

run_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '.')

def setup_instr_no_path():
    """
    Sets up a neutron instrument without a package_path
    """

    with WorkInTestDir() as handler:
        instrument = McStas_instr("test_instrument")

    return instrument


class Test_user_vars(unittest.TestCase):
    """
    Tests of user var behavior, collisions tested in test_Instr
    """

    def test_simple_initialize(self):
        """
        Test adding basic flag
        """
        my_instrument = setup_instr_no_path()

        flag = my_instrument.add_user_var("int", "flag")

        self.assertIsInstance(flag, DeclareVariable)
        self.assertEqual(len(my_instrument.user_var_list), 1)
        self.assertIs(my_instrument.user_var_list[0], flag)

    def test_move_user_var_to_declare(self):
        """
        Test ability to move user vars to declare for compatibility
        """
        my_instrument = setup_instr_no_path()

        declare_var1 = my_instrument.add_declare_var("int", "declare_var_1")
        declare_var2 = my_instrument.add_declare_var("double", "declare_var_2", value=4)
        flag = my_instrument.add_user_var("int", "flag")
        another_user = my_instrument.add_user_var("double", "lifetime")

        self.assertEqual(len(my_instrument.declare_list), 2)
        self.assertEqual(len(my_instrument.user_var_list), 2)
        self.assertIs(my_instrument.declare_list[0], declare_var1)
        self.assertIs(my_instrument.declare_list[1], declare_var2)
        self.assertIs(my_instrument.user_var_list[0], flag)
        self.assertIs(my_instrument.user_var_list[1], another_user)

        # Moves all user vars to declare
        my_instrument.move_user_vars_to_declare()

        self.assertEqual(len(my_instrument.declare_list), 4)
        self.assertEqual(len(my_instrument.user_var_list), 0)
        self.assertIs(my_instrument.declare_list[0], declare_var1)
        self.assertIs(my_instrument.declare_list[1], declare_var2)
        self.assertIs(my_instrument.declare_list[2], flag)
        self.assertIs(my_instrument.declare_list[3], another_user)

