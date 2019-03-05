# McStasScript classes written by Mads Bertelsen, ESS, DMSC

from __future__ import print_function
import datetime
import os
import time
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator

try: # check whether python knows about 'basestring'
   basestring
except NameError: # no, it doesn't (it's Python3); use 'str' instead
   basestring=str
   
   
class mcstas_data:
    def __init__(self,*args,**kwargs):
        # Name of data set (usually filename
        self.name = str(args[0])
        # three basic arrays as first 
        self.Intensity = args[1]
        self.Error = args[2]
        self.Ncount = args[3]
        
        self.dimension=[]  # size of the data, list with a number per dimension s
        self.limits=[]     # limits on the data to be used for plotting
        self.parameters={} # parameters used in McStas simulation
        
        self.xlabel=""
        self.ylabel=""
        self.title=""
        
        if "dimension" in kwargs:
            self.dimension = kwargs["dimension"]
        else:
            raise NameError("ERROR: Initialization of mcstas_data done without dimension for data set named " + self.name + "!")
        
        if type(self.dimension) == int:
            if "xaxis" in kwargs:
                self.xaxis = kwargs["xaxis"]
            else:
                raise NameError("ERROR: Initialization of mcstas_data done with 1d data, but without xaxis" + self.name + "!")
        
        if "limits" in kwargs:
            self.limits = kwargs["limits"]
        else:
            raise NameError("ERROR: Initialization of mcstas_data done without limits for data set named " + self.name + "!")
        
        if "parameters" in kwargs:
            self.limits = kwargs["parameters"]
            
        
    # Methods xlabel, ylabel and title as they might not be found
    def set_xlabel(self,*args):
        self.xlabel = args[0]

    def set_ylabel(self,*args):
        self.ylabel = args[0]
        
    def set_title(self,*args):
        self.title = args[0]


