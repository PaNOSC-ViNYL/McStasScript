class View:
    def __init__(self, axis1, axis2=None, bins=100, same_scale=True, **kwargs):
        self.same_scale = same_scale

        self.axis1 = axis1
        self.axis1_limits = None

        self.axis2 = axis2
        self.axis2_limits = None

        self.bins = bins

        self.plot_options = kwargs

    def set_axis1_limits(self, start, end):
        if start > end:
            raise ValueError("Start point over end for this view.")

        self.axis1_limits = start, end

    def set_axis2_limits(self, start, end):
        if start > end:
            raise ValueError("Start point over end for this view.")

        self.axis2_limits = start, end

    def clear_limits(self):
        self.axis1_limits = None
        self.axis2_limits = None