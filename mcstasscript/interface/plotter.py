import math
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator
from openpyxl.worksheet import dimensions
from boto.ec2.autoscale import limits

from mcstasscript.data.data import McStasMetaData
from mcstasscript.data.data import McStasPlotOptions
from mcstasscript.data.data import McStasData

class make_plot:
    """
    make_plot plots contents of McStasData objects

    Plotting is controlled through options assosciated with the
    McStasData objects.

    If a list is given, the plots appear individually.
    """

    def __init__(self, data_list):
        """
        plots McStasData, single object or list of McStasData

        The options concerning plotting are stored with the data

        Parameters
        ----------
        data_list : McStasData or list of McStasData
            McStasData to be plotted
        """

        # Relevant options:
        #  select colormap
        #  show / hide colorbar
        #  custom title / label
        #  color of 1d plot
        #  overlay several 1d
        #  log scale (orders of magnitude)
        #  compare several 1d
        #  compare 2D

        if isinstance(data_list, McStasData):
            # Only a single element, put it in a list for easier syntax later
            data_list = [data_list]

        number_of_plots = len(data_list)

        print("number of elements in data list = " + str(len(data_list)))

        index = -1
        for data in data_list:
            index = index + 1

            print("Plotting data with name " + data.metadata.component_name)
            if type(data.metadata.dimension) == int:
                fig = plt.figure(0)

                # print(data.T)
                x = data.xaxis
                y = data.Intensity
                y_err = data.Error

                plt.errorbar(x, y, yerr=y_err)

                if data.plot_options.log:
                    ax0.set_yscale("log", nonposy='clip')

                plt.xlim(data.metadata.limits[0], data.metadata.limits[1])

                # Add a title
                plt.title(data.metadata.title)

                # Add axis labels
                plt.xlabel(data.metadata.xlabel)
                plt.ylabel(data.metadata.ylabel)

            elif len(data.metadata.dimension) == 2:

                # Split the data into intensity, error and ncount
                Intensity = data.Intensity
                Error = data.Error
                Ncount = data.Ncount

                if data.plot_options.log:
                    min_value = np.min(Intensity[np.nonzero(Intensity)])
                    min_value = np.log10(min_value)

                    to_plot = np.log10(Intensity)

                    max_value = to_plot.max()

                    if (max_value - min_value
                            > data.plot_options.orders_of_mag):
                        min_value = (max_value
                                     - data.plot_options.orders_of_mag)
                else:
                    to_plot = Intensity
                    min_value = to_plot.min()
                    max_value = to_plot.max()

                # Check the size of the array to be plotted
                # print(to_plot.shape)

                # Set the axis (might be switched?)
                X = np.linspace(data.metadata.limits[0],
                                data.metadata.limits[1],
                                data.metadata.dimension[0]+1)
                Y = np.linspace(data.metadata.limits[2],
                                data.metadata.limits[3],
                                data.metadata.dimension[1])

                # Create a meshgrid for both x and y
                y, x = np.meshgrid(Y, X)

                # Generate information on necessary colorrange
                levels = MaxNLocator(nbins=150).tick_values(min_value,
                                                            max_value)

                # Select colormap
                cmap = plt.get_cmap('hot')
                norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

                # Create the figure
                fig, (ax0) = plt.subplots()

                # Plot the data on the meshgrids
                if data.plot_options.log:
                    color_norm = matplotlib.colors.LogNorm(vmin=min_value,
                                                           vmax=max_value)
                    im = ax0.pcolormesh(x, y, to_plot,
                                        cmap=cmap, norm=color_norm)
                else:
                    im = ax0.pcolormesh(x, y, to_plot, cmap=cmap, norm=norm)

                # Add the colorbar
                fig.colorbar(im, ax=ax0)

                # Add a title
                ax0.set_title(data.metadata.title)

                # Add axis labels
                plt.xlabel(data.metadata.xlabel)
                plt.ylabel(data.metadata.ylabel)

            else:
                print("Error, dimension not read correctly")

        plt.show()


