# Demonstration of McStasScript, an API for creating and running McStas instruments from python scripts
# Written by Mads Bertelsen, ESS DMSC
import random
import sys
sys.path.append('/Users/madsbertelsen/PaNOSC/McStasScript')
from mcstasscript.interface import instr, plotter, functions

# if the mcrun command from McStas is not in your path, provide absolute path for the binary here:
#mcrun_path = ""
mcrun_path = "/Applications/McStas-2.5.app/Contents/Resources/mcstas/2.5/bin"
#mcstas_path = ""
mcstas_path = "/Applications/McStas-2.5.app/Contents/Resources/mcstas/2.5/"

# Create a McStas instrument
instr = instr.McStas_instr("random_demo",
                           author = "Mads Bertelsen",
                           origin = "ESS DMSC",
                           mcrun_path = mcrun_path,
                           mcstas_path = mcstas_path)

# Set up a material called Cu with approrpiate properties (uses McStas Union components, here the processes)
instr.add_component("Cu_incoherent", "Incoherent_process")
instr.set_component_parameter("Cu_incoherent", {"sigma" : 4*0.55, "packing_factor" : 1, "unit_cell_volume" :  55.4})

instr.add_component("Cu_powder", "Powder_process")
instr.set_component_parameter("Cu_powder", {"reflections" : "\"Cu.laz\""})

instr.add_component("Cu", "Union_make_material")
instr.set_component_parameter("Cu", {"my_absorption" : "100*4*3.78/55.4", "process_string" : "\"Cu_incoherent,Cu_powder\""})

# Set neutron source
instr.add_component("source","Source_div", AT=[0,0,0])
instr.add_parameter("double","energy", value=10, comment="[meV] source energy") # Add parameter to select energy at run time
instr.set_component_parameter("source", {"xwidth" : 0.12, "yheight" : 0.12, "focus_aw" : 0.1, "focus_ah" : 0.1, "E0" : "energy", "dE" : 0, "flux" : 1E13})

# List of available materials, Vacuum is provided by the system
material_name_list = ["Cu", "Vacuum"]

# Wish to set up a number of randomly sized and placed boxes, here we choose the number
number_of_volumes = random.randint(30,40)

# Initialize the priority that needs to be unique for each volume
current_priority = 99
for volume in range(number_of_volumes):

    current_priority = current_priority + 1 # update the priority
    max_side_length = 0.04
    max_depth = 0.003
    position = [random.uniform(-0.05,0.05), random.uniform(-0.05,0.05), 1+random.uniform(-0.05,0.05)] # Set position in 10x10x10 cm^3 box 1 m from source
    rotation = [random.uniform(0,360), random.uniform(0,360), random.uniform(0,360)] # random rotation
    
    # Choose a random material from the list of available materials
    volume_material = random.choice(material_name_list)

    # Add a McStas Union geometry with unique name
    instr.add_component("volume_" + str(volume), "Union_box")
    instr.set_component_parameter("volume_" + str(volume), {"xwidth" : random.uniform(0.01,max_side_length), "yheight" : random.uniform(0.01,max_side_length), "zdepth" : random.uniform(0.001,max_depth),})
    instr.set_component_parameter("volume_" + str(volume), {"material_string" : "\""+volume_material+"\"", "priority" : current_priority, "p_interact" : 0.3})
    instr.set_component_AT("volume_" + str(volume), position, RELATIVE="ABSOLUTE")
    instr.set_component_ROTATED("volume_" + str(volume), rotation, RELATIVE="ABSOLUTE")


# A few Union loggers are set up for display of the scattering locations
instr.add_component("logger_space_zx_all", "Union_logger_2D_space")
current_component = instr.get_last_component()
current_component.set_parameters({"filename" : "\"space_zx.dat\"",})
current_component.set_parameters({"n1" : 1000, "D_direction_1" : "\"z\"", "D1_min" : -0.05, "D1_max" : 0.05})
current_component.set_parameters({"n2" : 1000, "D_direction_2" : "\"x\"", "D2_min" : -0.05, "D2_max" : 0.05})
current_component.set_AT([0,0,1])

instr.add_component("logger_space_zy_all", "Union_logger_2D_space")
current_component = instr.get_last_component()
current_component.set_parameters({"filename" : "\"space_zy.dat\"",})
current_component.set_parameters({"n1" : 1000, "D_direction_1" : "\"z\"", "D1_min" : -0.05, "D1_max" : 0.05})
current_component.set_parameters({"n2" : 1000, "D_direction_2" : "\"y\"", "D2_min" : -0.05, "D2_max" : 0.05})
current_component.set_AT([0,0,1])

# Union master component that executes the simulation of the random boxes
instr.add_component("random_boxes", "Union_master")

# McStas monitors for viewing the beam after the random boxes
instr.add_component("detector", "PSD_monitor", AT=[0,0,2])
instr.set_component_parameter("detector", {"xwidth" : 0.10, "yheight" : 0.10, "nx" : 500, "ny" : 500, "filename" : "\"PSD.dat\"", "restore_neutron" : 1})

instr.add_component("large_detector","PSD_monitor", AT=[0,0,2])
instr.set_component_parameter("large_detector", {"xwidth" : 1.0, "yheight" : 1.0, "nx" : 500, "ny" : 500, "filename" : "\"large_PSD.dat\"", "restore_neutron" : 1})

# Run the McStas simulation, a unique foldername is required for each run
data = instr.run_full_instrument(foldername="demonstration2", parameters={"energy":600},mpi=2,ncount=5E7)

# Set plotting options for the data (optional)
functions.name_plot_options("logger_space_zx_all", data, log=1, orders_of_mag=3)
functions.name_plot_options("logger_space_zy_all", data, log=1, orders_of_mag=3)
functions.name_plot_options("detector", data, log=1, colormap="hot", orders_of_mag=0.5)
functions.name_plot_options("large_detector", data, log=1, orders_of_mag=8)

# Plot the resulting data on a logarithmic scale
plot = plotter.make_sub_plot(data)


