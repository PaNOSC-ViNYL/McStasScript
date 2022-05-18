import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import graphviz

def instrument_diagram(instrument):
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

    margin = 0.001
    box_height_centers = np.linspace(1-margin, margin, n_components)
    box_height = (1 - 2*margin)/n_components
    for box, y_pos in zip(component_boxes, box_height_centers):
        box.set_y(y_pos)
        box.set_box_height(box_height)

    for box in component_boxes:
        box.set_x(0.2)

    lane_width = 0.025

    arrows = []
    destinations_AT = set()
    destinations_ROTATED = set()
    box_names = [x.name for x in component_boxes]
    for component in components:
        if component.AT_reference is None:
            origin = component_box_dict[component.name]
            target = absolute_box
        else:
            origin = component_box_dict[component.name]
            target = component_box_dict[component.AT_reference]

        #print(origin.name, "to ", target.name)
        destinations_AT.add(target.name)

        origin_index = box_names.index(origin.name)
        target_index = box_names.index(target.name)
        names_between = box_names[target_index:origin_index]
        #print(origin_index, target_index)
        #print("between: ", names_between)
        unique_destinations_between = destinations_AT.intersection(names_between)
        lane_number = len(unique_destinations_between)
        #print("destinations between: ", unique_destinations_between)

        # Different technique for lane numbers:


        arrow = Arrow(origin, target)
        arrow.set_lane_width(lane_width)
        arrow.set_box_offset_origin(0.24*box_height)
        arrow.set_box_offset_target(-0.2 * box_height)
        arrow.set_lane(lane_number)

        arrows.append(arrow)
        #print()

        if not component.ROTATED_specified:
            continue

        if component.ROTATED_reference is None:
            origin = component_box_dict[component.name]
            target = absolute_box
        else:
            origin = component_box_dict[component.name]
            target = component_box_dict[component.ROTATED_reference]

        destinations_ROTATED.add(target.name)

        origin_index = box_names.index(origin.name)
        target_index = box_names.index(target.name)
        names_between = box_names[target_index:origin_index]
        unique_destinations_between = destinations_ROTATED.intersection(names_between)

        arrow = Arrow(origin, target)
        arrow.set_lane_width(lane_width)
        arrow.set_lane_offset(0.5)
        arrow.set_box_offset_origin(0.16 * box_height)
        arrow.set_box_offset_target(-0.05 * box_height)
        arrow.color = "red"
        arrow.set_lane(len(unique_destinations_between))
        arrows.append(arrow)

    fig, ax = plt.subplots(figsize=(5, graph_height))
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    for box in component_boxes:
        box.plot_box(ax)

    for arrow in arrows:
        arrow.set_arrow_width(0.03/graph_height)
        arrow.plot(ax)

    plt.show()


class Component_box:
    def __init__(self, component_object=None, name=None):
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

    def get_origin_x(self):
        return self.position_x

    def get_origin_y(self):
        return self.position_y + 0.2 * self.box_height

    def get_target_x(self):
        return self.position_x

    def get_target_y(self):
        return self.position_y - 0.15 * self.box_height

    def plot_box(self, ax):
        bbox = dict(boxstyle="round", facecolor="white", edgecolor="black")

        ax.text(self.position_x + 0.03, self.position_y, self.name,
                va="center", fontweight="bold", color="black", bbox=bbox)


class Arrow:
    def __init__(self, origin, target):
        self.origin = origin
        self.target = target
        self.lane = None
        self.lane_width = None
        self.color = "blue"
        self.lane_offset = 0

        self.box_offset_origin = 0
        self.box_offset_target = 0
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

    def plot(self, ax):
        origin_x = self.origin.position_x
        origin_y = self.origin.position_y + self.box_offset_origin

        origin_lane_x = origin_x - self.get_lane_value()
        origin_lane_y = origin_y

        ax.plot([origin_x + 0.05, origin_lane_x], [origin_y, origin_lane_y], color=self.color)

        target_x = self.target.position_x
        target_y = self.target.position_y + self.box_offset_target

        target_lane_x = target_x - self.get_lane_value()
        target_lane_y = target_y

        ax.plot([origin_lane_x, target_lane_x], [origin_lane_y, target_lane_y], color=self.color)

        ax.arrow(x=target_lane_x, y=target_lane_y,
                 dx=self.get_lane_value() + 0.01, dy=0,
                 color=self.color, length_includes_head=True,
                 width=self.arrow_width)


def instrument_diagram_gv(instrument):
    dot = graphviz.Digraph('instrument_layout', comment='Connections in instrument', filename="test.gv")

    components = instrument.component_list

    dot.node("ABSOLUTE")
    for component in components:
        dot.node(component.name)

    print(dot.source)

    for component in components:
        if component.AT_reference is None:
            dot.edge(component.name, "ABSOLUTE", constraint=False)
        else:
            dot.edge(component.name, component.AT_reference, constraint=False)

    print(dot.source)

    dot.view()
