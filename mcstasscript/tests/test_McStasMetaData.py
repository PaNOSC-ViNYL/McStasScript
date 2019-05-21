import unittest

from mcstasscript.data.data import McStasMetaData


class TestMcStasMetaData(unittest.TestCase):
    """
    Various test of McStasMetaData class
    """

    def test_McStasMetaData_return_type(self):
        """
        Test that newly created McStasMetaData has correct type
        """
        meta_data = McStasMetaData()
        self.assertIsInstance(meta_data, McStasMetaData)

    def test_McStasMetaData_init(self):
        """
        Test that newly created McStasMetaData has no content
        """
        meta_data = McStasMetaData()
        self.assertEqual(len(meta_data.info), 0)

    def test_McStasMetaData_add_info_len(self):
        """
        Test that info can be added to McStasMetaData
        """
        meta_data = McStasMetaData()
        meta_data.add_info("test", 3)
        self.assertEqual(len(meta_data.info), 1)

    def test_McStasMetaData_add_info(self):
        """
        Test that info can be read from McStasMetaData
        """
        meta_data = McStasMetaData()
        meta_data.add_info("test", 3)
        self.assertEqual(meta_data.info["test"], 3)

    def test_McStasMetaData_add_info_title(self):
        """
        Test that title can be set
        """
        meta_data = McStasMetaData()
        meta_data.set_title("title_test")
        self.assertEqual(meta_data.title, "title_test")

    def test_McStasMetaData_add_info_xlabel(self):
        """
        Test that xlabel can be set
        """
        meta_data = McStasMetaData()
        meta_data.set_xlabel("xlabel test")
        self.assertEqual(meta_data.xlabel, "xlabel test")

    def test_McStasMetaData_add_info_ylabel(self):
        """
        Test that ylabel can be set
        """
        meta_data = McStasMetaData()
        meta_data.set_ylabel("ylabel test")
        self.assertEqual(meta_data.ylabel, "ylabel test")

    def test_McStasMetaData_long_read_1d(self):
        """
        Test that extact info can read appropriate info
        """
        meta_data = McStasMetaData()
        meta_data.add_info("type", "array_1d(500)")
        meta_data.add_info("component", "test_A COMP")
        meta_data.add_info("filename", "test_A name")
        meta_data.add_info("xlimits", " 0.92 3.68")
        meta_data.add_info("xlabel", "test A xlabel")
        meta_data.add_info("ylabel", "test A ylabel")
        meta_data.add_info("title", "test A title")

        meta_data.extract_info()  # Converts info to attributes

        self.assertIsInstance(meta_data.dimension, int)
        self.assertEqual(meta_data.dimension, 500)
        self.assertIs(meta_data.component_name, "test_A COMP")
        self.assertIs(meta_data.filename, "test_A name")
        self.assertEqual(len(meta_data.limits), 2)
        self.assertEqual(meta_data.limits[0], 0.92)
        self.assertEqual(meta_data.limits[1], 3.68)
        self.assertIs(meta_data.xlabel, "test A xlabel")
        self.assertIs(meta_data.ylabel, "test A ylabel")
        self.assertIs(meta_data.title, "test A title")

    def test_McStasMetaData_long_read_2d(self):
        """
        Test that extact info can read appropriate info
        """
        meta_data = McStasMetaData()
        meta_data.add_info("type", "array_2d(500, 12)")
        meta_data.add_info("component", "test_A_COMP")
        meta_data.add_info("filename", "test_A_name")
        meta_data.add_info("xlimits", "-2.4 5.99 0.92 3.68")
        meta_data.add_info("xlabel", "test A xlabel")
        meta_data.add_info("ylabel", "test A ylabel")
        meta_data.add_info("title", "test A title")

        meta_data.extract_info()  # Converts info to attributes

        self.assertEqual(len(meta_data.dimension), 2)
        self.assertEqual(meta_data.dimension[0], 500)
        self.assertEqual(meta_data.dimension[1], 12)
        self.assertIs(meta_data.component_name, "test_A_COMP")
        self.assertIs(meta_data.filename, "test_A_name")
        self.assertEqual(len(meta_data.limits), 4)
        self.assertEqual(meta_data.limits[0], -2.4)
        self.assertEqual(meta_data.limits[1], 5.99)
        self.assertEqual(meta_data.limits[2], 0.92)
        self.assertEqual(meta_data.limits[3], 3.68)
        self.assertIs(meta_data.xlabel, "test A xlabel")
        self.assertIs(meta_data.ylabel, "test A ylabel")
        self.assertIs(meta_data.title, "test A title")


if __name__ == '__main__':
    unittest.main()
