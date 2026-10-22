import os
import unittest
import unittest.mock
import copy

from mcstasscript.instrument_diagram.arrow import Arrow
from mcstasscript.instrument_diagram.box import ComponentBox
from mcstasscript.instrument_diagram.connections import IndexConnection
from mcstasscript.instrument_diagram.connections import Lane
from mcstasscript.instrument_diagram.connections import ConnectionList
from mcstasscript.instrument_diagram.canvas import DiagramCanvas
from mcstasscript.tests.helpers_for_tests import WorkInTestDir
from mcstasscript.interface.instr import McStas_instr


def setup_instr_no_path():
    """
    Sets up a neutron instrument without a package_path
    """

    with WorkInTestDir() as handler:
        instrument = McStas_instr("test_instrument")

    return instrument

def setup_populated_instr():
    """
    Sets up a neutron instrument with some features used and three components
    """
    instr = setup_instr_no_path()

    instr.add_parameter("double", "theta")
    instr.add_parameter("double", "has_default", value=37)
    instr.add_declare_var("double", "two_theta")
    instr.append_initialize("two_theta = 2.0*theta;")

    A = instr.add_component("first_component", "test_for_reading")
    B = instr.add_component("second_component", "test_for_reading")
    C = instr.add_component("third_component", "test_for_reading")
    D = instr.add_component("fourth_component", "test_for_reading")

    B.set_AT(0, RELATIVE=A)
    C.set_AT(0, RELATIVE=A)
    D.set_AT(0, RELATIVE=B)

    return instr

def setup_boxes():

    instr = setup_populated_instr()

    comp1 = instr.get_component("first_component")
    comp2 = instr.get_component("third_component")

    return ComponentBox(comp1), ComponentBox(comp2)


class TestInstrumentDiagram(unittest.TestCase):
    """
    Instrument diagram is not critical for operation, tests just to ensure it runs
    """

    def test_Box_initialize_name(self):
        """
        Check that a box can be initialized with a string
        """
        name = "ABSOLUTE"
        box = ComponentBox(name)

        self.assertEqual(box.name, name)

    def test_Box_initialize_comp(self):
        """
        Check that a box can be initialized with a component object
        """
        instr = setup_populated_instr()
        comp = instr.get_last_component()

        box = ComponentBox(comp)

        self.assertEqual(box.name, "fourth_component")

    def test_Arrow_initialize(self):
        """
        Check that an arrow can be initialized with two Box instances
        """

        box1, box2 = setup_boxes()

        arrow = Arrow(origin=box1, target=box2, kind="KIND")

        self.assertEqual(arrow.origin, box1)
        self.assertEqual(arrow.target, box2)
        self.assertEqual(arrow.kind, "KIND")

        string_box = ComponentBox("string")
        arrow = Arrow(origin=box1, target=string_box, kind="KIND_2")

        self.assertEqual(arrow.origin, box1)
        self.assertEqual(arrow.target, string_box)
        self.assertEqual(arrow.kind, "KIND_2")

    def test_IndexConnection(self):
        """
        Ensure IndexConnections find overlap
        """

        A = IndexConnection(2, 8)
        B = IndexConnection(9, 10)
        C = IndexConnection(5, 7)

        self.assertTrue(A.compatible_with(B))
        self.assertTrue(B.compatible_with(C))
        self.assertFalse(A.compatible_with(C))

    def test_Lane(self):
        """
        Ensure a lane reports when a connection can be added and saves allowed
        """

        lane = Lane()

        self.assertTrue(lane.add_connection(2, 8))
        self.assertTrue(lane.add_connection(9, 12))
        self.assertTrue(lane.add_connection(7, 8))  # Same destination allowed
        self.assertFalse(lane.add_connection(3, 9))

        # ensure only allowed connections added
        self.assertEqual(len(lane.connections), 3)

    def test_connection(self):
        """
        Ensure connection lists can return included connections and set lanes
        """
        c_list = ConnectionList()

        box_list = []
        name_list = []
        for index in range(0,10):
            name = "box_" + str(index)
            name_list.append(name)
            box_list.append(ComponentBox(name))

        # Add some connections to list
        c_list.add(box_list[0], box_list[5])  # Lane 1 # Connection 0
        c_list.add(box_list[6], box_list[8])  # Lane 1 # Connection 1
        c_list.add(box_list[1], box_list[7])  # Lane 2 # Connection 2
        c_list.add(box_list[3], box_list[6])  # Lane 3 # Connection 3
        c_list.add(box_list[0], box_list[8])  # Lane 4 # Connection 4

        targets_for_0 = c_list.get_targets_for_origin(box_list[0])
        self.assertEqual(targets_for_0, [box_list[5], box_list[8]])

        c_list.distribute_lane_numbers(name_list)

        connections = c_list.get_connections()
        self.assertEqual(connections[0].lane_number, 1)
        self.assertEqual(connections[1].lane_number, 1)
        self.assertEqual(connections[2].lane_number, 2)
        self.assertEqual(connections[3].lane_number, 3)
        self.assertEqual(connections[4].lane_number, 4)

    def test_DiagramCanvas_initialize(self):
        """
        Ensure the DiagramCanvas can be initialized
        """
        string_box_0 = ComponentBox("string_0")
        string_box_1 = ComponentBox("string_1")
        string_box_2 = ComponentBox("string_2")
        arrow_0 = Arrow(origin=string_box_1, target=string_box_0)
        arrow_1 = Arrow(origin=string_box_2, target=string_box_0)
        arrow_0.set_lane(1)
        arrow_1.set_lane(1)

        left_side_arrows = [arrow_0, arrow_1]

        boxes = [string_box_0, string_box_1, string_box_2]

        arrow_0 = Arrow(origin=string_box_0, target=string_box_1)
        arrow_1 = Arrow(origin=string_box_1, target=string_box_0, kind="JUMP")
        arrow_2 = Arrow(origin=string_box_0, target=string_box_2, kind="Union")
        arrow_0.set_lane(1)
        arrow_1.set_lane(1)
        arrow_2.set_lane(2)
        right_side_arrows = [arrow_0, arrow_1, arrow_2]

        # Get component_categories
        with WorkInTestDir() as handler:
            instrument = McStas_instr("test_instrument")

        component_reader = instrument.component_reader
        component_categories = copy.deepcopy(component_reader.component_category)

        color_choices = {"AT": "blue", "ROTATED": "red", "JUMP": "black", "GROUP": [0.4, 0.4, 0.4], "Union": "green"}

        canvas = DiagramCanvas(left_side_arrows=left_side_arrows, component_boxes=boxes,
                               right_side_arrows=right_side_arrows,
                               component_categories=component_categories,
                               colors=color_choices)

