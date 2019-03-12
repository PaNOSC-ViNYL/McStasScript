# McStasScript classes written by Mads Bertelsen, ESS, DMSC

from __future__ import print_function
import datetime
import os
import time
import math
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from matplotlib.ticker import MaxNLocator
from openpyxl.worksheet import dimensions
from boto.ec2.autoscale import limits

try: # check whether python knows about 'basestring'
   basestring
except NameError: # no, it doesn't (it's Python3); use 'str' instead
   basestring=str

class mcstas_meta_data:
    def __init__(self,*args,**kwargs):
        self.info = {}
    
    def add_info(self,key,value):
        self.info[key] = value
        
    def extract_info(self):
        
        
        if "type" in self.info:
            # extract dimension
            type = self.info["type"]
            if "array_1d" in type:
                self.dimension = int(type[9:-2])
            if "array_2d" in type:
                self.dimension=[]
                type_strings = self.info["type"].split(",")
                temp_str = type_strings[0]
                self.dimension.append(int(temp_str[9:]))
                temp_str = type_strings[1]
                self.dimension.append(int(temp_str[1:-2]))
        else:
            raise NameError("No type in mccode data section!")
                
        if "component" in self.info:
            self.component_name = self.info["component"].rstrip()

        if "filename" in self.info:
            self.filename = self.info["filename"].rstrip()
        else:
            raise NameError("No filename found in mccode data section!")
        
        self.limits = []
        if "xylimits" in self.info:
            # find the four numbers 
            temp_str = self.info["xylimits"]
            limits_string = temp_str.split()
            for limit in limits_string:
                self.limits.append(float(limit))

        if "xlimits" in self.info:
            # find the four numbers 
            temp_str = self.info["xlimits"]
            limits_string = temp_str.split()
            for limit in limits_string:
                self.limits.append(float(limit))

        if "xlabel" in self.info:
            self.xlabel = self.info["xlabel"].rstrip()
        if "ylabel" in self.info:
            self.ylabel = self.info["ylabel"].rstrip()
        if "title" in self.info:
            self.title = self.info["title"].rstrip()
    
    def set_title(self,string):
        self.title = string
        
    def set_xlabel(self,string):
        self.xlabel = string
        
    def set_ylabel(self,string):
        self.ylabel = string
        
    
        
