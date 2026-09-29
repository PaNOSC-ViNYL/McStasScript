from libpyvinyl.BaseData import BaseData
from mcstasscript.data.McStasDataFormat import McStasFormat
from mcstasscript.data.MCPLDataFormat import MCPLDataFormat


class pyvinylMcStasData(BaseData):
    def __init__(
        self,
        key,
        data_dict=None,
        filename=None,
        file_format_class=None,
        file_format_kwargs=None,
    ):

        expected_data = {}

        ### DataClass developer's job start
        expected_data["data"] = None
        ### DataClass developer's job end

        super().__init__(
            key,
            expected_data,
            data_dict,
            filename,
            file_format_class,
            file_format_kwargs,
        )

    @classmethod
    def supported_formats(self):
        format_dict = {}
        ### DataClass developer's job start
        self._add_ioformat(format_dict, McStasFormat)
        ### DataClass developer's job end
        return format_dict

    @classmethod
    def from_file(cls, filename: str, format_class, key, **kwargs):
        """Create the data class by the file in the `format`."""
        return cls(
            key,
            filename=filename,
            file_format_class=format_class,
            file_format_kwargs=kwargs,
        )

    @classmethod
    def from_dict(cls, data_dict, key):
        """Create the data class by a python dictionary."""
        return cls(key, data_dict=data_dict)


class pyvinylMCPLData(BaseData):
    def __init__(
        self,
        key,
        data_dict=None,
        # the filename can be assigned later.
        # If filename == "" or None it fails the consistency check of BaseData
        filename="none",
        file_format_class=None,
        file_format_kwargs=None,
    ):
        expected_data = {}
        super().__init__(key, expected_data, None, filename, MCPLDataFormat, None)

    def supported_formats(self):
        format_dict = {}
        self._add_ioformat(format_dict, MCPLDataFormat)
        return format_dict

    @classmethod
    def from_file(cls, filename: str, key="mcpl"):
        return cls(key, filename=filename)
