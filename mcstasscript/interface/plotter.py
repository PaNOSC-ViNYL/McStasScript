import math
import copy
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator

from mcstasscript.data.data import McStasData


def _fmt(x, pos):
    """
    Used for nice formatting of powers of 10 when plotting logarithmic
    """
    a, b = '{:.2e}'.format(x).split('e')
    b = int(b)
    if abs(float(a) - 1) < 0.01:
        return r'$10^{{{}}}$'.format(b)
    else:
        return r'${} \times 10^{{{}}}$'.format(a, b)


def _find_min_max_I(data):
    """
    Returns minimum and maximum intensity to plot given dataset

    Uses the plot options embedded in McStasData to determine the proper
    minimum and maximum intensity to display in a plot.

    Have to take cut_min and cut_max into account that can cut parts of
    the intensity away. When plotting logarithmic, orders_of_mags limits
    the orders of magnitude shown.

    Returns tuple of minimum and maximum, when no data is present the
    function returns 0, 0.
    """
    cut_max = data.plot_options.cut_max  # Default 1
    cut_min = data.plot_options.cut_min  # Default 0

    to_plot = data.Intensity

    min_value = to_plot.min()
    max_value = to_plot.max()

    if min_value == 0 and max_value == 0:
        return 0, 0

    if not data.plot_options.log:
        # Linear, simple case
        # Cut top and bottom of data as specified in cut variables
        min_value = min_value + (max_value - min_value) * cut_min
        max_value = max_value * cut_max

    else:
        # Logarithmic, minimum / maximum can not be zero
        max_data_value = to_plot.max()
        max_value = np.log10(max_data_value * cut_max)

        min_value = np.min(to_plot[np.nonzero(to_plot)])
        min_value = min_value + (max_data_value - min_value) * cut_min
        min_value = np.log10(min_value)

        # Take orders_of_mag into account (max / min in log10)
        if max_value - min_value > data.plot_options.orders_of_mag:
            min_value = max_value - data.plot_options.orders_of_mag

        # Convert back from log10
        min_value = 10.0 ** min_value
        max_value = 10.0 ** max_value

    return min_value, max_value


def _plot_fig_ax(data, fig, ax, **kwargs):
    """
    Plots the content of a single McStasData object

    Plotting is controlled through options assosciated with the
    McStasData objects.

    When plotting 2D objects, returns the pcolormesh object
    """

    print("Plotting data with name " + data.metadata.component_name)
    if type(data.metadata.dimension) == int:

        x_axis_mult = data.plot_options.x_limit_multiplier

        x = data.xaxis * x_axis_mult
        y = data.Intensity
        y_err = data.Error

        ax.errorbar(x, y, yerr=y_err)

        if data.plot_options.log:
            ax.set_yscale("log", nonposy='clip')

        ax.set_xlim(data.metadata.limits[0] * x_axis_mult,
                    data.metadata.limits[1] * x_axis_mult)

        # Add a title
        ax.set_title(data.metadata.title)

        # Add axis labels
        ax.set_xlabel(data.metadata.xlabel)
        ax.set_ylabel(data.metadata.ylabel)

        if data.plot_options.custom_xlim_left:
            ax.set_xlim(left=data.plot_options.left_lim)

        if data.plot_options.custom_xlim_right:
            ax.set_xlim(right=data.plot_options.right_lim)

    elif len(data.metadata.dimension) == 2:

        min_value, max_value = _find_min_max_I(data)

        if "fixed_minimum_value" in kwargs:
            min_value = kwargs["fixed_minimum_value"]
        if "fixed_maximum_value" in kwargs:
            max_value = kwargs["fixed_maximum_value"]

        # Set the axis
        x_axis_mult = data.plot_options.x_limit_multiplier
        y_axis_mult = data.plot_options.y_limit_multiplier

        X = np.linspace(data.metadata.limits[0] * x_axis_mult,
                        data.metadata.limits[1] * x_axis_mult,
                        data.metadata.dimension[0] + 1)
        Y = np.linspace(data.metadata.limits[2] * y_axis_mult,
                        data.metadata.limits[3] * y_axis_mult,
                        data.metadata.dimension[1] + 1)

        # Create a meshgrid for both x and y
        x, y = np.meshgrid(X, Y)

        # Generate information on necessary colorrange
        levels = MaxNLocator(nbins=150).tick_values(min_value, max_value)

        # Select colormap
        cmap = copy.copy(plt.get_cmap(data.plot_options.colormap))
        if "no_data_to_black" in kwargs:
            if kwargs["no_data_to_black"]:
                cmap.set_bad((0, 0, 0))

        norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

        # Empty data, return without cmap or norm
        if min_value == 0 and max_value == 0:
            levels = MaxNLocator(nbins=150).tick_values(0.001, 1.0)
            norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)
            im = ax.pcolormesh(x, y, data.Intensity, cmap=cmap, norm=norm)

        # Plot the data on the meshgrids
        elif data.plot_options.log:
            color_norm = matplotlib.colors.LogNorm(vmin=min_value,
                                                   vmax=max_value)
            im = ax.pcolormesh(x, y, data.Intensity,
                               cmap=cmap, norm=color_norm)
        else:
            im = ax.pcolormesh(x, y, data.Intensity, cmap=cmap, norm=norm)

        # Add the colorbar
        if data.plot_options.show_colorbar:
            cax = None
            if "colorbar_axes" in kwargs:
                cax = kwargs["colorbar_axes"]
                print("colorbar axes set")
            fig.colorbar(im, ax=ax, cax=cax,
                         format=matplotlib.ticker.FuncFormatter(_fmt))
            cax.set_aspect(20)

        # Add a title
        ax.set_title(data.metadata.title)

        # Add axis labels
        ax.set_xlabel(data.metadata.xlabel)
        ax.set_ylabel(data.metadata.ylabel)

        if data.plot_options.custom_ylim_top:
            ax.set_ylim(top=data.plot_options.top_lim)

        if data.plot_options.custom_ylim_bottom:
            ax.set_ylim(bottom=data.plot_options.bottom_lim)

        if data.plot_options.custom_xlim_left:
            ax.set_xlim(left=data.plot_options.left_lim)

        if data.plot_options.custom_xlim_right:
            ax.set_xlim(right=data.plot_options.right_lim)

        return im
    else:
        print("Error, dimension not read correctly")


