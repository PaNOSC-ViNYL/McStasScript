import math
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator

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

    def __init__(self, data_list, **kwargs):
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

        if "fontsize" in kwargs:
            plt.rcParams.update({'font.size': kwargs["fontsize"]})

        print("number of elements in data list = " + str(len(data_list)))

        index = -1
        for data in data_list:
            index = index + 1

            print("Plotting data with name " + data.metadata.component_name)
            if type(data.metadata.dimension) == int:
                fig = plt.figure(0)

                x_axis_mult = data.plot_options.x_limit_multiplier
                # print(data.T)
                x = data.xaxis*x_axis_mult
                y = data.Intensity
                y_err = data.Error

                #(fig, ax0) = plt.errorbar(x, y, yerr=y_err)
                plt.errorbar(x, y, yerr=y_err)

                ax0 = plt.gca()

                if data.plot_options.log:
                    ax0.set_yscale("log", nonposy='clip')

                ax0.set_xlim(data.metadata.limits[0]*x_axis_mult,
                             data.metadata.limits[1]*x_axis_mult)

                # Add a title
                plt.title(data.metadata.title)

                # Add axis labels
                plt.xlabel(data.metadata.xlabel)
                plt.ylabel(data.metadata.ylabel)

                if data.plot_options.custom_xlim_left:
                    ax0.set_xlim(left=data.plot_options.left_lim)

                if data.plot_options.custom_xlim_right:
                    ax0.set_xlim(right=data.plot_options.right_lim)

            elif len(data.metadata.dimension) == 2:
                # Split the data into intensity, error and ncount
                Intensity = data.Intensity
                Error = data.Error
                Ncount = data.Ncount

                cut_max = data.plot_options.cut_max  # Default 1
                cut_min = data.plot_options.cut_min  # Default 0

                if data.plot_options.log:
                    to_plot = Intensity

                    max_data_value = to_plot.max()

                    min_value = np.min(Intensity[np.nonzero(Intensity)])
                    min_value = np.log10(min_value
                                         + (max_data_value-min_value)*cut_min)

                    max_value = np.log10(max_data_value*cut_max)

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

                    # Cut top and bottom of data as specified in cut variables
                    min_value = min_value + (max_value-min_value)*cut_min
                    max_value = max_value*cut_max

                # Check the size of the array to be plotted
                # print(to_plot.shape)

                # Set the axis (might be switched?)
                x_axis_mult = data.plot_options.x_limit_multiplier
                y_axis_mult = data.plot_options.y_limit_multiplier

                X = np.linspace(data.metadata.limits[0]*x_axis_mult,
                                data.metadata.limits[1]*x_axis_mult,
                                data.metadata.dimension[0]+1)
                Y = np.linspace(data.metadata.limits[2]*y_axis_mult,
                                data.metadata.limits[3]*y_axis_mult,
                                data.metadata.dimension[1]+1)

                # Create a meshgrid for both x and y
                x, y = np.meshgrid(X, Y)

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
                    im = ax0.pcolormesh(y, x, to_plot,
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

                if data.plot_options.custom_ylim_top:
                    ax0.set_ylim(top=data.plot_options.top_lim)

                if data.plot_options.custom_ylim_bottom:
                    ax0.set_ylim(bottom=data.plot_options.bottom_lim)

                if data.plot_options.custom_xlim_left:
                    ax0.set_xlim(left=data.plot_options.left_lim)

                if data.plot_options.custom_xlim_right:
                    ax0.set_xlim(right=data.plot_options.right_lim)

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

    def __init__(self, data_list, **kwargs):
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

        if "fontsize" in kwargs:
            plt.rcParams.update({'font.size': kwargs["fontsize"]})

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
                x_axis_mult = data.plot_options.x_limit_multiplier

                x = data.xaxis*x_axis_mult
                y = data.Intensity
                y_err = data.Error

                ax0.errorbar(x, y, yerr=y_err)

                if data.plot_options.log:
                    ax0.set_yscale("log", nonposy='clip')

                ax0.set_xlim(data.metadata.limits[0]*x_axis_mult,
                             data.metadata.limits[1]*x_axis_mult)

                # Add a title
                ax0.set_title(data.metadata.title)

                # Add axis labels
                ax0.set_xlabel(data.metadata.xlabel)
                ax0.set_ylabel(data.metadata.ylabel)

                if data.plot_options.custom_xlim_left:
                    ax0.set_xlim(left=data.plot_options.left_lim)

                if data.plot_options.custom_xlim_right:
                    ax0.set_xlim(right=data.plot_options.right_lim)

            elif len(data.metadata.dimension) == 2:

                # Split the data into intensity, error and ncount
                Intensity = data.Intensity
                Error = data.Error
                Ncount = data.Ncount

                cut_max = data.plot_options.cut_max  # Default 1
                cut_min = data.plot_options.cut_min  # Default 0

                if data.plot_options.log:
                    to_plot = Intensity

                    max_data_value = to_plot.max()

                    min_value = np.min(Intensity[np.nonzero(Intensity)])
                    min_value = np.log10(min_value
                                         + (max_data_value-min_value)*cut_min)

                    max_value = np.log10(max_data_value*cut_max)

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

                    # Cut top and bottom of data as specified in cut variables
                    min_value = min_value + (max_value-min_value)*cut_min
                    max_value = max_value*cut_max

                # Check the size of the array to be plotted
                # print(to_plot.shape)

                # Set the axis
                x_axis_mult = data.plot_options.x_limit_multiplier
                y_axis_mult = data.plot_options.y_limit_multiplier

                X = np.linspace(data.metadata.limits[0]*x_axis_mult,
                                data.metadata.limits[1]*x_axis_mult,
                                data.metadata.dimension[0]+1)
                Y = np.linspace(data.metadata.limits[2]*y_axis_mult,
                                data.metadata.limits[3]*y_axis_mult,
                                data.metadata.dimension[1]+1)

                # Create a meshgrid for both x and y
                x, y = np.meshgrid(X, Y)

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
                im = ax0.pcolormesh(y, x, to_plot, cmap=cmap, norm=norm)

                def fmt(x, pos):
                    a, b = '{:.2e}'.format(x).split('e')
                    b = int(b)
                    if abs(float(a) - 1) < 0.01 :
                        return r'$10^{{{}}}$'.format(b)
                    else:
                        return r'${} \times 10^{{{}}}$'.format(a, b)

                # Add the colorbar
                if data.plot_options.colormap:
                    fig.colorbar(im, ax=ax0,
                                 format=matplotlib.ticker.FuncFormatter(fmt))

                # Add a title
                ax0.set_title(data.metadata.title)

                # Add axis labels
                ax0.set_xlabel(data.metadata.xlabel)
                ax0.set_ylabel(data.metadata.ylabel)

                if data.plot_options.custom_ylim_top:
                    ax0.set_ylim(top=data.plot_options.top_lim)

                if data.plot_options.custom_ylim_bottom:
                    ax0.set_ylim(bottom=data.plot_options.bottom_lim)

                if data.plot_options.custom_xlim_left:
                    ax0.set_xlim(left=data.plot_options.left_lim)

                if data.plot_options.custom_xlim_right:
                    ax0.set_xlim(right=data.plot_options.right_lim)

            else:
                print("Error, dimension not read correctly")

        plt.show()


class make_animation:
    """
    make_plot plots contents of McStasData objects

    Plotting is controlled through options assosciated with the
    McStasData objects.  If a list is given, the plots appear in one
    subplot.
    """

    def __init__(self, data_list, **kwargs):
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

        # Relevant options:
        #  select colormap
        #  show / hide colorbar
        #  custom title / label
        #  color of 1d plot
        #  overlay several 1d
        #  log scale (o$rders of magnitude)
        #  compare several 1d
        #  compare 2D

        if "fontsize" in kwargs:
            plt.rcParams.update({'font.size': kwargs["fontsize"]})
            
        if "fps" in kwargs:
            period_in_ms = 1000/kwargs["fps"]
        else:
            period_in_ms = 200

        fig = plt.figure()
        ax = plt.axes()
        #fig, ax = plt.subplot()
        
        # find limits for entire dataset
        maximum_values = []
        minimum_values = []
        
        is_1D = False
        is_2D = False
        
        for data in data_list:
            if isinstance(data.metadata.dimension, int):
                is_1D = True
                
                y = data.Intensity[np.nonzero(data.Intensity)]
                if len(y) > 0:
                    maximum_values.append(y.max())
                    minimum_values.append(y.min())
            
            elif len(data.metadata.dimension) == 2:
                is_2D = True
                
                y = data.Intensity[np.nonzero(data.Intensity)]
                if len(y) > 0:
                    maximum_values.append(y.max())
                    minimum_values.append(y.min())
        
        if len(maximum_values) > 0:
            maximum_value = np.array(maximum_values).max()
        else:
            maximum_value = 0
            
        if len(minimum_values) > 0:
            minimum_value = np.array(minimum_values).min()
        else:
            minimum_value = 0
        
        if is_1D and is_2D:
            raise InputError(
                "Both 1D and 2D data in animation, only one allowed.")

        # initialize plots
        
        data = data_list[0]
        if isinstance(data.metadata.dimension, int):
            x_axis_mult = data.plot_options.x_limit_multiplier
            
            x = data.xaxis*x_axis_mult
            y = data.Intensity
            y_err = data.Error
            
            er = ax.errorbar(x, y, yerr=y_err)
            
            if data.plot_options.log:
                    ax.set_yscale("log", nonposy='clip')

            ax.set_xlim(data.metadata.limits[0]*x_axis_mult,
                             data.metadata.limits[1]*x_axis_mult)

            # Add a title
            ax.set_title(data.metadata.title)

            # Add axis labels
            ax.set_xlabel(data.metadata.xlabel)
            ax.set_ylabel(data.metadata.ylabel)

            if data.plot_options.custom_xlim_left:
                ax.set_xlim(left=data.plot_options.left_lim)

            if data.plot_options.custom_xlim_right:
                ax.set_xlim(right=data.plot_options.right_lim)
                
            ax.set_ylim(minimum_value, maximum_value)
        
        elif len(data.metadata.dimension) == 2:
            # Split the data into intensity, error and ncount
            Intensity = data.Intensity
            Error = data.Error
            Ncount = data.Ncount
            
            cut_max = data.plot_options.cut_max  # Default 1
            cut_min = data.plot_options.cut_min  # Default 0

            if data.plot_options.log:
                
                min_value = minimum_value
                max_value = maximum_value
                
                min_value = np.log10(min_value
                                     + (max_value-min_value)*cut_min)
                
                max_value = np.log10(max_value*cut_max)

                if (max_value - min_value
                        > data.plot_options.orders_of_mag):
                    min_value = (max_value
                                 - data.plot_options.orders_of_mag)
                    
                min_value = 10.0 ** min_value
                max_value = 10.0 ** max_value
            else:
                
                min_value = minimum_value 
                max_value = maximum_value

            # Check the size of the array to be plotted
            # print(to_plot.shape)

            # Set the axis
            x_axis_mult = data.plot_options.x_limit_multiplier
            y_axis_mult = data.plot_options.y_limit_multiplier

            X = np.linspace(data.metadata.limits[0]*x_axis_mult,
                            data.metadata.limits[1]*x_axis_mult,
                            data.metadata.dimension[0]+1)
            Y = np.linspace(data.metadata.limits[2]*y_axis_mult,
                            data.metadata.limits[3]*y_axis_mult,
                            data.metadata.dimension[1]+1)

            # Create a meshgrid for both x and y
            x, y = np.meshgrid(X, Y)

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
            im = ax.pcolormesh(y, x, Intensity,
                               cmap=cmap, norm=norm)

            def fmt(x, pos):
                a, b = '{:.2e}'.format(x).split('e')
                b = int(b)
                if abs(float(a) - 1) < 0.01 :
                    return r'$10^{{{}}}$'.format(b)
                else:
                    return r'${} \times 10^{{{}}}$'.format(a, b)

            # Add the colorbar
            if data.plot_options.colormap:
                fig.colorbar(im, ax=ax,
                             format=matplotlib.ticker.FuncFormatter(fmt))

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

        def init_1D():
            # initialize function for animation
            er.set_data([], [], []) # wont work
            return er,
        
        def animate_1D(index):
            data = data_list[index]
            intensity = data.Intensity
            error = data.Error
            
            er.set_data(x, intensity, error)
            return er,

        def init_2D():
            # initialize function for animation
            im.set_array([])
            return im,
            
        def animate_2D(index):
            data = data_list[index]
            intensity = data.Intensity

            im.set_array(intensity.ravel())
            return im,
        
        anim = animation.FuncAnimation(fig, animate_2D, #init_func=init_2D,
                                       frames=len(data_list),
                                       interval=period_in_ms,
                                       blit=False, repeat=True)

        #plt.draw()
        plt.show()

        # The animation doesn't play unless it is saved. Bug.
        if "filename" in kwargs:
            filename = kwargs["filename"]
            if not filename.endswith(".gif"):
                filename = filename + ".gif"

            # check if imagemagick available?
            print("Saving animation with filename : \"" + filename + "\"")
            anim.save(filename, writer="imagemagick")