class mcstas_data:
    def __init__(self,*args,**kwargs):
        # attatch meta data
        self.metadata = args[0]
        # get name from metadata
        self.name = self.metadata.component_name
        # three basic arrays as first 
        self.Intensity = args[1]
        self.Error = args[2]
        self.Ncount = args[3]
        
        if type(self.metadata.dimension) == int:
            if "xaxis" in kwargs:
                self.xaxis = kwargs["xaxis"]
            else:
                raise NameError("ERROR: Initialization of mcstas_data done with 1d data, but without xaxis" + self.name + "!")
        
    # Methods xlabel, ylabel and title as they might not be found
    def set_xlabel(self,string):
        self.metadata.set_xlabel(string)
        
    def set_ylabel(self,string):
        self.metadata.set_ylabel(string)
        
    def set_title(self,string):
        self.metadata.set_title(string)
        

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
        if len(self.mcrun_path) > 1:
            if self.mcrun_path[-1] == "\\" or self.mcrun_path[-1] == "/": 
                mcrun_full_path = self.mcrun_path + "mcrun"
            else:
                mcrun_full_path = self.mcrun_path + "/mcrun"
        else:
            mcrun_full_path = self.mcrun_path + "mcrun"
        
        os.system(mcrun_full_path + " " + option_string + " " + self.custom_flags + " " + self.name_of_instrumentfile + " " + parameter_string)
        
        # Assume the script will continue when the os.system call has concluded. Is there a way to ensure this?
        # can use subprocess from spawn* if more controll is needed over the spawned process, including a timeout
        
        time.sleep(1) # sleep 1 second to make sure data is written to disk before trying to open
         
        # find all data files in generated folder
        files_in_folder = os.listdir(self.data_folder_name)
        
        # raise an error if mccode.sim is not available
        if not "mccode.sim" in files_in_folder:
            raise NameError("mccode.sim not written to output folder.")
        
        f = open(self.data_folder_name + "/mccode.sim","r")
        #fl = f.readlines()
        
        metadata_list = []
        in_data = False
        
        for lines in f:
            # Could read other details about run
            
            if lines == "end data\n":
                # current data object done, write to list
                current_object.extract_info()
                metadata_list.append(current_object)
                in_data = False
            
            if in_data:
                # break info into key and info
                colon_index = lines.index(":")
                key = lines[2:colon_index]
                value = lines[colon_index+2:]
                current_object.add_info(key, value)
            
            if lines == "begin data\n":
                # new data object
                current_object = mcstas_meta_data()
                in_data = True
                
                
        f.close()
        
        # create a list for data instances to return
        results = []
        
        for metadata in metadata_list:
            data = np.loadtxt(self.data_folder_name + "/" + metadata.filename.rstrip())
    
            # split data into intensity, error and ncount
            if type(metadata.dimension) == int:
                xaxis = data.T[0,:]
                Intensity = data.T[1,:]
                Error = data.T[2,:]
                Ncount = data.T[3,:]
                
            elif len(metadata.dimension) == 2:
                xaxis = [] # assume evenly binned in 2d
                Intensity = data.T[:,0:metadata.dimension[1]-1]
                Error = data.T[:,metadata.dimension[1]:2*metadata.dimension[1]-1]
                Ncount = data.T[:,2*metadata.dimension[1]:3*metadata.dimension[1]-1]
            else:
                raise NameError("Dimension not read correctly in data set connected to monitor named " + metadata.component_name)    
            
            # The data is saved as a mcstas_data object
            result = mcstas_data(metadata,Intensity,Error,Ncount,xaxis=xaxis)
            
            results.append(result)
            
            f.close()
            
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
        
        if isinstance(data_list,mcstas_data):
            # Only a single element, put it in a list for easier syntax later
            data_list = [data_list]
            
        number_of_plots = len(data_list)
        
        self.log = [False]*number_of_plots
        if "log" in kwargs:
            if isinstance(kwargs["log"],list):
                if not len(kwargs["log"]) == number_of_plots:
                    raise IndexError("Length of list given for log logic does not match number of data elements")
                else:
                    self.log = kwargs["log"]
                    for element in self.log:
                        if not isinstance(element, bool):
                            if not element == 0:
                                element = True 
            elif isinstance(kwargs["log"],bool):
                if kwargs["log"] == True:
                    self.log = [True]*number_of_plots
            elif isinstance(kwargs["log"],int):
                if kwargs["log"] == 1:
                    self.log = [True]*number_of_plots
            else:
                raise NameError("log keyword Argument in make_sub_plot not understood. Needs to be int, [1/0], bool [True/False] or array of same length as data.")
                
        
        self.orders_of_mag=[300] * number_of_plots
        if "max_orders_of_mag" in kwargs:
            if isinstance(kwargs["max_orders_of_mag"],list):
                if not len(kwargs["max_orders_of_mag"]) == number_of_plots:
                    raise IndexError("Length of list given for max_orders_of_mag does not match number of data elements")
                else: 
                    self.orders_of_mag = kwargs["max_orders_of_mag"]
            else:
                if isinstance(kwargs["max_orders_of_mag"],float) or isinstance(kwargs["max_orders_of_mag"],int):
                    self.orders_of_magnitude=[kwargs["max_orders_of_mag"]]*number_of_plots
                else:
                    raise TypeError("max_orders_of_mag need to be of type float or int")
        
            
        print("number of elements in data list = " + str(len(data_list)))
        
        index = -1
        for data in data_list:
            index = index + 1
            
            print("Plotting data with name " + data.metadata.component_name)
            if type(data.metadata.dimension) == int:
                fig = plt.figure(0)
                
                #print(data.T)
                x = data.xaxis
                y = data.Intensity
                y_err = data.Error
                
                plt.errorbar(x, y, yerr=y_err)
                
                plt.xlim(data.metadata.limits[0],data.metadata.limits[1])
                
                # Add a title
                plt.title(data.metadata.title)
                
                # Add axis labels
                plt.xlabel(data.metadata.xlabel)
                plt.ylabel(data.metadata.ylabel)
                
            elif  len(data.metadata.dimension) == 2:
                
                # Split the data into intensity, error and ncount
                Intensity = data.Intensity
                Error = data.Error
                Ncount = data.Ncount
                
                # Select to plot the intensity
                #to_plot = np.log(Intensity)
                
                if self.log[index]:
                    min_value = np.min(Intensity[np.nonzero(Intensity)])
                    min_value = np.log10(min_value)
                    
                    to_plot = np.log10(Intensity)
                    
                    max_value = to_plot.max()
                    
                    if max_value - min_value > self.orders_of_mag[index]:
                        min_value = max_value - self.orders_of_mag[index]
                else:
                    to_plot = Intensity
                    min_value = to_plot.min()
                    max_value = to_plot.max()
                
                # Check the size of the array to be plotted 
                #print(to_plot.shape)
                
                # Set the axis (might be switched?)
                X=np.linspace(data.metadata.limits[0],data.metadata.limits[1],data.metadata.dimension[0]+1)
                Y=np.linspace(data.metadata.limits[2],data.metadata.limits[3],data.metadata.dimension[1])
                
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
                ax0.set_title(data.metadata.title)
                
                # Add axis labels
                plt.xlabel(data.metadata.xlabel)
                plt.ylabel(data.metadata.ylabel)
                
            else:
                print("Error, dimension not read correctly")
            
        plt.show()
        
