import math

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from mcstasscript.helper.plot_helper import _fmt
from mcstasscript.helper.plot_helper import _find_min_max_I
from mcstasscript.helper.plot_helper import _plot_fig_ax
from mcstasscript.helper.plot_helper import _handle_kwargs


def make_plot(data_list, **kwargs):
    """
    make_plot plots contents of McStasData objects given in list

    Here a new figure is used for each dataset

    Plotting is controlled through options assosciated with the
    McStasData objects.  If a list is given, the plots appear in one
    subplot.
    """

    data_list = _handle_kwargs(data_list, **kwargs)

    if "figsize" in kwargs:
        figsize = kwargs["figsize"]
        if isinstance(figsize, list):
            figsize = (figsize[0], figsize[1])
    else:
        figsize = (13, 7)

    for data in data_list:
        fig, ax0 = plt.subplots(figsize=figsize, tight_layout=True)
        _plot_fig_ax(data, fig, ax0, **kwargs)

    if "filename" in kwargs:
        fig.tight_layout()
        fig.savefig(kwargs["filename"])
    else:
        plt.show()


def make_sub_plot(data_list, **kwargs):
    """
    make_sub_plot plots contents of McStasData objects given in list

    It is fit into one big figure, each data set as a subplot.

    Plotting is controlled through options assosciated with the
    McStasData objects.  If a list is given, the plots appear in one
    subplot.
    """

    data_list = _handle_kwargs(data_list, **kwargs)

    number_of_plots = len(data_list)
    if number_of_plots == 0:
        print("No data to plot")
        return

    # Find reasonable grid size for the number of plots
    special_cases = {
        1: (1, 1),
        4: (2, 2),
    }

    if number_of_plots in special_cases:
        dim1 = special_cases[number_of_plots][0]
        dim2 = special_cases[number_of_plots][0]
    else:
        if number_of_plots < 3:
            dim2 = number_of_plots
            dim1 = 1
        else:
            dim2 = 3
            dim1 = math.ceil(number_of_plots / dim2)

    if "figsize" in kwargs:
        figsize = kwargs["figsize"]
        if isinstance(figsize, list):
            figsize = (figsize[0], figsize[1])
    else:
        # Adjust figure size after number of plots
        figsize = (1 + dim2*4, 0.5 + 3.0*dim1)
        if dim1 == 1 and dim2 == 1:
            # Single plots can be a bit larger
            figsize = (7, 5)

    fig, axs = plt.subplots(dim1, dim2, figsize=figsize, tight_layout=True)
    axs = np.array(axs)
    ax = axs.reshape(-1)

    for data, ax0 in zip(data_list, ax):
        _plot_fig_ax(data, fig, ax0, **kwargs)

    fig.tight_layout()

    if "filename" in kwargs:
        fig.tight_layout()
        fig.savefig(kwargs["filename"])
        plt.close(fig)
    else:
        plt.show()


def make_animation(data_list, **kwargs):
    """
    Creates an animation from list of McStasData objects

    Parameters
    ----------
    data_list : list of McStasData
        List of McStasData objects for animation

    Keyword arguments
    -----------------
        filename : str
            Filename for saving the gif

        fps : float
            Number of frames per second

    """

    data_list = _handle_kwargs(data_list, **kwargs)

    if "figsize" in kwargs:
        figsize = kwargs["figsize"]
        if isinstance(figsize, list):
            figsize = (figsize[0], figsize[1])
    else:
        figsize = (13, 7)

    if "fps" in kwargs:
        period_in_ms = 1000 / kwargs["fps"]
    else:
        period_in_ms = 200

    # find limits for entire dataset
    maximum_values = []
    minimum_values = []

    is_1D = False
    is_2D = False

    for data in data_list:
        if isinstance(data.metadata.dimension, int):
            is_1D = True

        elif len(data.metadata.dimension) == 2:
            is_2D = True

        min_value, max_value = _find_min_max_I(data)

        # When data empty, min and max value is 0, skip
        if not (min_value == 0 and max_value == 0):
            minimum_values.append(min_value)
            maximum_values.append(max_value)

    if is_1D and is_2D:
        raise ValueError(
            "Both 1D and 2D data in animation, only one allowed.")

    if len(minimum_values) == 0:
        raise ValueError(
            "No data found for animation!")

    maximum_value = np.array(maximum_values).max()
    minimum_value = np.array(minimum_values).min()

    if "orders_of_mag" in kwargs:
        orders_of_mag = kwargs["orders_of_mag"]
        mag_diff = np.log10(maximum_value) - np.log10(minimum_value)
        if mag_diff > orders_of_mag:
            minimum_value_log10 = np.log10(maximum_value) - orders_of_mag
            minimum_value = 10**(minimum_value_log10)

    kwargs["fixed_minimum_value"] = minimum_value
    kwargs["fixed_maximum_value"] = maximum_value

    fig, ax0 = plt.subplots(figsize=figsize, tight_layout=True)
    im = _plot_fig_ax(data_list[0], fig, ax0, **kwargs)

    def animate_2D(index):
        data = data_list[index]
        intensity = data.Intensity

        im.set_array(intensity.ravel())
        return im,

    anim = animation.FuncAnimation(fig, animate_2D,
                                   frames=len(data_list),
                                   interval=period_in_ms,
                                   blit=False, repeat=True)

    plt.show()

    # The animation doesn't play unless it is saved. Bug.
    if "filename" in kwargs:
        filename = kwargs["filename"]
        if not filename.endswith(".gif"):
            filename = filename + ".gif"

        # check if imagemagick available?
        print("Saving animation with filename : \"" + filename + "\"")
        anim.save(filename, writer="imagemagick")