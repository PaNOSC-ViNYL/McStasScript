# Demonstration of McStasScript, an API for creating and running McStas instruments from python scripts
# Written by Mads Bertelsen, ESS DMSC
import random

import mcstasscript as ms

# Create a McStas instrument
instr = ms.McStas_instr("random_demo",
                        author = "Mads Bertelsen",
                        origin = "ESS DMSC")

# Set up a material called Cu with approrpiate properties
# (uses McStas Union components, here the processes)

Init = instr.add_component("init", "Union_init")

Cu_inc = instr.add_component("Cu_incoherent", "Incoherent_process")
Cu_inc.sigma = 4*0.55
Cu_inc.packing_factor = 1
Cu_inc.unit_cell_volume = 55.4

Cu_powder = instr.add_component("Cu_powder", "Powder_process")
Cu_powder.reflections = "\"Cu.laz\""

Cu = instr.add_component("Cu", "Union_make_material")
Cu.my_absorption = "100*4*3.78/55.4"
Cu.process_string = "\"Cu_incoherent,Cu_powder\""

# Add neutron source
Source = instr.add_component("source", "Source_div")
# Add parameter to select energy at run time
energy = instr.add_parameter("double", "energy", value=10, comment="[meV] source energy")

Source.xwidth = 0.12
Source.yheight = 0.12
Source.focus_aw = 0.1
Source.focus_ah = 0.1
Source.E0 = energy
Source.dE = 0.0
Source.flux = 1E13

# List of available materials, Vacuum is provided by the system
material_name_list = ["Cu", "Vacuum"]

# Wish to set up a number of random boxes, here the number is chosen at random
number_of_volumes = random.randint(30, 40)

# Initialize the priority that needs to be unique for each volume
current_priority = 99
for volume in range(number_of_volumes):

    current_priority = current_priority + 1 # update the priority
    max_side_length = 0.04
    max_depth = 0.003
    # Set position in 10x10x10 cm^3 box 1 m from source
    position = [random.uniform(-0.05,0.05),
                random.uniform(-0.05,0.05),
                1+random.uniform(-0.05,0.05)]
    # Set random rotation
    rotation = [random.uniform(0,360),
                random.uniform(0,360),
                random.uniform(0,360)]

    # Choose a random material from the list of available materials
    volume_material = random.choice(material_name_list)

    # Add a McStas Union geometry with unique name
    this_geometry = instr.add_component("volume_" + str(volume), "Union_box")
    this_geometry.xwidth = random.uniform(0.01, max_side_length)
    this_geometry.yheight = random.uniform(0.01, max_side_length)
    this_geometry.zdepth = random.uniform(0.01, max_side_length)
    this_geometry.material_string = '"' + volume_material + '"'
    this_geometry.priority = current_priority
    this_geometry.p_interact = 0.3
    
    this_geometry.set_AT(position, RELATIVE="ABSOLUTE")
    this_geometry.set_ROTATED(rotation, RELATIVE="ABSOLUTE")

# A few Union loggers are set up for display of the scattering locations
space_2D_zx = instr.add_component("logger_space_zx_all", "Union_logger_2D_space")
space_2D_zx.filename = '"space_zx.dat"'
space_2D_zx.n1 = 1000
space_2D_zx.D_direction_1 = '"z"'
space_2D_zx.D1_min = -0.05
space_2D_zx.D1_max = 0.05
space_2D_zx.n2 = 1000
space_2D_zx.D_direction_2 = '"x"'
space_2D_zx.D2_min = -0.05
space_2D_zx.D2_max = 0.05
space_2D_zx.set_AT([0,0,1])

space_2D_zy = instr.add_component("logger_space_zy_all", "Union_logger_2D_space")
space_2D_zy.filename = '"space_zy.dat"'
space_2D_zy.n1 = 1000
space_2D_zy.D_direction_1 = '"z"'
space_2D_zy.D1_min = -0.05
space_2D_zy.D1_max = 0.05
space_2D_zy.n2 = 1000
space_2D_zy.D_direction_2 = '"y"'
space_2D_zy.D2_min = -0.05
space_2D_zy.D2_max = 0.05
space_2D_zy.set_AT([0,0,1])

# Union master component that executes the simulation of the random boxes
instr.add_component("random_boxes", "Union_master")

# McStas monitors for viewing the beam after the random boxes
PSD = instr.add_component("detector", "PSD_monitor", AT=[0,0,2])
PSD.xwidth = 0.1
PSD.yheight = 0.1
PSD.nx = 500
PSD.ny = 500
PSD.filename = '"PSD.dat"'
PSD.restore_neutron = 1

big_PSD = instr.add_component("large_detector", "PSD_monitor", AT=[0,0,2])
big_PSD.xwidth = 1.0
big_PSD.yheight = 1.0
big_PSD.nx = 500
big_PSD.ny = 500
big_PSD.filename = '"big_PSD.dat"'
big_PSD.restore_neutron = 1

Stop = instr.add_component("stop", "Union_stop")

instr.show_components()

# Run the McStas simulation, a unique foldername is required for each run
instr.settings(output_path="demonstration", mpi=2, ncount=5E7)
instr.set_parameters(energy=600)

data = instr.backengine()

# Set plotting options for the data (optional)
ms.name_plot_options("logger_space_zx_all", data, log=1, orders_of_mag=3)
ms.name_plot_options("logger_space_zy_all", data, log=1, orders_of_mag=3)
ms.name_plot_options("detector", data, log=1, colormap="hot", orders_of_mag=0.5)
ms.name_plot_options("large_detector", data, log=1, orders_of_mag=8)

# Plot the resulting data on a logarithmic scale
plot = ms.make_sub_plot(data)
