import inspect
from inspect import Signature, Parameter
from typing import Any


class SetParametersCallable:
    """
    Method that can overwrite set_parameters on instr object and provide help

    Help is provided as docstring which is updated whenever add_parameters is
    called, and signature which provide autocompletion in jupyter notebooks.
    """
    def __init__(self, owner):
        self.owner = owner
        self.refresh_docstring()

    def __call__(self, args_as_dict=None, **kwargs: Any) -> None:
        if args_as_dict is not None:
            kwargs.update(args_as_dict)

        allowed = set(self.owner.get_parameter_names())
        unknown = set(kwargs) - allowed
        if unknown:
            raise KeyError(f"Unknown parameters: {sorted(unknown)}")

        if args_as_dict is not None:
            parameter_dict = args_as_dict
        else:
            parameter_dict = kwargs

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
            "Parameters",
            "----------",
            "args_as_dict : dict, optional",
            "    Dictionary mapping parameter names to values.",
        ]

        current_parameters = self.owner.parameters.parameters.values()

        if len(current_parameters) == 0:
            lines.append("")
            lines.append("This instrument current does not have any parameters, "
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
                lines.append(f"    Remember '{'"'}string_input{'"'}' format for literal strings")

        lines.extend([
            "",
            "Examples",
            "--------",
            ">>> instr.set_parameters(parameter_name=2.0)",
            ">>> instr.set_parameters({'parameter_name': 2.0})",
        ])

        return "\n".join(lines)