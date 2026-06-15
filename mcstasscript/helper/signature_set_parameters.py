import inspect
from inspect import Signature, Parameter
from typing import Any


class SetParametersCallableInstrument:
    """
    Class that can overwrite set_parameters on instr object and provide help

    Help is provided as docstring which is updated whenever add_parameters is
    called, and signature which provide autocompletion in jupyter notebooks.
    """
    def __init__(self, owner):
        self.owner = owner
        self.refresh_docstring()

    def __call__(self, args_as_dict=None, **kwargs: Any) -> None:
        """
        This method is called when set_parameters is used on the instrument
        object, updates the parameters accordingly
        """
        parameter_dict = {}
        if args_as_dict is not None:
            parameter_dict = args_as_dict

        # Parameters specified both in arg_as_dict and kwarg use kwarg value
        parameter_dict.update(kwargs)

        allowed = set(self.owner.get_parameter_names())
        unknown = set(parameter_dict) - allowed
        if unknown:
            raise KeyError(f"Unknown parameters: {sorted(unknown)}")

        for key, parameter_value in parameter_dict.items():
            self.owner.parameters[key].value = parameter_value

    @property
    def __signature__(self):
        params = [
            Parameter(
                "args_as_dict",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                default=None,
            )
        ]

        for name in self.owner.get_parameter_names():
            params.append(
                Parameter(
                    name,
                    kind=Parameter.KEYWORD_ONLY,
                    default=None,
                )
            )

        return Signature(params, return_annotation=None)

    def refresh_docstring(self):
        self.__doc__ = self._make_docstring()

    def _make_docstring(self):
        lines = [
            "Set instrument parameters.",
            "",
            "Parameters can be supplied either as keyword arguments or as a dictionary.",
            "",
            "The .show_parameters method shows all available parameters",
            "",
            "Parameters",
            "----------",
            "args_as_dict : dict, optional",
            "    Dictionary mapping parameter names to values.",
        ]

        current_parameters = self.owner.parameters.parameters.values()

        if len(current_parameters) == 0:
            lines.append("")
            lines.append("This instrument currently does not have any parameters, "
                         "can be added with add_parameter method")

        for parameter in current_parameters:
            name = parameter.name
            type_name = getattr(parameter, "type", "double")
            description = getattr(parameter, "comment", "")
            if type_name == "":
                type_name = "float"

            lines.append(f"{name} : {type_name}, optional")

            if description:
                lines.append(f"    {description}")
            else:
                lines.append("    Instrument parameter.")

            if type_name == "string":
                lines.append(f"    Remember '\"string_input\"' format for literal strings")

        lines.extend([
            "",
            "Examples",
            "--------",
            ">>> instr.set_parameters(parameter_name=2.0)",
            ">>> instr.set_parameters({'parameter_name': 2.0})",
        ])

        return "\n".join(lines)


class SetParametersCallableIComponent:
    """
    Class that can overwrite set_parameters on component object and provide help

    Help is provided as docstring which is updated whenever add_parameters is
    called, and signature which provide autocompletion in jupyter notebooks.
    """
    def __init__(self, owner):
        self.owner = owner
        #self.__doc__ = self._make_docstring()

    def __call__(self, args_as_dict=None, **kwargs: Any) -> None:
        """
        This method is called when set_parameters is used on the instrument
        object, updates the parameters accordingly
        """
        parameter_dict = {}
        if args_as_dict is not None:
            parameter_dict = args_as_dict

        # Parameters specified both in arg_as_dict and kwarg use kwarg value
        parameter_dict.update(kwargs)

        allowed = set(self.owner.get_parameter_names())
        unknown = set(parameter_dict) - allowed
        if unknown:
            raise NameError(f"Unknown parameters: {sorted(unknown)}")

        for key, parameter_value in parameter_dict.items():
            setattr(self.owner, key, parameter_value)

    @property
    def __signature__(self):
        params = [
            Parameter(
                "args_as_dict",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                default=None,
            )
        ]

        for name in self.owner.get_parameter_names():
            params.append(
                Parameter(
                    name,
                    kind=Parameter.KEYWORD_ONLY,
                    default=None,
                )
            )

        return Signature(params, return_annotation=None)

    def refresh_docstring(self):
        self.__doc__ = self._make_docstring()

    def _make_docstring(self):
        lines = [
            "Set component parameters.",
            "",
            "Parameters can be supplied either as keyword arguments or as a dictionary.",
            "",
            "The .show_parameters method shows all available parameters",
            "",
            "Parameters",
            "----------",
            "args_as_dict : dict, optional",
            "    Dictionary mapping parameter names to values.",
        ]

        parameter_names = self.owner.get_parameter_names()

        if len(parameter_names) == 0:
            lines.append("")
            lines.append("This component does not have any parameters")

        for parameter_name in parameter_names:
            type_name = self.owner.parameter_types[parameter_name]

            if parameter_name in self.owner.parameter_comments:
                description = self.owner.parameter_comments[parameter_name]
            else:
                description = ""

            if parameter_name in self.owner.parameter_units:
                unit = f'[{self.owner.parameter_units[parameter_name]}]'
            else:
                unit = ""

            required = False
            if parameter_name in self.owner.parameter_defaults:
                if self.owner.parameter_defaults[parameter_name] is None:
                    required = True
                else:
                    required = False
            else:
                required = True

            if required:
                optional_text = "needs to be set"
            else:
                optional_text = "optional"

            if type_name == "":
                type_name = "float"

            lines.append(f"{parameter_name} : {unit}, {type_name}, {optional_text}")

            if description:
                lines.append(f"    {description}")
            else:
                lines.append("    Component parameter.")

            if type_name == "string":
                lines.append(f"    Remember '\"string_input\"' format for literal strings")

        lines.extend([
            "",
            "Examples",
            "--------",
            ">>> comp.set_parameters(parameter_name=2.0)",
            ">>> comp.set_parameters({'parameter_name': 2.0})",
        ])

        return "\n".join(lines)