class managed_mcrun:
    def __init__(self,*args,**kwargs):
        self.name_of_instrumentfile = args[0]
        
        self.data_folder_name = ""
        self.ncount = 1E6 # number of rays to 
        self.parameters = {}
        self.mpi=1
        self.custom_flags = ""
        self.mcrun_path = kwargs["mcrun_path"] # mcrun_path always in kwargs
        
        
        if "foldername" in kwargs:
            self.data_folder_name = kwargs["foldername"]
        
        if "ncount" in kwargs:
            self.ncount = kwargs["ncount"]
            
        if "parameters" in kwargs:
            self.parameters = kwargs["parameters"]
            
        if "mpi" in kwargs:
            self.mpi = kwargs["mpi"]
            
        if "custom_flags" in kwargs:
            self.custom_flags = kwargs["custom_flags"]
            
    def run_simulation(self):
        option_string = "-c -n " + str(self.ncount) + " --mpi=" + str(self.mpi) + " "
        if len(self.data_folder_name) > 0:
            option_string = option_string + "-d " + self.data_folder_name
        
        parameter_string = ""
        for key,val in self.parameters.items():
            parameter_string = parameter_string + " " + str(key) + "=" + str(val)
        
        #os.system("mcstas-2.5-environment")
        
        #mcrun_path = "/Applications/McStas-2.5.app/Contents/Resources/mcstas/2.5/bin/mcrun"
        
        if self.mcrun_path[-1] == "\\" or self.mcrun_path[-1] == "/": 
            mcrun_full_path = self.mcrun_path + "mcrun"
        else:
            mcrun_full_path = self.mcrun_path + "/mcrun"
        
        os.system(mcrun_full_path + " " + option_string + " " + self.custom_flags + " " + self.name_of_instrumentfile + " " + parameter_string)
        
        # Assume the script will continue when the os.system call has concluded. Is there a way to ensure this?
        # can use subprocess from spawn* if more controll is needed over the spawned process, including a timeout
        
        time.sleep(2) # sleep 2 seconds to make sure data is written to disk before trying to open
         
        # find all data files in generated folder
        files_in_folder = os.listdir(self.data_folder_name)
        
        # create a list for data instances to return
        results = []
        
        # load the data into the list
        for file in files_in_folder:
            # Find data dimension, labels and axis
            # Find lines with these variable names
            
            filename = self.data_folder_name + "/" + file
            
            variable_list = ["type", "title", "xlabel", "ylabel", "xlimits", "xylimits"]
            located_variable_lines = {}
            
            f = open(filename,"r")
            fl = f.readlines()
            
            # Need to check if this is a data file written by McStas
            for line in fl:
                for word in variable_list:
                    if word in line:
                        located_variable_lines[word]=line
                        
            f.close()
             
            if not fl[0] == "# Format: McCode with text headers\n":
                print("Decided not to read file named " + filename)
            else:
                print("Decided to read file named " + filename)
                #print(located_variable_lines)
                
                # Need to remove the variable name and end of line break
                for key in located_variable_lines:
                    string = located_variable_lines[key]
                    located_variable_lines[key] = string[len(key)+4:-1]
                
                limits=[]
                dimension=[]
                type_string = located_variable_lines["type"]
                if "1d" in type_string:
                    # extract number of pixels
                    dimension = int(type_string[9:-1])
                    print(dimension) 
                    
                    # extract the limits of each direction
                    temp_str = located_variable_lines["xlimits"]
                    limits_string = temp_str.split()
                    for limit in limits_string:
                        limits.append(float(limit))
                    
                else:
                    # extract number of pixels in each direction
                    type_strings = type_string.split(",")
                    temp_str = type_strings[0]
                    dimension.append(int(temp_str[9:]))
                    temp_str = type_strings[1]
                    dimension.append(int(temp_str[1:-1]))
                    
                    # extract the limits of each direction
                    temp_str = located_variable_lines["xylimits"]
                    limits_string = temp_str.split()
                    for limit in limits_string:
                        limits.append(float(limit))    
                
                # Loads bulk data from file
                # Does not seem to get the meta data
                data = np.loadtxt(filename)
    
                # split data into intensity, error and ncount
                if type(dimension) == int:
                    xaxis = data.T[0,:] # not used in data yet
                    Intensity = data.T[1,:]
                    Error = data.T[2,:]
                    Ncount = data.T[3,:]
                    
                elif len(dimension) == 2:
                    xaxis = [] # assume evenly binned in 2d
                    Intensity = data.T[:,0:dimension[1]-1]
                    Error = data.T[:,dimension[1]:2*dimension[1]-1]
                    Ncount = data.T[:,2*dimension[1]:3*dimension[1]-1]
                    
                else:
                    # probably just not a McStas file then
                    raise NameError("ERROR: Could not load dimensionality of data in file named " + str(file) + "!")
                    # should probably just skip this file 
                
                # The data is saved as a mcstas_data object
                result = mcstas_data(file,Intensity,Error,Ncount,xaxis=xaxis,dimension=dimension,limits=limits)
                
                # Set optional fields
                if "xlabel" in located_variable_lines:
                    result.set_xlabel(located_variable_lines["xlabel"])
                if "ylabel" in located_variable_lines:
                    result.set_ylabel(located_variable_lines["ylabel"])
                if "title" in located_variable_lines:
                    result.set_title(located_variable_lines["title"])
                    
                results.append(result)
        
        return results
    
    
