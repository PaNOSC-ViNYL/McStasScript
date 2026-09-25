from .simulation_interface import SimInterface
from .plot_interface import PlotInterface

from mcstasscript.interface.instr import McCode_instr
from mcstasscript.data.data import McStasData


def show(function_input):
    """
    Shortcut to showing an interface appropriate for given object

    Can show widget interface for instrument object or list of McStasData
    objects. Needs "%matplotlib widget" in notebook to work correctly.

    Parameters
    ----------

    function_input : McCode_instr, list of McStasData

    """

    if isinstance(function_input, McCode_instr):
        return show_instrunent(function_input)

    elif isinstance(function_input, (list, McStasData)):
        return show_plot(function_input)

    else:
        raise RuntimeError("Show did not recoignize object of type"
                           + str(type(function_input)) + ".")


def show_instrunent(instrument):
    """
    Shows simulation interface for instrument
    """
    simulation_interface = SimInterface(instrument)
    return simulation_interface.show_interface()


def show_plot(data):
    """
    Shows plot interface for given data
    """
    if isinstance(data, list):
        for element in data:
            if not isinstance(element, McStasData):
                raise RuntimeError("Given list contains elements that "
                                   + "are not McStasData objects.")
    else:
        if not isinstance(data, McStasData):
            raise RuntimeError("Given data is not McStasData.")

    plot_interface = PlotInterface(data)
    return plot_interface.show_interface()
