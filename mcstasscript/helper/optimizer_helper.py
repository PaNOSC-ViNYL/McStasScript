"""
example use:
results = ms.optimizer(instrument=instrument, param_names=["z_width","mosaich", "y_height"], lb = [0.01, 10, 0.01], ub = [0.1, 120, 0.1], fom=adv_fom_1, maxiter=15, swarmsize=9, ncount=1E5)
results.plot_2d()
results.plot_3d_scatter()
results.plot_3d_surface()
results.print_history_table()
results.print_optimal_table()
results.xopt
results.fopt
results.histories
"""

import copy
import numpy as np
import mcstasscript as ms
from pyswarm import pso
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from scipy.interpolate import griddata

"""
We define a class OptimizationLogger that 
can be used to log the history of optimization runs. 
It provides methods to wrap an objective function and 
retrieve the history of parameter values and corresponding results.
"""
class OptimizationLogger:
    def __init__(self):
        self.history = []

    def wrap_objective(self, func, **kwargs):
        """
        Wrap the objective function to log parameters and results.
        Pass keyword arguments to wrapped function.

        Parameters:
        - func: The objective function to wrap. It should take a parameters array and return a single value.

        Returns:
        A new function that logs calls to `func`.
        """
        def wrapped_func(params, **kwargs):
            result = func(params, **kwargs)
            self.history.append((copy.copy(params), result))

            return result

        return wrapped_func

    def get_history(self):
        """
        Get the logged history of parameters and results.

        Returns:
        A list of tuples, where each tuple contains (parameters, result).
        """
        return self.history
"""
We define a function starter_fom as a predefined figure of merit taking into account only Intensity
The user is to make a function describing their preferred figure of merit 
"""
def starter_fom(data):
    detector_data = ms.name_search("Detector", data)
    return -detector_data.metadata.total_I

"""
We make a class that will contain all the results that optimizer will return
"""
class Result:
    def __init__(self, xopt, fopt, histories, param_names):
        self.xopt = xopt
        self.fopt = fopt
        self.histories = histories
        self.param_names = param_names

    def plot_2d(self, parameter_names=None):
        # Extract parameters and results from the history
        # history = logger.get_history()
        params, results = zip(*self.histories)
        params = np.array(params)
        results = np.array(results)

        if parameter_names is None:
            optimized_parameters = self.param_names
        else:
            optimized_parameters = parameter_names

        # Assuming you have a list of parameter names
        param_names = {optimized_parameters[i]: params[:, i] for i in range(params.shape[1])}

        # Combine parameters and results into a pandas DataFrame
        df = pd.DataFrame({**param_names, 'Objective Function Result': results})

        # Check the number of parameters
        num_params = params.shape[1]

        if num_params == 2:
            # Create a 2D scatter plot for 2 parameters
            plt.figure(figsize=(10, 6))
            scatter = plt.scatter(df[optimized_parameters[0]], df[optimized_parameters[1]],
                                  c=df['Objective Function Result'], cmap='viridis')
            plt.colorbar(scatter, label='Objective Function Result')
            plt.xlabel(optimized_parameters[0])
            plt.ylabel(optimized_parameters[1])
            plt.title('Scatter Plot: Parameters vs. Result')
            plt.grid(True)
            plt.show()
        elif num_params > 2:
            # Create a pair plot using seaborn for more than 2 parameters
            sns.pairplot(df, hue='Objective Function Result', palette='viridis')
            plt.suptitle('Pair Plot: Parameters vs. Result', y=1.02)
            plt.show()
        else:
            print("Plotting is supported only for 2 or more parameters.")

    def plot_3d_scatter(self, parameter_names=None):

        if parameter_names is None:
            param_names = self.param_names
        else:
            param_names = parameter_names

        num_params = len(param_names)
        params, results = zip(*self.histories)
        params = np.array(params)

        for i in range(num_params - 1):
            for j in range(i + 1, num_params):
                x_vals = np.array([p[i] for p in params])
                y_vals = np.array([p[j] for p in params])
                z_vals = np.array(results)

                xi = np.linspace(x_vals.min(), x_vals.max(), 100)
                yi = np.linspace(y_vals.min(), y_vals.max(), 100)
                xi, yi = np.meshgrid(xi, yi)

                fig = plt.figure(figsize=(12, 8))
                ax = fig.add_subplot(111, projection='3d')

                # Scatter plot
                scatter = ax.scatter(x_vals, y_vals, z_vals, c=z_vals, cmap='viridis', marker='.')

                # Color bar
                color_bar = fig.colorbar(scatter, ax=ax, shrink=0.5, aspect=5)
                color_bar.set_label('Objective Function Result')

                # Labels
                ax.set_xlabel(param_names[i])
                ax.set_ylabel(param_names[j])
                ax.set_zlabel('Objective Function Result')

                plt.title(f'3D Scatter Plot of Optimization History ({param_names[i]}, {param_names[j]})')
                plt.show()


    def plot_3d_surface(self, parameter_names=None):

        if parameter_names is None:
            param_names = self.param_names
        else:
            param_names = parameter_names

        num_params = len(param_names)
        params, results = zip(*self.histories)

        for i in range(num_params - 1):
            for j in range(i + 1, num_params):
                param1_vals = np.array([p[i] for p in params])
                param2_vals = np.array([p[j] for p in params])
                z_vals = np.array(results)

                xi = np.linspace(param1_vals.min(), param1_vals.max(), 100)
                yi = np.linspace(param2_vals.min(), param2_vals.max(), 100)
                xi, yi = np.meshgrid(xi, yi)

                zi = griddata((param1_vals, param2_vals), z_vals, (xi, yi), method='linear')

                fig = plt.figure(figsize=(12, 8))
                ax = fig.add_subplot(111, projection='3d')

                # Surface plot
                surf = ax.plot_surface(xi, yi, zi, cmap='viridis', edgecolor='none')
                ax.set_xlabel(param_names[i])
                ax.set_ylabel(param_names[j])
                ax.set_zlabel('Objective Function Result')
                fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
                plt.title(f'3D Surface Plot of Optimization History ({param_names[i]}, {param_names[j]})')
                plt.show()

        """
    prints a table with the first 10 (if not specified differently) rows of combinations-of-parameters 
    that the simulation went through, alongside the objection function value 
    example use:
    ms.print_history_table(histories,["z_width", "mosaich", "y_height"], decimal_places=6,num_rows=9 )
    where histories is returned by the optimizer
    """
    def print_history_table(self, headers=None, decimal_places=6,num_rows=10):
        # Extract values from arrays and round them
        data_values = [(tuple(round(item, decimal_places) for item in arr) + (round(value, decimal_places),)) for arr, value in self.histories[:num_rows]]
        # Determine headers based on the number of columns
        if headers is None:
            headers = [f'Column{i+1}' for i in range(len(data_values[0]) - 1)] + ['Value']
        headers = self.param_names
        headers = headers + ['fom value']
        # Calculate column widths
        column_widths = [max(len(str(item)) for item in column) for column in zip(headers, *data_values)]

        # Add width for the last column (Value)
        column_widths[-1] = max(column_widths[-1], len('Value'))

        # Print headers
        print('┌' + '─'.join('─' * (width + 2) for width in column_widths) + '┐')
        print('│' + '│'.join(f' {header:<{width}} ' for header, width in zip(headers, column_widths)) + '│')
        print('├' + '┼'.join('─' * (width + 2) for width in column_widths) + '┤')

        # Print data
        for row in data_values:
            print('│' + '│'.join(f' {str(item):<{width}} ' for item, width in zip(row, column_widths)) + '│')

        # Print bottom border
        print('└' + '─'.join('─' * (width + 2) for width in column_widths) + '┘')



    """
    prints a table with the optimal combinations of parameters , alongside the objection function value 
    example use:
    ms.print_optimal_table(xopt, fopt,["z_width", "mosaich", "y_height"], decimal_places=6,num_rows=9 )
    where xopt, fopt are returned by the optimizer
    """
    def print_optimal_table(self, headers=None, decimal_places=6):
        # Prepare data for printing
        data_values = [(tuple(round(item, decimal_places) for item in self.xopt) + (round(self.fopt, decimal_places),))]
        # Determine headers based on the number of columns
        if headers is None:
            headers = [f'Column{i+1}' for i in range(len(data_values[0]) - 1)] + ['Value']
        headers = self.param_names
        headers = headers + ['fom value']

        # Calculate column widths
        column_widths = [max(len(str(item)) for item in column) for column in zip(headers, *data_values)]

        # Add width for the last column (Value)
        column_widths[-1] = max(column_widths[-1], len('Value'))

        # Print over header
        print('Optimal:')
        print()

        # Print headers
        print('┌' + '─'.join('─' * (width + 2) for width in column_widths) + '┐')
        print('│' + '│'.join(f' {header:<{width}} ' for header, width in zip(headers, column_widths)) + '│')
        print('├' + '┼'.join('─' * (width + 2) for width in column_widths) + '┤')

        # Print data
        for row in data_values:
            print('│' + '│'.join(f' {str(item):<{width}} ' for item, width in zip(row, column_widths)) + '│')

        # Print bottom border
        print('└' + '─'.join('─' * (width + 2) for width in column_widths) + '┘')