class make_sub_plot:
    """
    make_plot plots contents of McStasData objects

    Plotting is controlled through options assosciated with the
    McStasData objects.  If a list is given, the plots appear in one
    subplot.
    """

    def __init__(self, data_list):
        """
        plots McStasData, single object or list of McStasData

        The options concerning plotting are stored with the data

        Parameters
        ----------
        data_list : McStasData or list of McStasData
            McStasData to be plotted
        """
        if not isinstance(data_list, McStasData):
            print("number of elements in data list = "
                  + str(len(data_list)))
        else:
            # Make list from single element to simplify syntax
            data_list = [data_list]

        number_of_plots = len(data_list)

        # Relevant options:
        #  select colormap
        #  show / hide colorbar
        #  custom title / label
        #  color of 1d plot
        #  overlay several 1d
        #  log scale (o$rders of magnitude)
        #  compare several 1d
        #  compare 2D

        # Find reasonable grid size for the number of plots
        dim2 = math.ceil(math.sqrt(number_of_plots))
        dim1 = math.ceil(number_of_plots/dim2)

        fig, axs = plt.subplots(dim1, dim2, figsize=(13, 7))
        axs = np.array(axs)
        ax = axs.reshape(-1)

        index = -1
        for data in data_list:
            index = index + 1
            ax0 = ax[index]

            print("Plotting data with name "
                  + data.metadata.component_name)

            if isinstance(data.metadata.dimension, int):
                # fig = plt.figure(0)
                # plt.subplot(dim1, dim2, n_plot)
                x = data.xaxis
                y = data.Intensity
                y_err = data.Error

                ax0.errorbar(x, y, yerr=y_err)

                if data.plot_options.log:
                    ax0.set_yscale("log", nonposy='clip')

                ax0.set_xlim(data.metadata.limits[0],
                             data.metadata.limits[1])

                # Add a title
                # ax0.title(data.title)

                # Add axis labels
                ax0.set_xlabel(data.metadata.xlabel)
                ax0.set_ylabel(data.metadata.ylabel)

            elif len(data.metadata.dimension) == 2:

                # Split the data into intensity, error and ncount
                Intensity = data.Intensity
                Error = data.Error
                Ncount = data.Ncount

                if data.plot_options.log:
                    min_value = np.min(Intensity[np.nonzero(Intensity)])
                    min_value = np.log10(min_value)

                    to_plot = Intensity

                    max_value = np.log10(to_plot.max())

                    if (max_value - min_value
                            > data.plot_options.orders_of_mag):
                        min_value = (max_value
                                     - data.plot_options.orders_of_mag)
                    min_value = 10.0 ** min_value
                    max_value = 10.0 ** max_value
                else:
                    to_plot = Intensity
                    min_value = to_plot.min()
                    max_value = to_plot.max()

                # Check the size of the array to be plotted
                # print(to_plot.shape)

                # Set the axis (might be switched?)
                X = np.linspace(data.metadata.limits[0],
                                data.metadata.limits[1],
                                data.metadata.dimension[0]+1)
                Y = np.linspace(data.metadata.limits[2],
                                data.metadata.limits[3],
                                data.metadata.dimension[1])

                # Create a meshgrid for both x and y
                y, x = np.meshgrid(Y, X)

                # Generate information on necessary colorrange
                levels = MaxNLocator(nbins=150).tick_values(min_value,
                                                            max_value)

                # Select colormap
                cmap = plt.get_cmap(data.plot_options.colormap)

                # Select the colorscale normalization
                if data.plot_options.log:
                    norm = matplotlib.colors.LogNorm(vmin=min_value,
                                                     vmax=max_value)
                else:
                    norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)

                # Create plot
                im = ax0.pcolormesh(x, y, to_plot, cmap=cmap, norm=norm)

                def fmt(x, pos):
                    a, b = '{:.2e}'.format(x).split('e')
                    b = int(b)
                    return r'${} \times 10^{{{}}}$'.format(a, b)

                # Add the colorbar
                fig.colorbar(im, ax=ax0,
                             format=matplotlib.ticker.FuncFormatter(fmt))

                # Add a title
                ax0.set_title(data.metadata.title)

                # Add axis labels
                ax0.set_xlabel(data.metadata.xlabel)
                ax0.set_ylabel(data.metadata.ylabel)

            else:
                print("Error, dimension not read correctly")

        plt.show()