import matplotlib.pyplot as plt


class ComponentBox:
    """
    Helper class for creating text boxes describing components
    """
    def __init__(self, component_object=None, name=None):
        """
        Text box object
        """
        self.component_object = component_object
        if component_object is None:
            self.name = name
        else:
            self.name = self.component_object.name

        # Produced weighted length of name, capital letters count for 1.2
        self.weighted_name_length = len(self.name) + 0.2*sum(1 for c in self.name if c.isupper())

        self.position_x = None
        self.position_y = None
        self.box_height = None
        self.box_indent = None
        self.background_color = "white"

        self.t = None # text object
        self.graph_box_end = None # graph position where text ends
        self.graph_box_start = None  # graph position where text ends

    def set_box_height(self, box_height):
        self.box_height = box_height

    def set_x(self, x):
        self.position_x = x

    def set_y(self, y):
        self.position_y = y

    def set_box_indent(self, value):
        self.box_indent = value

    def set_background_color(self, value):
        self.background_color = value

    def plot_box(self, ax):
        bbox = dict(boxstyle="round", facecolor=self.background_color, edgecolor="black")

        self.t = ax.text(self.position_x + self.box_indent, self.position_y, self.name,
                         va="center", fontweight="semibold", color="black", #font="monospace",
                         bbox=bbox)

    def get_text_start(self):
        return self.graph_box_start

    def get_text_end(self):
        return self.graph_box_end

    def calculate_bbox_dimensions(self, ax, graph_width):
        """
        Method that gets dimensions of plotted text box
        """
        transf = ax.transAxes.inverted()
        bb = self.t.get_window_extent(renderer=plt.gcf().canvas.get_renderer())
        bbox = bb.transformed(transf)

        TEXT_PADDING_IN_FIG_UNITS = 0.08
        box_padding = TEXT_PADDING_IN_FIG_UNITS / graph_width
        self.graph_box_start = bbox.x0 - box_padding
        self.graph_box_end = bbox.x1 + box_padding