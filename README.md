# McStasScript
McStas API for creating and running McStas instruments from python scripting

Prototype for an API that allow interaction with McStas through an interface like Jupyter Notebooks created under WP5 of PaNOSC.

## Instructions for basic use:
Download the entire project
Set up paths to McStas in the configuration.yaml file
Before import in python, add the project to your path: 
import sys
sys.path.append('path/to/McStasScript')
Import the interface 
from mcstasscript.interface import instr, plotter, functions

Now the package can be used. Start with creating a new instrument, just needs a name

my_instrument = instr.McStas_instr("my_instrument_file")

Then McStas components can be added, here we add a source

my_source = my_instrument.add_component("source", "Source_simple")

my_source.show_parameters() # Can be used to show available parameters for Source simple

The parameters of the source can be adjusted directly as attributes of the python object

my_source.xwidth = 0.12

my_source.yheight = 0.12

my_source.lambda0 = 3

my_source.dlambda = 2.2

my_source.focus_xw = 0.05

my_source.focus_yh = 0.05

Running the simple instrument of just a source
data = my_instrument.run_full_instrument(foldername="first_run", increment_folder_name=True)

Any data generated would be stored as a list of McStasData objects in the returned data

plot = plotter.make_sub_plot(data)