def _handle_kwargs(data_list, **kwargs):
    """
    Handle kwargs when list of McStasData objects given.

    Returns figsize and data_list

    figsize has a default value, but can be changed with keyword argument
    data_list is turned into a list if it isn't already

    Any kwargs can be given as a list, in that case apply them to given
    to the corresponding index.
    """

    if "fontsize" in kwargs:
        used_fontsize = kwargs["fontsize"]
    else:
        used_fontsize = 11
    plt.rcParams.update({'font.size': used_fontsize})

    if isinstance(data_list, McStasData):
        # Only a single element, put it in a list for easier syntax later
        data_list = [data_list]

    known_plotting_kwargs = ["log", "orders_of_mag",
                             "top_lim", "bottom_lim",
                             "left_lim", "right_lim",
                             "cut_min", "cut_max",
                             "colormap", "show_colorbar",
                             "x_axis_multiplier",
                             "y_axis_multiplier"]

    for option in known_plotting_kwargs:
        if option in kwargs:
            given_option = kwargs[option]

            if isinstance(given_option, list):
                if len(data_list) < len(given_option):
                    raise ValueError("Keyword argument " + option + " is "
                                     + "given as a list, but this list has "
                                     + "more elements than there are "
                                     + "data sets to be plotted.")

                index = 0
                for per_list_option in given_option:
                    input_kwarg = {option: per_list_option}
                    data_list[index].set_plot_options(**input_kwarg)
                    index += 1

            else:
                for data in data_list:
                    input_kwarg = {option: given_option}
                    data.set_plot_options(**input_kwarg)

            # Remove option from kwargs
            del kwargs[option]

    if "figsize" in kwargs:
        figsize = kwargs["figsize"]
        if isinstance(figsize, list):
            figsize = (figsize[0], figsize[1])
    else:
        figsize = (13, 7)

    return figsize, data_list


def make_plot(data_list, **kwargs):
    """
    make_plot plots contents of McStasData objects given in list

    Here a new figure is used for each dataset

    Plotting is controlled through options assosciated with the
    McStasData objects.  If a list is given, the plots appear in one
    subplot.
    """

    figsize, data_list = _handle_kwargs(data_list, **kwargs)

    for data in data_list:
        fig, ax0 = plt.subplots(figsize=figsize)
        _plot_fig_ax(data, fig, ax0, **kwargs)

    if "filename" in kwargs:
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

    figsize, data_list = _handle_kwargs(data_list, **kwargs)

    number_of_plots = len(data_list)
    # Find reasonable grid size for the number of plots
    dim2 = math.ceil(math.sqrt(number_of_plots))
    dim1 = math.ceil(number_of_plots / dim2)

    fig, axs = plt.subplots(dim1, dim2, figsize=figsize)
    axs = np.array(axs)
    ax = axs.reshape(-1)

    for data, ax0 in zip(data_list, ax):
        _plot_fig_ax(data, fig, ax0, **kwargs)

    fig.tight_layout()

    if "filename" in kwargs:
        fig.savefig(kwargs["filename"])
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

    figsize, data_list = _handle_kwargs(data_list, **kwargs)

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

    fig, ax0 = plt.subplots(figsize=figsize)
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