class make_plot:
    def __init__(self,*args,**kwargs):
        data_list = args[0]
        
        # Relevant options: 
        #  select colormap
        #  show / hide colorbar
        #  custom title / label
        #  color of 1d plot
        #  overlay several 1d
        #  log scale (orders of magnitude)
        #  compare several 1d
        #  compare 2D
        
        self.log = False
        if "log" in kwargs:
            if not kwargs["log"] == 0:
                self.log = True
            
        self.orders_of_magnitude=300
        if "max_orders_of_mag" in kwargs:
            self.orders_of_magnitude=kwargs["max_orders_of_mag"]
        
        if not isinstance(data_list,mcstas_data):
            print("number of elements in data list = " + str(len(data_list)))
        else:
            # Only a single element, put it in a list for easier syntax later
            data_list = [data_list]
        for data in data_list:
            print("Plotting data with name " + data.name)
            if type(data.dimension) == int:
                fig = plt.figure(0)
                
                #print(data.T)
                x = data.xaxis
                y = data.Intensity
                y_err = data.Error
                
                plt.errorbar(x, y, yerr=y_err)
                
                plt.xlim(data.limits[0],data.limits[1])
                
                # Add a title
                plt.title(data.title)
                
                # Add axis labels
                plt.xlabel(data.xlabel)
                plt.ylabel(data.ylabel)
                
            elif  len(data.dimension) == 2:
                
                # Split the data into intensity, error and ncount
                Intensity = data.Intensity
                Error = data.Error
                Ncount = data.Ncount
                
                # Select to plot the intensity
                #to_plot = np.log(Intensity)
                
                if self.log:
                    min_value = np.min(Intensity[np.nonzero(Intensity)])
                    min_value = np.log10(min_value)
                    
                    to_plot = np.log10(Intensity)
                    
                    max_value = to_plot.max()
                    
                    if max_value - min_value > self.orders_of_magnitude:
                        min_value = max_value - self.orders_of_magnitude
                else:
                    to_plot = Intensity
                    min_value = to_plot.min()
                    max_value = to_plot.max()
                
                # Check the size of the array to be plotted 
                #print(to_plot.shape)
                
                # Set the axis (might be switched?)
                X=np.linspace(data.limits[0],data.limits[1],data.dimension[0]+1)
                Y=np.linspace(data.limits[2],data.limits[3],data.dimension[1])
                
                # Create a meshgrid for both x and y
                y, x = np.meshgrid(Y,X)
                
                
                # Generate information on necessary colorrange
                levels = MaxNLocator(nbins=150).tick_values(min_value, max_value)
                #levels = MaxNLocator(nbins=150).tick_values(to_plot.max()-12, to_plot.max())
                
                # Select colormap
                cmap = plt.get_cmap('hot')
                norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)
                
                # Create the figure
                fig, (ax0) = plt.subplots()
                
                # Plot the data on the meshgrids
                im = ax0.pcolormesh(x, y, to_plot, cmap=cmap, norm=norm)
                
                # Add the colorbar
                fig.colorbar(im, ax=ax0)
                
                # Add a title
                ax0.set_title(data.title)
                
                # Add axis labels
                plt.xlabel(data.xlabel)
                plt.ylabel(data.ylabel)
                
            else:
                print("Error, dimension not read correctly")
            
        plt.show()
        

class parameter_variable:
    def __init__(self,*args,**kwargs):
        if len(args) == 1:
            self.type = ""
            self.name = str(args[0])
        if len(args) == 2:
            self.type = args[0] + " "
            self.name = str(args[1])
        
        if "value" in kwargs:
            self.value_set = 1
            self.value = kwargs["value"]
        else:
            self.value_set = 0

        if "comment" in kwargs:
            self.comment = "// " + kwargs["comment"]
        else:
            self.comment = ""

        # could check for allowed types
        # they are int, double, string, are there more?

    def write_parameter(self,fo,stop_character):
        fo.write("%s%s" % (self.type, self.name))
        if self.value_set == 1:
            if isinstance(self.value,int):
                fo.write(" = %d" % self.value)
            elif isinstance(self.value,float):
                fo.write(" = %G" % self.value)
            else:
                fo.write(" = %s" % str(self.value))
        fo.write(stop_character)
        fo.write(self.comment)
        fo.write("\n")

class declare_variable:
    def __init__(self,*args,**kwargs):
        self.type = args[0]
        self.name = str(args[1])
        if "value" in kwargs:
            self.value_set = 1
            self.value = kwargs["value"]
        else:
            self.value_set = 0
        if "array" in kwargs:
            self.vector = kwargs["array"]
        else:
            self.vector = 0

        if "comment" in kwargs:
            self.comment = " // " + kwargs["comment"]
        else:
            self.comment = ""

    def write_line(self,fo):
        if self.value_set == 0 and self.vector == 0:
            fo.write("%s %s;%s" % (self.type, self.name,self.comment))
        if self.value_set == 1 and self.vector == 0:
            if self.type == "int":
                fo.write("%s %s = %d;%s" % (self.type, self.name, self.value, self.comment))
            else:
                fo.write("%s %s = %G;%s" % (self.type, self.name, self.value,self.comment))
        if self.value_set == 0 and self.vector != 0:
            fo.write("%s %s[%d];%s" % (self.type, self.name, self.vector, self.comment))
        if self.value_set == 1 and self.vector != 0:
            fo.write("%s %s[%d] = {" % (self.type, self.name, self.vector))
            for i in range(0,len(self.value)-1):
                fo.write("%G," % self.value[i])
            fo.write("%G};%s" % (self.value[-1], self.comment))


