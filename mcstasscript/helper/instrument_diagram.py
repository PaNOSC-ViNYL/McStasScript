import matplotlib.pyplot as plt
import numpy as np


def instrument_diagram(instrument):
    """
    Plots diagram of components in instrument with RELATIVE connections

    All components in the instrument are shown as text fields and arrows are
    drawn showing the AT RELATIVE and ROTATED RELATIVE connections between
    components.
    """
    lane_width = 0.033  # spacing between lanes
    margin = 0.01  # Margin on figure at top and bottom

    components = instrument.component_list
    n_components = len(components) + 1
    graph_height = n_components / 2.5

    absolute_box = Component_box(name="ABSOLUTE")
    component_boxes = [absolute_box]
    component_box_dict = {"ABSOLUTE": absolute_box}
    for component in components:
        box = Component_box(component)
        component_boxes.append(box)
        component_box_dict[component.name] = box

    box_height_centers = np.linspace(1-margin, margin, n_components)
    box_height = (1 - 2*margin)/n_components
    for box, y_pos in zip(component_boxes, box_height_centers):
        box.set_y(y_pos)
        box.set_box_height(box_height)

    arrows = []
    box_names = [x.name for x in component_boxes]

    AT_connections = {}
    AT_lane_numbers = {}
    ROTATED_connections = {}
    ROTATED_lane_numbers = {}
    for component in components:
        if component.AT_reference is None:
            origin = component_box_dict[component.name]
            target = absolute_box
        else:
            origin = component_box_dict[component.name]
            target = component_box_dict[component.AT_reference]

        AT_connections[origin] = target

        if not component.ROTATED_specified:
            continue

        if component.ROTATED_reference is None:
            origin = component_box_dict[component.name]
            target = absolute_box
        else:
            origin = component_box_dict[component.name]
            target = component_box_dict[component.ROTATED_reference]

        ROTATED_connections[origin] = target

    # Make arrows for AT connections
    for origin, target in AT_connections.items():
        lane_number = find_lane_number(origin=origin, target=target, box_names=box_names,
                                       connections=AT_connections,
                                       lane_numbers=AT_lane_numbers,
                                       component_box_dict=component_box_dict)

        arrow = Arrow(origin, target)
        arrow.set_lane_width(lane_width)
        arrow.set_box_offset_origin(0.24 * box_height)
        arrow.set_box_offset_target(-0.2 * box_height)
        arrow.set_lane(lane_number)
        #arrow.set_linestyle("--")

        arrows.append(arrow)

    # Make arrows for ROTATED connections
    for origin, target in ROTATED_connections.items():
        lane_number = find_lane_number(origin=origin, target=target, box_names=box_names,
                                       connections=ROTATED_connections,
                                       lane_numbers=ROTATED_lane_numbers,
                                       component_box_dict=component_box_dict)

        arrow = Arrow(origin, target)
        arrow.set_lane_width(lane_width)
        arrow.set_lane_offset(0.4)
        arrow.set_box_offset_origin(0.16 * box_height)
        arrow.set_box_offset_target(-0.05 * box_height)
        arrow.color = "red"
        #arrow.set_linestyle("--")

        arrow.set_lane(lane_number)
        arrows.append(arrow)

    # Infer how wide the figure should be based on number of lanes used
    highest_lane = 0
    for arrow in arrows:
        highest_lane = max(arrow.lane, highest_lane)

    lane_width = highest_lane/3
    lane_width = max(0.6, lane_width)
    name_width = 3  # Reserve space of 3 for component names
    graph_width = lane_width + name_width

    for box in component_boxes:
        box.set_x(lane_width / graph_width)  # Places boxes so they get name_width space

    fig, ax = plt.subplots(figsize=(graph_width, graph_height))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    for box in component_boxes:
        box.plot_box(ax)

    for arrow in arrows:
        arrow.set_arrow_width(0.03/graph_height)
        arrow.plot(ax)

    plt.show()


def find_lane_number(origin, target, box_names, connections, lane_numbers, component_box_dict):
    """
    Helper function for finding how many lanes the current connection should go
    """
    origin_index = box_names.index(origin.name)
    target_index = box_names.index(target.name)
    names_between = box_names[target_index + 1:origin_index]

    max_lane_number = 0
    for name_between in names_between:
        between_object = component_box_dict[name_between]
        if name_between == "ABSOLUTE":
            continue

        if between_object not in connections:
            continue

        if connections[between_object] is target:
            continue

        if lane_numbers[between_object] > max_lane_number:
            max_lane_number = lane_numbers[between_object]

    lane_number = max_lane_number + 1
    lane_numbers[origin] = lane_number
    return lane_number


class Component_box:
    """
    Helper class for creating text boxes
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
        self.position_x = None
        self.position_y = None
        self.box_height = None

    def set_box_height(self, box_height):
        self.box_height = box_height

    def set_x(self, x):
        self.position_x = x

    def set_y(self, y):
        self.position_y = y

    def plot_box(self, ax):
        bbox = dict(boxstyle="round", facecolor="white", edgecolor="black")

        ax.text(self.position_x + 0.03, self.position_y, self.name,
                va="center", fontweight="bold", color="black", bbox=bbox)


class Arrow:
    """
    Helper class for creating arrows with connections
    """
    def __init__(self, origin, target):
        """
        Arrow object with origin Component_box and target component_box
        """
        self.origin = origin
        self.target = target
        self.lane = None
        self.lane_width = None
        self.lane_offset = 0

        self.box_offset_origin = 0
        self.box_offset_target = 0

        self.origin_linestyle = "-"
        self.color = "blue"
        self.arrow_width = 0.003

    def set_lane(self, lane):
        self.lane = lane

    def set_lane_width(self, lane_width):
        self.lane_width = lane_width

    def set_lane_offset(self, offset):
        self.lane_offset = offset*self.lane_width

    def get_lane_value(self):
        return self.lane*self.lane_width + self.lane_offset

    def set_box_offset_origin(self, value):
        self.box_offset_origin = value

    def set_box_offset_target(self, value):
        self.box_offset_target = value

    def set_arrow_width(self, value):
        self.arrow_width = value

    def set_linestyle(self, value):
        self.origin_linestyle = value

    def plot(self, ax):
        origin_x = self.origin.position_x
        origin_y = self.origin.position_y + self.box_offset_origin

        origin_lane_x = origin_x - self.get_lane_value()
        origin_lane_y = origin_y

        ax.plot([origin_x + 0.05, origin_lane_x], [origin_y, origin_lane_y],
                color=self.color, linestyle=self.origin_linestyle)

        target_x = self.target.position_x
        target_y = self.target.position_y + self.box_offset_target

        target_lane_x = target_x - self.get_lane_value()
        target_lane_y = target_y

        ax.plot([origin_lane_x, target_lane_x], [origin_lane_y, target_lane_y], color=self.color)

        ax.arrow(x=target_lane_x, y=target_lane_y,
                 dx=self.get_lane_value() + 0.01, dy=0,
                 color=self.color, length_includes_head=True,
                 width=self.arrow_width)