class make_sub_plot:
    def __init__(self,*args,**kwargs):
        data_list = args[0]
        
        if not isinstance(data_list,mcstas_data):
            print("number of elements in data list = " + str(len(data_list)))
        else:
            # Only a single element, put it in a list for easier syntax later
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
        
        #fig = plt.figure(figsize=(20,10))

        # instead of passing this information here, it should just be a property of the data
        self.log = [False]*number_of_plots
        if "log" in kwargs:
            if isinstance(kwargs["log"],list):
                if not len(kwargs["log"]) == number_of_plots:
                    raise IndexError("Length of list given for log logic does not match number of data elements")
                else:
                    self.log = kwargs["log"]
                    for element in self.log:
                        if not isinstance(element, bool):
                            if not element == 0:
                                element = True 
            elif isinstance(kwargs["log"],bool):
                if kwargs["log"] == True:
                    self.log = [True]*number_of_plots
            elif isinstance(kwargs["log"],int):
                if kwargs["log"] == 1:
                    self.log = [True]*number_of_plots
            else:
                raise NameError("log keyword Argument in make_sub_plot not understood. Needs to be int, [1/0], bool [True/False] or array of same length as data.")
                
        
        self.orders_of_mag=[300] * number_of_plots
        if "max_orders_of_mag" in kwargs:
            if isinstance(kwargs["max_orders_of_mag"],list):
                if not len(kwargs["max_orders_of_mag"]) == number_of_plots:
                    raise IndexError("Length of list given for max_orders_of_mag does not match number of data elements")
                else: 
                    self.orders_of_mag = kwargs["max_orders_of_mag"]
            else:
                if isinstance(kwargs["max_orders_of_mag"],float) or isinstance(kwargs["max_orders_of_mag"],int):
                    self.orders_of_magnitude=[kwargs["max_orders_of_mag"]]*number_of_plots
                else:
                    raise TypeError("max_orders_of_mag need to be of type float or int")
        
        # Find reasonable grid size for the number of plots
        dim2 = math.ceil(math.sqrt(number_of_plots))
        dim1 = math.ceil(number_of_plots/dim2)
          
        fig, axs = plt.subplots(dim1,dim2,figsize=(13,7))
        axs = np.array(axs)
        ax = axs.reshape(-1)
        
        index = -1
        for data in data_list:
            index = index + 1
            ax0 = ax[index]
              
            print("Plotting data with name " + data.metadata.component_name)
            
            if type(data.metadata.dimension) == int:
                #fig = plt.figure(0)
                #plt.subplot(dim1, dim2, n_plot)
                
                #print(data.T)
                x = data.xaxis
                y = data.Intensity
                y_err = data.Error
                
                
                ax0.errorbar(x, y, yerr=y_err)
                
                if self.log[index]:
                    ax0.set_yscale("log",nonposy='clip')
                
                ax0.set_xlim(data.metadata.limits[0],data.metadata.limits[1])
                
                # Add a title
                #ax0.title(data.title)
                
                # Add axis labels
                ax0.set_xlabel(data.metadata.xlabel)
                ax0.set_ylabel(data.metadata.ylabel)
                
            elif  len(data.metadata.dimension) == 2:
                
                # Split the data into intensity, error and ncount
                Intensity = data.Intensity
                Error = data.Error
                Ncount = data.Ncount
                
                # Select to plot the intensity
                #to_plot = np.log(Intensity)
                
                if self.log[index]:
                    min_value = np.min(Intensity[np.nonzero(Intensity)])
                    min_value = np.log10(min_value)
                    
                    #to_plot = np.log10(Intensity)
                    to_plot = Intensity
                    
                    max_value = np.log10(to_plot.max())
                    
                    if max_value - min_value > self.orders_of_mag[index]:
                        min_value = max_value - self.orders_of_mag[index]
                    min_value = 10.0 ** min_value
                    max_value = 10.0 ** max_value
                else:
                    to_plot = Intensity
                    min_value = to_plot.min()
                    max_value = to_plot.max()
                
                # Check the size of the array to be plotted 
                #print(to_plot.shape)
                
                # Set the axis (might be switched?)
                X=np.linspace(data.metadata.limits[0],data.metadata.limits[1],data.metadata.dimension[0]+1)
                Y=np.linspace(data.metadata.limits[2],data.metadata.limits[3],data.metadata.dimension[1])
                
                # Create a meshgrid for both x and y
                y, x = np.meshgrid(Y,X)
                
                
                # Generate information on necessary colorrange
                levels = MaxNLocator(nbins=150).tick_values(min_value, max_value)
                #levels = MaxNLocator(nbins=150).tick_values(to_plot.max()-12, to_plot.max())
                
                # Select colormap
                cmap = plt.get_cmap('jet')
                norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)
                
                # Create the figure
                #fig, (ax0) = plt.subplots()
                
                #fig, ax0 = plt.subplot(dim1, dim2, n_plot)
                
                # Plot the data on the meshgrids
                #im = plt.pcolormesh(x, y, to_plot, cmap=cmap, norm=norm)
                if self.log[index]: 
                    im = ax0.pcolormesh(x, y, to_plot, cmap=cmap, norm=matplotlib.colors.LogNorm(vmin=min_value,vmax=max_value))
                else:
                    im = ax0.pcolormesh(x, y, to_plot, cmap=cmap, norm=norm)
                
                
                def fmt(x, pos):
                    a, b = '{:.2e}'.format(x).split('e')
                    b = int(b)
                    return r'${} \times 10^{{{}}}$'.format(a, b)
                
                # Add the colorbar
                fig.colorbar(im, ax=ax0, format=matplotlib.ticker.FuncFormatter(fmt))
                
                # Add a title
                ax0.set_title(data.metadata.title)
                
                # Add axis labels
                ax0.set_xlabel(data.metadata.xlabel)
                ax0.set_ylabel(data.metadata.ylabel)
                
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
            self.ROTATED_data = kwargs["ROTATED"]
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

        if "WHEN" in kwargs:
            self.WHEN = "WHEN (" + kwargs["WHEN"] + ")\n"
        else:
            self.WHEN = ""
            
        if "EXTEND" in kwargs:
            self.EXTEND = kwargs["EXTEND"]
        else:
            self.EXTEND = ""
            
        if "GROUP" in kwargs:
            self.GROUP = kwargs["GRPUP"]
        else:
            self.GROUP = ""

        if "JUMP" in kwargs:
            self.JUMP = kwargs["JUMP"]
        else:
            self.JUMP = ""

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
        
    def set_WHEN(self,string):
        self.WHEN = string
        
    def set_GROUP(self,string):
        self.GROUP = string
    
    def set_JUMP(self,string):
        self.JUMP = string
        
    def append_EXTEND(self,string):
        self.EXTEND = self.EXTEND + string + "\n"
    
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
                    fo  .write("\n")
            else:
                fo.write(")\n") # end paranthesis after last parameter
                
        # Optional WHEN section
        if not self.WHEN == "":
            fo.write("WHEN(%s)\n" % self.WHEN)
        # Need to add JUMP section here
        
        # write AT and ROTATED section
        fo.write("AT (%s,%s,%s)" % (str(self.AT_data[0]),str(self.AT_data[1]),str(self.AT_data[2])))
        fo.write(" %s\n" % self.AT_relative)
        fo.write("ROTATED (%s,%s,%s)" % (str(self.ROTATED_data[0]),str(self.ROTATED_data[1]),str(self.ROTATED_data[2])))
        fo.write(" %s\n" % self.ROTATED_relative)
        
        if not self.GROUP == "":
            fo.write("GROUP %s\n" % self.GROUP)
        
        # Optional EXTEND section
        if not self.EXTEND == "":
            fo.write("EXTEND %{\n")
            fo.write("%s" % self.EXTEND)
            fo.write("%}\n")
            
        if not self.JUMP == "":
            fo.write("JUMP %s\n" % self.JUMP)
            
        # Leave a new line between components for readability
        fo.write("\n")
            

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
        self.finally_section = "// Start of finally for generated " + name + "\n"
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
        
    def append_finally(self,string):
        self.finally_section = self.finally_section + string + "\n"
    
    def append_finally_no_new_line(self,string):
        self.finally_section = self.finally_section + string
    
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
        
    def set_component_WHEN(self,name,WHEN):
        component = self.get_component(name)
        component.set_WHEN(WHEN)
        
    def append_component_EXTEND(self,name,EXTEND):
        component = self.get_component(name)
        component.append_EXTEND(EXTEND)
        
    def set_component_GROUP(self,name,GROUP):
        component = self.get_component(name)
        component.set_GROUP(GROUP)
        
    def set_component_JUMP(self,name,JUMP):
        component = self.get_component(name)
        component.set_JUMP(JUMP)
    
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
        fo.write("DECLARE \n%{\n")
        for dec_line in self.declare_list:
            dec_line.write_line(fo)
            fo.write("\n")
        fo.write("%}\n\n")

        # Write initialize
        fo.write("INITIALIZE \n%{\n")
        fo.write(self.initialize_section)
        # Alternatively hide everything in include
        # fo.write("%include "generated_includes/" + self.name + "_initialize.c")
        fo.write("%}\n\n")

        # Write trace
        fo.write("TRACE \n")
        for component in self.component_list:
            component.write_component(fo)

        # Write finally
        fo.write("FINALLY \n%{\n")
        fo.write(self.finally_section)
        # Alternatively hide everything in include
        fo.write("%}\n")

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
        
        
        