def optimizer(instrument, param_names, lb, ub, fom=starter_fom, maxiter=25, swarmsize=15, ncount=1E5 ):

    # Create an instance of the logger and wrap the objective function
    logger = OptimizationLogger()

    # Make the optimizer function wrapped in the logger
    logged_sim = logger.wrap_objective(simulate)

    # Set some instrument settings
    instrument.write_full_instrument()
    instrument.settings(ncount=ncount, mpi = 8, force_compile=False, suppress_output=True)

    # Make a dict with the keyward arguments needed by the optimized function
    kwargs_input = dict(par_names=param_names, instrument=instrument, fom=fom)

    # The PSO optimization is performed and the optimal parameters (xopt) and the objective function value (fopt) are printed
    xopt, fopt = pso(logged_sim, lb, ub, swarmsize=swarmsize, maxiter=maxiter, kwargs=kwargs_input)
    print("xopt:",xopt, "fopt:",fopt)
    for i in range(len(xopt)):
        instrument.set_parameters({param_names[i]: xopt[i]})
    data = instrument.backengine()
    ms.make_sub_plot(data)
    histories = logger.get_history()
    print(f"10 first lines of history:")
    for history_line in histories[0:10]:
        print(history_line)

    #print("The user now has the option to depict the correlation the parameters by using any of the, plot_2d(param_names, histories),  plot_3d_scatter(param_names, histories), plot_3d_surface(param_names, histories)")
    return Result(xopt,fopt,histories,param_names)





def simulate(x, par_names=None, instrument=None, fom=starter_fom):
    # Need to ensure parameters are given
    if par_names is None:
        raise ValueError("No parameter names specified.")

    for par, par_value in zip(par_names, x):
        par_dict = {}
        par_dict[par] = par_value

        instrument.set_parameters(par_dict)

    # Run simulation
    data = instrument.backengine()

    # Verbose mode
    #print(x, "\t", data[0])

    # Negative because it is a minimizer
    """
    The negative of the total intensity (if the starter_fom is used) is returned because PSO minimizes the objective function
    """

    # PERHAPS JUST MAKE IT RETURN THE -fom(data) JUST TO MAKE IT EASIER FOR THE USER
    return fom(data)






