from libpyvinyl.BaseFormat import BaseFormat
from mcstasscript.helper.managed_mcrun import load_results


class MCPLDataFormat(BaseFormat):
    def __init__(self) -> None:
        super().__init__()

    @classmethod
    def format_register(self):
        key = "mcpl"
        desciption = "MCPL file"
        file_extension = ".mcpl"
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
        raise NotImplemented("Read method for MCPL is not implemented nor required")

    @classmethod
    def write(cls, object, filename: str, key: str = None):
        """Don't have a way to write McStasData"""
        raise NotImplemented("Write method for MCPL is not implemented nor required")
