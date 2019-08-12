# McStasScript
McStas API for creating and running McStas instruments from python scripting

Prototype for an API that allow interaction with McStas through an interface like Jupyter Notebooks created under WP5 of PaNOSC.

## Installation
The package can be installed using pip

    python3 -m pip install McStasScript --upgrade

It is necessary to configure the package so the McStas installation can be found, here we show how the appropriate code for an Ubuntu system. The configuration is saved permanently, and only needs to be updated when McStas is updated.

    from mcstasscript.interface import functions
    my_configurator = functions.Configurator()
    my_configurator.set_mcrun_path("/usr/bin/")
    my_configurator.set_mcstas_path("/usr/share/mcstas/2.5/")


## Instructions for basic use:
Import the interface 

    from mcstasscript.interface import instr, plotter, functions, reader

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
    
A monitor is added as well to get data out of the simulation

    PSD = my_instrument.add_component("PSD", "PSD_monitor", AT=[0,0,1], RELATIVE="source") 
    PSD.xwidth = 0.1
    PSD.yheight = 0.1
    PSD.nx = 200
    PSD.ny = 200
    PSD.filename = "\"PSD.dat\""

This simple simulation can be executed from the 

    data = my_instrument.run_full_instrument(foldername="first_run", increment_folder_name=True)

Results from the monitors would be stored as a list of McStasData objects in the returned data. The counts are stored as numpy arrays. We can read and change the intensity directly and manipulate the data before plotting.

    data[0].Intensity
    
Plotting is usually done in a subplot of all monitors recorded.    

    plot = plotter.make_sub_plot(data)

## Use in existing project
If one wish to work on existing projects using McStasScript, there is a reader included that will read a McStas Instrument file and write the corresponding McStasScript python instrument to disk. Here is an example where the PSI_DMC.instr example is converted:

    Reader = reader.McStas_file("PSI_DMC.instr")
    reader.write_python_file("PSI_DMC_generated.py")

It is highly advised to run a check between the output of the generated file and the original to ensure the process was sucessful.

## Method overview
Here is a quick overview of the available methods of the main classes in the project. Most have more options from keyword arguments that are explained in the manual, but also in python help, for example help(instr.McStas_instr.show_components).

    instr
    └── McStas_instr(str instr_name) # Returns McStas instrument object on initialize
        ├── show_components(str category_name) # Show available components in given category
        ├── component_help(str component_name) # Prints component parameters for given component name   
        ├── add_component(str name, str component_name) # Adds component to instrument and returns object
        ├── add_parameter(str name) # Adds instrument parameter with name
        ├── add_declare_var(str type, str name) # Adds declared variable with type and name
        ├── append_initialize(str string) # Appends a line to initialize (c syntax)
        ├── print_components() # Prints list of components and their location
        ├── write_full_instrument() # Writes instrument to disk with given name + ".instr"
        └── run_full_instrument() # Runs simulation. Options in keyword arguments. Returns list of McStasData
        
    component # returned by add_component
    ├── set_AT(list at_list) # Sets component position (list of x,y,z positions in [m])
    ├── set_ROTATED(list rotated_list) # Sets component rotation (list of x,y,z rotations in [deg])
    ├── set_RELATIVE(str component_name) # Sets relative to other component name
    ├── set_parameters(dict input) # Set parameters using dict input
    ├── set_comment(str string) # Set comment explaining something about the component
    └── print_long() # Prints currently contained information on component
    
    functions
    ├── name_search(str name, list McStasData) # Returns data set with given name from McStasData list
    ├── name_plot_options(str name, list McStasData, kwargs) # Sends kwargs to dataset with given name
    ├── load_data(str foldername) # Loads data from folder with McStas data as McStasData list
    └── Configurator()
        ├── set_mcrun_path(str path) # sets mcrun path
        ├── set_mcstas_path(str path) # sets mcstas path
        └── set_line_length(int length) # sets maximum line length
    
    plotter
    ├── make_plot(list McStasData) # Plots each data set individually
    └── make_sub_plot(list McStasData) # Plots data as subplot
    
    reader
    └──  McStas_file(str filename) # Returns a reader that can extract information from given instr file

    InstrumentReader # returned by McStas_file
    ├── generate_python_file(str filename) # Writes python file with information contaiend in isntrument
    └── add_to_instr(McStas_instr Instr) # Adds information from instrument to McStasScirpt instrument
