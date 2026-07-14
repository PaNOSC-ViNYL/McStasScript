# McStasScript

[McStas](http://www.mcstas.org) API for creating and running McStas/McXtrace instruments from Python scripting.

Prototype for an API that allows interaction with McStas through an interface like Jupyter Notebooks, created under WP5 of PaNOSC.

Full documentation can be found [here](https://mads-bertelsen.github.io)!

## Installation

McStasScript can be installed from conda-forge or pip:

```bash
conda install -c conda-forge mcstasscript
```

```bash
pip install McStasScript --upgrade
```

When McStas is installed via conda-forge, McStasScript is included automatically.

## Configuration

In most cases, no configuration is needed. If the `MCSTAS` environment variable is set (e.g., after running `eval $(mcstas)`), McStasScript will automatically detect the McStas installation. If `mcrun` is available on the PATH, it will be used directly.

For manual configuration or troubleshooting, see the [online documentation](https://mads-bertelsen.github.io).

## Instructions for basic use

This section provides a quick way to get started; a more in-depth tutorial using Jupyter Notebooks is available in the tutorial folder.

Import the package:

```python
import mcstasscript as ms
```

Create a new instrument (use `McXtrace_instr` for McXtrace):

```python
my_instrument = ms.McStas_instr("my_instrument")
```

Add components:

```python
my_source = my_instrument.add_component("source", "Source_simple")
my_source.show_parameters()  # Show available parameters for Source_simple
```

Set parameters as attributes, in jupyter notebooks these are autocompleted if the object has been created:

```python
my_source.set_parameters(xwidth=0.12, yheight=0.12, lambda0=3, dlambda = 2.2, focus_xw = 0.05, focus_yh = 0.05)
```

Add a monitor (notice the use of single and double quotes to set a string literal in the file):

```python
PSD = my_instrument.add_component("PSD", "PSD_monitor", AT=[0,0,1], RELATIVE="source")
PSD.set_parameters(xwidth=0.1, yheight=0.1, nx=5, ny=5, filename='"PSD.dat"')
```

Set simulation options and run:

```python
my_instrument.settings(output_path="first_run", ncount=1E7)
data = my_instrument.backengine()
```

Access and manipulate results:

```python
data[0].Intensity
```

Plot results:

```python
ms.make_sub_plot(data)
```

## Widgets in Jupyter Notebooks

Interactive widget interface for plotting:

```python
import mcstasscript.jb_interface as ms_widget
ms_widget.show(data)
```

Interactive simulation widget (alternative to `backengine`):

```python
ms_widget.show(instr)
```

Programmatic access to widget-generated data:

```python
sim_widget = ms_widget.SimInterface(instr)
sim_widget.show_interface()
data = sim_widget.get_data()
```

## Use existing instrument files

The McStas package now includes the ability to create McStasScript python files from instrument files.
```
mcstas-pygen my_isntrument.instr
```
This can also be done through mcgui using the Pylab button.

## Method overview

### Instrument (`McStas_instr` / `McXtrace_instr`)

```
McStas_instr(name)  # Returns instrument object
├── show_parameters()           # Print instrument parameters
├── show_settings()             # Print current run settings
├── show_variables()            # Print declared and user variables
├── show_components()           # Print components and their positions
├── show_instrument()           # Show instrument in mcdisplay
├── show_diagram()              # Show instrument layout diagram
├── set_parameters(**kwargs)    # Set instrument parameters (dict or kwargs, autocompletes)
├── available_components([category])  # Show available components
├── component_help(name)        # Show parameters for a component type
├── add_component(name, type, **kwargs)  # Add component, returns component object
├── copy_component(name, original, **kwargs)  # Copy a component
├── remove_component(name)       # Remove a component
├── move_component(name, before=None, after=None)  # Move component
├── get_component(name)          # Get component object by name
├── get_last_component()         # Get last added component
├── add_parameter(*args, **kwargs)  # Add instrument parameter
├── add_declare_var(type, name, **kwargs)  # Add declared variable
├── add_user_var(type, name, **kwargs)     # Add user variable
├── append_declare(string)       # Append raw C code to declare section
├── append_initialize(string)    # Append raw C code to initialize section
├── append_finally(string)       # Append raw C code to finally section
├── write_full_instrument()      # Write instrument file to disk
├── show_diagram()               # Show instrument layout diagram
├── settings(**kwargs)           # Set simulation options
├── backengine()                 # Run simulation, returns data
├── run_to(component, ...)       # Set simulation end point (saves MCPL dump)
├── run_from(component, ...)     # Set simulation start point (loads MCPL dump)
└── show_dumps()                 # Show available beam dumps
```

### Component (returned by `add_component`)

Component parameters are set directly as attributes. Additional methods:

```
├── show_parameters()           # Show component parameters
├── set_parameters(**kwargs)    # Set parameters (dict or kwargs)
├── set_AT(list 3, RELATIVE)    # Set position
├── set_ROTATED(list 3, RELATIVE) # Set rotation
├── set_RELATIVE(name)          # Set position and rotation reference
├── set_WHEN(string)            # Set WHEN condition
├── append_EXTEND(string)       # Append C code to EXTEND section
├── set_GROUP(string)           # Set GROUP name
├── set_JUMP(string)            # Set JUMP target
├── set_SPLIT(value)            # Set SPLIT value
├── set_comment(string)         # Set component comment
├── set_c_code_before(string)   # Set C code before component
├── set_c_code_after(string)    # Set C code after component
└── print_long()                # Print full component info
```

Placement attributes (`AT`, `ROTATED`, `RELATIVE`, `WHEN`, `EXTEND`, `GROUP`, `JUMP`, `SPLIT`) can also be set via keyword arguments in `add_component()`.

### Package-level functions

```
ms.load_data(folder)            # Load simulation data from a McStas output folder
ms.load_metadata(folder)        # Load metadata (mccode.sim) from a data folder
ms.load_monitor(metadata, folder)  # Load single monitor data
ms.name_search(name, data_list) # Find dataset by component or filename
ms.name_plot_options(name, data_list, **kwargs)  # Set plot options for a dataset
```

### Plotting

```
ms.make_plot(data_list)         # Plot each dataset in a separate figure
ms.make_sub_plot(data_list)     # Plot all datasets as subplots in one figure
ms.make_animation(data_list)    # Create an animation from a list of datasets
```

### Diagnostics

```
ms.Diagnostics(instr)           # Beam and intensity diagnostics tool
```

### Tools

```
ms.Cryostat()                   # Cryostat builder for Union-based instruments
ms.has_component(instr, ...)    # Check if instrument has a given component
ms.has_parameter(instr, ...)    # Check if instrument has a given parameter
ms.all_parameters_set(instr)    # Check if all parameters have values
```

### Configuration

```
ms.Configurator()
├── set_mcrun_path(path)       # Set path to mcrun directory
├── set_mcstas_path(path)      # Set path to McStas resources
├── set_mxrun_path(path)       # Set path to mxrun directory
├── set_mcxtrace_path(path)    # Set path to McXtrace resources
└── set_line_length(length)    # Set maximum line length for output
```

### Jupyter widgets

```
import mcstasscript.jb_interface as ms_widget
ms_widget.show(data_or_instr)   # Show plot or simulation widget
ms_widget.SimInterface(instr)   # Programmatic simulation widget
ms_widget.PlotInterface(data)   # Programmatic plotting widget
```
