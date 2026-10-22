import pickle


class CustomMcStasUnpickler(pickle.Unpickler):
    """
    Helps pickle find dynamic classes on users computer, McStas version

    Usage:
    pickle_data = CustomUnpickler(open('filename.dill', 'rb')).load()
    """

    def find_class(self, module, name):
        if not hasattr(self, "mcstasscript_instr"):
            from mcstasscript.interface import instr

            self.mcstasscript_instr = instr.McStas_instr("dummy")
            self.component_list = list(self.mcstasscript_instr.component_reader.component_category.keys())

        if str(module) == 'mcstasscript.interface.instr':
            if name in self.component_list:
                self.mcstasscript_instr._create_component_instance("dummy", name)

        return super().find_class(module, name)


class CustomMcXtraceUnpickler(pickle.Unpickler):
    """
    Helps pickle find dynamic classes on users computer, McXtrace version

    Usage:
    pickle_data = CustomUnpickler(open('filename.dill', 'rb')).load()
    """

    def find_class(self, module, name):
        if not hasattr(self, "mcstasscript_instr"):
            from mcstasscript.interface import instr

            self.mcstasscript_instr = instr.McXtrace_instr("dummy")
            self.component_list = list(self.mcstasscript_instr.component_reader.component_category.keys())

        if str(module) == 'mcstasscript.interface.instr':
            if name in self.component_list:
                self.mcstasscript_instr._create_component_instance("dummy", name)

        return super().find_class(module, name)