class component:
    def __init__(self,*args,**kwargs):
        # Defines a McStas component with name and component name as first inputs
        self.name = args[0]
        self.component_name = args[1]
        
        # Possible to give AT and ROTATED including AT_RELATIVE / ROTATED_RELATIVE
        # RELATIVE keyword also exists and sets both AT_RELATIVE and ROTATED_RELATIVE
        if "AT" in kwargs:
            self.AT_data = kwargs["AT"]
        else:
            self.AT_data = [0,0,0]
        # need to check if AT_RELATIVE is a string
        if "AT_RELATIVE" in kwargs:
            self.AT_relative = "RELATIVE " + kwargs["AT_RELATIVE"]
        else:
            self.AT_relative = "ABSOLUTE"
        
        # If rotated is never mentioned, why print it? How does this influence McStas?
        if "ROTATED" in kwargs:
            self.ROTATED_data = kwargs["AT"]
        else:
            self.ROTATED_data = [0,0,0]
        # need to check if ROTATED_RELATIVE is a string
        if "ROTATED_RELATIVE" in kwargs:
            self.ROTATED_relative = kwargs["ROTATED_RELATIVE"]
        else:
            self.ROTATED_relative = "ABSOLUTE"
        
        # need to check if RELATIVE is a string
        if "RELATIVE" in kwargs:
            self.AT_relative = "RELATIVE " + kwargs["RELATIVE"]
            self.ROTATED_relative = "RELATIVE " + kwargs["RELATIVE"]

        # possible to have a c comment
        if "comment" in kwargs:
            self.comment = kwargs["comment"]
        else:
            self.comment = ""

        # initialize a dictionary
        self.component_parameters = {}
        
        # possible to store a preference for wehter this component should
        #  be in a include file or directly in the instrument?
        
    # method for setting AT and AT_RELATIVE after initialization
    def set_AT(self,at_list,**kwargs):
        self.AT_data=at_list
        if "RELATIVE" in kwargs:
            relative_name = kwargs["RELATIVE"]
            if relative_name == "ABSOLUTE":
                self.AT_relative = relative_name
            else:
                self.AT_relative = "RELATIVE " + relative_name
    
    # method for setting ROTATED and ROTATED_RELATIVE after initialization
    def set_ROTATED(self,rotated_list,**kwargs):
        self.ROTATED_data=rotated_list
        if "RELATIVE" in kwargs:
            relative_name = kwargs["RELATIVE"]
            if relative_name == "ABSOLUTE":
                self.ROTATED_relative = relative_name
            else:
                self.ROTATED_relative = "RELATIVE " + relative_name
    
    # method for setting RELATIVE after initialization
    def set_RELATIVE(self,relative_name):
        if relative_name == "ABSOLUTE":
            self.AT_relative = relative_name
            self.ROTATED_relative = relative_name
        else:
            self.AT_relative = "RELATIVE " + relative_name
            self.ROTATED_relative = "RELATIVE " + relative_name

    # method that adds a parameter name / value pair to dictionary
    def set_parameters(self,dict_input):
        self.component_parameters.update(dict_input)
    
    # method that sets a comment to be written to instrument file
    def set_comment(self,string):
        self.comment = string

    # method that writes component to file
    def write_component(self,fo):
        parameters_per_line = 2 # write comma separated parameters, up to 2 per line
        # could use a character limit on lines instead
        parameters_written = 0  # internal parameter
        number_of_parameters = len(self.component_parameters) # internal parameter
    
        # write comment if present
        if len(self.comment) > 1:
            fo.write("// %s\n" % (str(self.comment)))
    
        # write component name and component type
        fo.write("COMPONENT %s = %s(" % (self.name, self.component_name))
        
        if number_of_parameters == 0:
            fo.write(")\n") # if there are no parameters, close the component immediately
        else:
            fo.write("\n") # if there are parameters to be written, start a new line
        
        for key,val in self.component_parameters.items():
            if isinstance(val,float): # check if value is a number
                fo.write(" %s = %G" % (str(key),val)) # Small or large numbers written in scientific format
            else:
                fo.write(" %s = %s" % (str(key),str(val)))
            parameters_written = parameters_written + 1
            if parameters_written < number_of_parameters:
                fo.write(",") # comma between parameters
                if parameters_written%parameters_per_line == 0:
                    fo.write("\n")
            else:
                fo.write(")\n") # end paranthesis after last parameter
    
        # Need to add WHEN section here
        # Need to add JUMP section here
        # write AT and ROTATED section
        fo.write("AT (%s,%s,%s)" % (str(self.AT_data[0]),str(self.AT_data[1]),str(self.AT_data[2])))
        fo.write(" %s\n" % self.AT_relative)
        fo.write("ROTATED (%s,%s,%s)" % (str(self.ROTATED_data[0]),str(self.ROTATED_data[1]),str(self.ROTATED_data[2])))
        fo.write(" %s\n\n" % self.ROTATED_relative)
        # Need to add EXTEND section here

    # print component long
    def print_long(self):
        print("// " + self.comment)
        print("COMPONENT " + str(self.name) + " = " + str(self.component_name))
        for key,val in self.component_parameters.items():
            print(" ",key,"=",val)
        print("AT",self.AT_data,self.AT_relative)
        print("ROTATED",self.ROTATED_data,self.ROTATED_relative)

    # print component short
    def print_short(self,**kwargs):
        if "longest_name" in kwargs:
            print("test")
            print(str(self.name)+" "*(3+kwargs["longest_name"]-len(self.name)),end='')
            print(str(self.component_name),"\tAT",self.AT_data,self.AT_relative,"ROTATED",self.ROTATED_data,self.ROTATED_relative)
        else:
            print(str(self.name),"=",str(self.component_name),"\tAT",self.AT_data,self.AT_relative,"ROTATED",self.ROTATED_data,self.ROTATED_relative)


