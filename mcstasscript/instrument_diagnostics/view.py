class View:
    def __init__(self, axis1, axis2=None, bins=100, same_scale=False,
                 axis1_values=None, axis2_values=None, **kwargs):
        """
        Plot view on one or two axis to be generated from event data

        The possible specifiers are defined in McStasEvenData and are
        x : x position [m]
        y : x position [m]
        z : x position [m]
        vx : x velocity [m/s]
        vy : x velocity [m/s]
        vz : x velocity [m/s]
        speed : [m/s]
        dx : divergence x [deg]
        dy : divergence y [deg]
        t : time [s]
        l : wavelength [AA]
        e : energy [meV]

        Parameters:

        axis1 : str
            Specifier for first axis to be shown

        axis2 : str (optional)
            Specifier for second axis to be shown

        bins : int or [int, int]
            Number of bins for generation of histogram

        axis1_values : float or list of floats
            Values that will be plotted as lines on plot

        axis2_values : float or list of floats
            Values that will be plotted as lines on plot

        same_scale : bool
            Controls whether all displays of this view is on same ranges
        """
        self.same_scale = same_scale

        self.axis1 = axis1
        self.axis1_limits = None

        if isinstance(axis1_values, (float, int)):
            axis1_values = [axis1_values]
        self.axis1_values = axis1_values

        self.axis2 = axis2
        self.axis2_limits = None
        if isinstance(axis2_values, (float, int)):
            axis2_values = [axis2_values]
        self.axis2_values = axis2_values

        self.bins = bins

        self.plot_options = kwargs

    def __repr__(self):
        string = f"View ({self.axis1}"
        if self.axis2 is not None:
            string += f", {self.axis2}"

        string += ")"
        string = string.ljust(25)
        string += f" bins: {str(self.bins)}"

        return string

    def set_axis1_limits(self, start, end):
        """
        Sets the axis1 limits
        """
        if start > end:
            raise ValueError("Start point over end for this view.")

        self.axis1_limits = start, end

    def set_axis2_limits(self, start, end):
        """
        Sets the axis2 limits
        """
        if start > end:
            raise ValueError("Start point over end for this view.")

        self.axis2_limits = start, end

    def clear_limits(self):
        """
        Clears all limits
        """
        self.axis1_limits = None
        self.axis2_limits = None