from libpyvinyl.BaseFormat import BaseFormat
from mcstasscript.helper.managed_mcrun import load_results


class McStasFormat(BaseFormat):
    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def format_register(self):
        key = "sim"
        desciption = "sim format for McStasData"
        file_extension = ".sim"
        read_kwargs = [""]
        write_kwargs = [""]
        return self._create_format_register(
            key, desciption, file_extension, read_kwargs, write_kwargs
        )

    @staticmethod
    def direct_convert_formats():
        # Assume the format can be converted directly to the formats supported by these classes:
        # AFormat, BFormat
        # Redefine this `direct_convert_formats` for a concrete format class
        return []

    @classmethod
    def read(cls, filename: str) -> dict:
        """Read the data from the file with the `filename` to a dictionary. The dictionary will
        be used by its corresponding data class."""

        data = load_results(filename)
        data_dict = {"data": data}
        return data_dict

    @classmethod
    def write(cls, object, filename: str, key: str = None):
        """Don't have a way to write McStasData"""
        pass

    """
    #def write(cls, object: NumberData, filename: str, key: str = None):
        #Save the data with the `filename`.
        data_dict = object.get_data()
        arr = np.array([data_dict["number"]])
        np.savetxt(filename, arr, fmt="%.3f")
        if key is None:
            original_key = object.key
            key = original_key + "_to_TXTFormat"
        return object.from_file(filename, cls, key)
    """
