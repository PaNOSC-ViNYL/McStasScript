import copy

class DiagnosticsInstrument:
    def __init__(self, instr):
        """
        Diagnostics instrument object with related capabilities

        The diagnostics instrument takes a copy of an instrument object
        and can modify this version in ways relevant for diagnostics of
        the instrument. It can remove use of PREVIOUS and correct the
        use of target_index to make it safe to add additional components
        without altering the instrument. It carries it's own settings
        and parameters that wont impact the original instrument. The
        diagnostics instrument can be reset to the original state, and
        will have settings and parameters applied again.

        Parameters:

        instr : McCode_instr object
            Instrument which needs a diagnostics copy
        """
        self.original_instr = instr
        self.instr = None
        self.instr_settings = {}
        self.instr_parameters = {}
        self.reset_instr()

        self.component_list = self.instr.make_component_subset()

    def reset_instr(self):
        """
        Resets instrument to original state, with new pars and settings
        """
        self.instr = copy.deepcopy(self.original_instr)
        self.instr.settings(**self.instr_settings)
        self.instr.set_parameters(**self.instr_parameters)

    def settings(self, **kwargs):
        """
        Apply settings as in an instrument object
        """
        self.instr.settings(**kwargs)
        self.instr_settings.update(kwargs)

    def show_settings(self):
        """
        Show settings of diagnostics instrument
        """
        self.instr.show_settings()

    def set_parameters(self, **kwargs):
        """
        Set parameters as in instrument object
        """
        self.instr.set_parameters(**kwargs)
        self.instr_parameters.update(kwargs)

    def show_parameters(self):
        """
        Show parameters as on instrument object
        """
        self.instr.show_parameters()

    def remove_previous_use(self):
        """
        Replaces use of PREVIOUS with direct references
        """
        self.component_list = self.instr.make_component_subset()
        previous_component = None
        for comp in self.component_list:
            if comp.AT_reference == "PREVIOUS":
                comp.set_AT_RELATIVE(previous_component)

            if comp.ROTATED_specified:
                if comp.ROTATED_reference == "PREVIOUS":
                    comp.set_ROTATED_RELATIVE(previous_component)

            previous_component = comp

    def correct_target_index(self):
        """
        Corrects target_index based on original instrument
        """
        original_component_list = self.original_instr.make_component_subset()
        original_comp_names = [x.name for x in original_component_list]

        modified_component_list = self.instr.make_component_subset()
        modified_comp_names = [x.name for x in modified_component_list]

        for comp in original_component_list:
            # Find components that use target index

            if not hasattr(comp, "target_index"):
                # Component doesnt have the target_index setting
                continue
            if comp.target_index is None:
                # A value has not been specified for target_index setting
                continue
            if comp.target_index == 0:
                # target_index is disabled
                continue

            # Only here if target_index is used, correct it in modified instr

            # Find original index and the name of the original target
            original_comp_index = original_comp_names.index(comp.name)
            comp_target_name = original_comp_names[original_comp_index + int(comp.target_index)]

            # Find index of the original and target in modified instrument
            modified_comp_index = modified_comp_names.index(comp.name)
            index_of_new_target = modified_comp_names.index(comp_target_name)
            new_target_index = index_of_new_target - modified_comp_index

            # Apply the new target_index to the component in the modified instrument
            modified_comp = self.instr.get_component(comp.name)
            modified_comp.target_index = new_target_index