class McStas_instr:
    def __init__(self,name,**kwargs):
        self.name = name
        
        if "author" in kwargs:
            self.author = kwargs["author"]
        else:
            self.author = "Python McStas Instrument Generator"
        
        if "origin" in kwargs:
            self.origin = kwargs["origin"]
        else:
            self.origin = "ESS DMSC"
            
        if "mcrun_path" in kwargs:
            self.mcrun_path = kwargs["mcrun_path"]
        else:
            self.mcrun_path = ""
        
        self.parameter_list = []
        self.declare_list = []
        self.initialize_section = "// Start of initialize for generated " + name + "\n"
        self.trace_section = "// Start of trace section for generated " + name + "\n"
        # handle components
        self.component_list = [] # list of components (have to be ordered)
        self.component_name_list = [] # list of component names
        
    def add_parameter(self,*args,**kwargs):
        # type of variable, name of variable, options described in declare_parameter class
        self.parameter_list.append(parameter_variable(*args,**kwargs))

    def add_declare_var(self,*args,**kwargs):
        # type of variable, name of variable, options described in declare_variable class
        self.declare_list.append(declare_variable(*args,**kwargs))

    def append_initialize(self,string):
        self.initialize_section = self.initialize_section + string + "\n"
    
    def append_initialize_no_new_line(self,string):
        self.initialize_section = self.initialize_section + string
    
    # Need to handle trace string differently when components also exists
    #  A) Could have trace string as a component attribute and set it before / after
    #  B) Could have trace string as a McStas_instr attribute and still attach placement to components
    #  C) Could have trace string as a different object and place it in component_list, but have a write function named as the component write function?
    
    def append_trace(self,string):
        self.trace_section = self.trace_section + string + "\n"
    
    def append_trace_no_new_line(self,string):
        self.trace_section = self.trace_section + string
                 
    # methods for creating new components and modifiying existing components
    def add_component(self,*args,**kwargs):
        if args[0] in self.component_name_list:
            raise NameError("Component name \"" + str(args[0]) + "\" used twice, McStas does not allow this. Rename or remove one instance of this name.")
        
        if "after" in kwargs: # insert component after component with this name
            if kwargs["after"] not in self.component_name_list:
                raise NameError("Trying to add a component after a component named \"" + str(kwargs["after"]) + "\", but a component with that name was not found.")
        
            new_index = self.component_name_list.index(kwargs["after"])
            self.component_list.insert(new_index+1,component(*args,**kwargs))
            self.component_name_list.insert(new_index+1,args[0])
        elif "before" in kwargs: # insret component after component with this name
            if kwargs["before"] not in self.component_name_list:
                raise NameError("Trying to add a component before a component named \"" + str(kwargs["before"]) + "\", but a component with that name was not found.")
        
            new_index = self.component_name_list.index(kwargs["before"])
            self.component_list.insert(new_index,component(*args,**kwargs))
            self.component_name_list.insert(new_index,args[0])
        else:
            self.component_list.append(component(*args,**kwargs))
            self.component_name_list.append(args[0])
    
    def get_component(self,name):
        if name in self.component_name_list:
            index = self.component_name_list.index(name)
            return self.component_list[index]
        else:
            raise NameError("No component was found with name \"" + str(name) + "\"!")
            
    def get_last_component(self):
        return self.component_list[-1]

    def set_component_parameter(self,name,input_dict):
        component = self.get_component(name)
        component.set_parameters(input_dict)

    def set_component_AT(self,name,at_list,**kwargs):
        component = self.get_component(name)
        component.set_AT(at_list,**kwargs)
        
    def set_component_ROTATED(self,name,rotated_list,**kwargs):
        component = self.get_component(name)
        component.set_ROTATED(rotated_list,**kwargs)
    
    def set_component_RELATIVE(self,name,relative):
        component = self.get_component(name)
        component.set_RELATIVE(relative)
    
    def set_component_comment(self,name,string):
        component = self.get_component(name)
        component.set_comment(string)

    def print_component(self,name):
        component = self.get_component(name)
        component.print_long()
    
    def print_component_short(self,name):
        component = self.get_component(name)
        component.print_short()
    
    def print_components(self):
    
        longest_name = len(max(self.component_name_list,key=len))
        
        # Investigate how this could have been done in a better way
        # Find longest field for each type of data printed
        component_type_list = []
        at_x_list = []
        at_y_list = []
        at_z_list = []
        at_relative_list = []
        rotated_x_list = []
        rotated_y_list = []
        rotated_z_list = []
        rotated_relative_list = []
        for component in self.component_list:
            component_type_list.append(component.component_name)
            at_x_list.append(str(component.AT_data[0]))
            at_y_list.append(str(component.AT_data[1]))
            at_z_list.append(str(component.AT_data[2]))
            at_relative_list.append(component.AT_relative)
            rotated_x_list.append(str(component.ROTATED_data[0]))
            rotated_y_list.append(str(component.ROTATED_data[1]))
            rotated_z_list.append(str(component.ROTATED_data[2]))
            rotated_relative_list.append(component.ROTATED_relative)
        
        longest_component_name = len(max(component_type_list,key=len))
        longest_at_x_name = len(max(at_x_list,key=len))
        longest_at_y_name = len(max(at_y_list,key=len))
        longest_at_z_name = len(max(at_z_list,key=len))
        longest_at_relative_name = len(max(at_relative_list,key=len))
        longest_rotated_x_name = len(max(rotated_x_list,key=len))
        longest_rotated_y_name = len(max(rotated_y_list,key=len))
        longest_rotated_z_name = len(max(rotated_z_list,key=len))
        longest_rotated_relative_name = len(max(rotated_relative_list,key=len))
        
        # Have longest field for each type, use ljust to align all columns
        for component in self.component_list:
            print(str(component.name).ljust(longest_name+2),end=' ')
            print(str(component.component_name).ljust(longest_component_name+2),end=' ')
            print("AT ",str(component.AT_data).ljust(longest_at_x_name+longest_at_y_name+longest_at_z_name+11),end='')
            print(component.AT_relative.ljust(longest_at_relative_name+2),end=' ')
            print("ROTATED ",str(component.ROTATED_data).ljust(longest_rotated_x_name+longest_rotated_y_name+longest_rotated_z_name+11),end='')
            print(component.ROTATED_relative)
            #print("")

    def write_c_files(self):
        # method for writing c files that can be included in instruments
        
        path = os.getcwd()
        path = path + "/generated_includes"
        if not os.path.isdir(path):
            try:
                os.mkdir(path)
            except OSError:
                print ("Creation of the directory %s failed" % path)
        
        fo = open("./generated_includes/" + self.name + "_declare.c","w")
        fo.write("// declare section for %s \n" % self.name)
        fo.close()
        fo = open("./generated_includes/" + self.name + "_declare.c","a")
        for dec_line in self.declare_list:
            dec_line.write_line(fo)
            fo.write("\n")
        fo.close()
        
        fo = open("./generated_includes/" + self.name + "_initialize.c","w")
        fo.write(self.initialize_section)
        fo.close()

        fo = open("./generated_includes/" + self.name + "_trace.c","w")
        fo.write(self.trace_section)
        fo.close()
        
        fo = open("./generated_includes/" + self.name + "_component_trace.c","w")
        for component in self.component_list:
            component.write_component(fo)
        fo.close()

    # Method that writes full instrument file.
    def write_full_instrument(self):
        # method for writing an instrument file
        # could either use generated includes or write everything out
        # will probably create an option to choose between these methods later
        
        # Create file identifier
        fo = open(self.name + ".instr","w")

        # Write quick doc start
        fo.write("/" + "*"*80 + "\n")
        fo.write("* \n")
        fo.write("* McStas, neutron ray-tracing package\n")
        fo.write("*         Copyright (C) 1997-2008, All rights reserved\n")
        fo.write("*         Risoe National Laboratory, Roskilde, Denmark\n")
        fo.write("*         Institut Laue Langevin, Grenoble, France\n")
        fo.write("* \n")
        fo.write("* This file was written by the Python McStas Instrument Generator \n")
        fo.write("*  which was written by Mads Bertelsen in 2019 while employed at \n")
        fo.write("*  the European Spallation Source Data Management and Software Center\n")
        fo.write("* \n")
        fo.write("* Instrument %s\n" % self.name)
        fo.write("* \n")
        fo.write("* %Identification\n") # Could allow the user to insert these
        fo.write("* Written by: %s\n" % self.author)
        fo.write("* Date: %s\n" % datetime.datetime.now().strftime("%H:%M:%S on %B %d, %Y"))
        fo.write("* Origin: %s\n" % self.origin)
        fo.write("* %INSTRUMENT_SITE: Generated_instruments\n")
        fo.write("* \n")
        fo.write("* \n")
        fo.write("* %Parameters\n")
        # Add description of parameters here
        fo.write("* \n")
        fo.write("* %End \n")
        fo.write("*"*80 + "/\n")
        fo.write("\n")
        fo.write("DEFINE INSTRUMENT %s (" % self.name)
        fo.write("\n")
        # Add loop that inserts parameters here
        for variable in self.parameter_list[0:-1]:
            variable.write_parameter(fo,",")
        if len(self.parameter_list) > 0:
            self.parameter_list[-1].write_parameter(fo," ")
        fo.write(")\n")
        fo.write("\n")

        # Write declare
        fo.write("DECLARE \n %{\n")
        for dec_line in self.declare_list:
            dec_line.write_line(fo)
            fo.write("\n")
        fo.write("%}\n\n")

        # Write initialize
        fo.write("INITIALIZE \n %{\n")
        fo.write(self.initialize_section)
        # Alternatively hide everything in include
        # fo.write("%include "generated_includes/" + self.name + "_initialize.c")
        fo.write("%}\n\n")

        # Write trace
        fo.write("TRACE \n")
        for component in self.component_list:
            component.write_component(fo)

        # Write finally (no finally possible yet)

        # End instrument file
        fo.write("\nEND\n")
        
    def run_full_instrument(self,*args,**kwargs):
        # Write the instrument file
        self.write_full_instrument()
        
        # Make sure mcrun path is in kwargs
        if not "mcrun_path" in kwargs:
            kwargs["mcrun_path"] = self.mcrun_path
            
        # Set up the simulation 
        simulation = managed_mcrun(self.name + ".instr",**kwargs)
        
        # Run the simulation and return data
        return simulation.run_simulation()
        
        
        
