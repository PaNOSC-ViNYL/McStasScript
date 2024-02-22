import copy
import numpy as np
import mcstasscript as ms
from pyswarm import pso
from scipy.signal import chirp, find_peaks, peak_widths
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import griddata
from itertools import combinations

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

def starter_fom(data):
    return -data[0].metadata.total_I


def optimizer(instrument, param_names, lb, ub, fom=starter_fom, maxiter=25, swarmsize=15, ncount=1E5 ):
    # Let the user do this part
    #for i in range(len(param_names)):
    #    param = instrument.add_parameter(f"{param_names[i]}", value=(ub[i] - lb[i]) / 2)
    #    # CHECK ABOVE LINE

    #instrument.show_instrument(format="window")

    #instrument.set_parameters(mosaich=20)
    #instrument.show_parameters()
    #data = instrument.backengine()
    #ms.make_sub_plot(data)  # with initial guess of params

    # Create an instance of the logger and wrap the objective function
    logger = OptimizationLogger()

    # Make the optimizer function wrapped in the logger
    logged_sim = logger.wrap_objective(simulate)

    # Set some instrument settings
    instrument.write_full_instrument()
    instrument.settings(ncount=ncount, force_compile=False, suppress_output=True)

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

    print("The user now has the option to depict the correlation between two parameters by using any of the, plot_2d(param_names, histories),  plot_3d_scatter(param_names, histories), plot_3d_surface(param_names, histories)")
    return xopt,fopt,histories

    # How to give the user xopt

# make empty subplots disappear




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
    The negative of the total intensity is returned because PSO minimizes the objective function
    """
    return fom(data)


def plot_2d(optimized_parameters, history):
    # Extract parameters and results from the history
    #history = logger.get_history()
    params, results = zip(*history)
    params = np.array(params)
    results = np.array(results)

    # Assuming you have a list of parameter names
    param_names = {optimized_parameters[i]: params[:, i] for i in range(params.shape[1])}

    # Combine parameters and results into a pandas DataFrame
    df = pd.DataFrame({**param_names, 'Objective Function Result': results})

    # Check the number of parameters
    num_params = params.shape[1]

    if num_params == 2:
        # Create a 2D scatter plot for 2 parameters
        plt.figure(figsize=(10, 6))
        scatter = plt.scatter(df[optimized_parameters[0]], df[optimized_parameters[1]], c=df['Objective Function Result'], cmap='viridis')
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


def plot_3d_scatter(param_names, history):
    num_params = len(param_names)
    params, results = zip(*history)
    params = np.array(params)
    fig, axes = plt.subplots(nrows=num_params-1, ncols=num_params-1, figsize=(5 * (num_params-1), 5 * (num_params-1)))
    plt.show()
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


def plot_3d_surface(param_names, history):
    num_params = len(param_names)
    params, results = zip(*history)

    fig, axes = plt.subplots(nrows=num_params-1, ncols=num_params-1, figsize=(5 * (num_params-1), 5 * (num_params-1)))
    plt.show()
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



