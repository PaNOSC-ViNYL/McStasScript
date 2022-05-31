import matplotlib.pyplot as plt
import numpy as np
import copy

from libpyvinyl.Parameters.Parameter import Parameter
from mcstasscript.helper.mcstas_objects import DeclareVariable


def instrument_diagram(instrument):
    """
    Plots diagram of components in instrument with RELATIVE connections

    All components in the instrument are shown as text fields and arrows are
    drawn showing the AT RELATIVE and ROTATED RELATIVE connections between
    components. When more advanced features are used, these are displayed
    with arrows on the right side of the diagram, currently JUMP, GROUP and
    use of Union components are visualized.

    Parameters
    ----------

    instrument : McCode_instr
        Instrument object from which the component list is taken
    """

    # Grab components from instrument file and make text box objects
    components = instrument.component_list

    # Prepare legend
    component_reader = instrument.component_reader
    component_categories = copy.deepcopy(component_reader.component_category)

    absolute_box = ComponentBox(name="ABSOLUTE")
    component_boxes = [absolute_box]
    component_box_dict = {"ABSOLUTE": absolute_box}
    for component in components:
        box = ComponentBox(component)
        component_boxes.append(box)
        component_box_dict[component.name] = box

    box_names = [x.name for x in component_boxes]

    color_choices = {"AT": "blue", "ROTATED": "red", "JUMP": "black", "GROUP": [0.4, 0.4, 0.4], "Union": "green"}

    # Arrows for the left side of the diagram
    AT_arrows = generate_AT_arrows(components, component_box_dict, box_names, color=color_choices["AT"])
    ROTATED_arrows = generate_ROTATED_arrows(components, component_box_dict, box_names, color=color_choices["ROTATED"])

    # Arrow for the right side of the diagram
    JUMP_arrows = generate_JUMP_arrows(components, component_box_dict, box_names, color=color_choices["JUMP"])
    GROUP_arrows = generate_GROUP_arrows(components, component_box_dict, box_names, color=color_choices["GROUP"])
    Union_arrows = generate_Union_arrows(components, component_box_dict, box_names,
                                         component_categories, color=color_choices["Union"])

    # Create canvas
    canvas = DiagramCanvas(AT_arrows + ROTATED_arrows, component_boxes, JUMP_arrows + GROUP_arrows + Union_arrows,
                           component_categories=component_categories, colors=color_choices)

    # Plot diagram
    canvas.plot()


def generate_GROUP_arrows(components, component_box_dict, box_names, existing_lane_numbers=None, color=None):
    """
    Generate Arrow objects related to the GROUP keyword
    """
    connections = {}
    if existing_lane_numbers is None:
        lane_numbers = {}
    else:
        lane_numbers = existing_lane_numbers

    groups = {}
    for component in components:
        if component.GROUP != "":
            group_reference = component.GROUP
            if group_reference not in groups:
                groups[group_reference] = [component_box_dict[component.name]]
            else:
                groups[group_reference].append(component_box_dict[component.name])

    for group_name, group_members in groups.items():
        if len(group_members) == 1:
            # Meaningless group
            continue
        base = group_members[0]
        connected_list = group_members[1:]

        for connected in connected_list:
            connections[connected] = base

    arrows = []
    """
    Reverse connections because group arrows are ordered from last elements to first, as the first encountered
    element is considered the base for the group that all the others point to.
    """
    for origin, target in reversed(connections.items()):
        lane_number = find_lane_number(origin=origin, target=target, box_names=box_names,
                                       connections=connections, lane_numbers=lane_numbers,
                                       component_box_dict=component_box_dict)

        group_name = origin.component_object.GROUP

        arrow = Arrow(origin, target, kind="GROUP", description=group_name)
        arrow.set_connection(True)
        if color is None:
            arrow.color = [0.4, 0.4, 0.4]
        else:
            arrow.color = color
        arrow.set_lane(lane_number + 2) # Leave name for JUMP description

        arrows.append(arrow)

        if existing_lane_numbers is not None:
            existing_lane_numbers = lane_numbers

    return arrows


def generate_JUMP_arrows(components, component_box_dict, box_names, existing_lane_numbers=None, color=None):
    """
    Generate Arrow objects related to the JUMP keyword
    """
    connections = {}
    if existing_lane_numbers is None:
        lane_numbers = {}
    else:
        lane_numbers = existing_lane_numbers

    for component in components:
        if component.JUMP != "":
            jump_reference = component.JUMP.split(" ")[0]
            if jump_reference not in component_box_dict:
                raise ValueError("JUMP reference: " + str(jump_reference)
                                 + " not found.")

            origin = component_box_dict[component.name]
            connections[origin] = component_box_dict[jump_reference]

    arrows = []
    for origin, target in connections.items():
        lane_number = find_lane_number(origin=origin, target=target, box_names=box_names,
                                       connections=connections, lane_numbers=lane_numbers,
                                       component_box_dict=component_box_dict)

        arrow = Arrow(origin, target, kind="JUMP", description="JUMP")
        arrow.set_sub_lane(1)
        if color is None:
            arrow.color = "black"
        else:
            arrow.color = color
        arrow.set_lane(lane_number + 2)  # Leave name for JUMP description

        arrows.append(arrow)

        if existing_lane_numbers is not None:
            existing_lane_numbers = lane_numbers

    return arrows


def generate_Union_arrows(components, component_box_dict, box_names, component_categories,
                          existing_lane_numbers=None, color=None):
    """
    Generate Arrow objects related to use of Union components

    Currently supports processes, materials, geometries and master. Can be
    expanded to also support loggers, abs_loggers and conditionals.
    """
    connections = {}
    if existing_lane_numbers is None:
        lane_numbers = {}
    else:
        lane_numbers = existing_lane_numbers

    process_names = []
    material_names = []
    geometry_names = []
    master_names = []
    geometry_activation_counters = {}
    for component in components:
        category = component_categories[component.component_name]
        if category == "union" or True:
            if "_process" in component.component_name:
                # Process component
                process_names.append(component.name)

            elif component.component_name == "Union_make_material":
                # Make material component
                material_names.append(component.name)

                process_string = component.process_string
                processes = process_string.strip('"').split(",")
                for process in processes:
                    if process not in process_names:
                        print("Didn't find process of name '" + process + "'")
                        print(process_names)
                    else:
                        origin = component_box_dict[process]
                        connections[origin] = component_box_dict[component.name]

            elif "material_string" in component.parameter_names:
                # Geometry
                geometry_names.append(component.name)

                material = component.material_string.strip('"')
                if material not in material_names:
                    print("Didn't find material of name '" + material + "'")
                    print(material_names)
                else:
                    origin = component_box_dict[material]
                    connections[origin] = component_box_dict[component.name]

                if component.number_of_activations is not None:
                    number_of_activations = component.number_of_activations
                else:
                    number_of_activations = component.parameter_defaults["number_of_activations"]

                geometry_activation_counters[component.name] = number_of_activations

            elif "_abs_logger" in component.parameter_names:
                # Abs logger
                pass

            elif "_logger" in component.parameter_names:
                # Logger
                pass

            elif "target_loggers" in component.parameter_names:
                # Conditional
                pass

            elif component.component_name == "Union_master":
                # Master
                master_names.append(component.name)

                for geometry in geometry_names:
                    if geometry_activation_counters[geometry] > 0:  # May need to account for floating point precision
                        # Only include if activation counter for this geometry is still positive
                        geometry_activation_counters[geometry] -= 1

                        origin = component_box_dict[geometry]
                        connections[origin] = component_box_dict[component.name]

    arrows = []
    for origin, target in connections.items():
        lane_number = find_lane_number(origin=origin, target=target, box_names=box_names,
                                       connections=connections, lane_numbers=lane_numbers,
                                       component_box_dict=component_box_dict)

        arrow = Arrow(origin, target, kind="Union")
        arrow.set_sub_lane(2)
        arrow.set_lane(lane_number)

        if color is None:
            arrow.color = "green"
        else:
            arrow.color = color

        if target.name in master_names:
            arrow.set_linestyle("--")

        arrows.append(arrow)

        if existing_lane_numbers is not None:
            existing_lane_numbers = lane_numbers

    return arrows


def generate_AT_arrows(components, component_box_dict, box_names, color=None):
    """
    Generate Arrow objects related to the AT relationship of components
    """
    connections = {}
    lane_numbers = {}
    for component in components:
        origin = component_box_dict[component.name]
        if component.AT_reference is None:
            target = component_box_dict["ABSOLUTE"]
        elif component.AT_reference == "PREVIOUS":
            origin_index = box_names.index(component.name)
            target_index = origin_index - 1
            target = component_box_dict[box_names[target_index]]
        else:
            target = component_box_dict[component.AT_reference]

        connections[origin] = target

    arrows = []
    # Make arrows for AT connections
    for origin, target in connections.items():
        lane_number = find_lane_number(origin=origin, target=target, box_names=box_names,
                                       connections=connections, lane_numbers=lane_numbers,
                                       component_box_dict=component_box_dict)

        arrow = Arrow(origin, target, kind="AT")
        arrow.set_box_offset_origin(0.24)
        arrow.set_box_offset_target(-0.2)
        if color is None:
            arrow.color = "blue"
        else:
            arrow.color = color
        arrow.set_lane(lane_number)
        # arrow.set_linestyle("--")

        arrows.append(arrow)

    return arrows


def generate_ROTATED_arrows(components, component_box_dict, box_names, color=None):
    """
    Generate Arrow objects related to the ROTATED relationship of components
    """
    connections = {}
    lane_numbers = {}
    for component in components:
        if not component.ROTATED_specified:
            continue

        if component.ROTATED_reference is None:
            origin = component_box_dict[component.name]
            target = component_box_dict["ABSOLUTE"]
        elif component.ROTATED_reference == "PREVIOUS":
            origin_index = box_names.index(component.name)
            target_index = origin_index - 1
            target = component_box_dict[box_names[target_index]]
        else:
            origin = component_box_dict[component.name]
            target = component_box_dict[component.ROTATED_reference]

        connections[origin] = target

    arrows = []
    # Make arrows for ROTATED connections
    for origin, target in connections.items():
        lane_number = find_lane_number(origin=origin, target=target, box_names=box_names,
                                       connections=connections, lane_numbers=lane_numbers,
                                       component_box_dict=component_box_dict)

        arrow = Arrow(origin, target, kind="ROTATED")
        arrow.set_lane_offset(0.2)
        arrow.set_box_offset_origin(0.16)
        arrow.set_box_offset_target(-0.05)
        if color is None:
            arrow.color = "red"
        else:
            arrow.color = color

        arrow.set_sub_lane(1)
        arrow.set_lane(lane_number)
        arrows.append(arrow)

    return arrows


def find_lane_number(origin, target, box_names, connections, lane_numbers, component_box_dict):
    """
    Helper function for finding how many lanes the current connection should go out
    """
    origin_index = box_names.index(origin.name)
    target_index = box_names.index(target.name)
    if origin_index < target_index + 1:
        names_between = box_names[origin_index + 1: target_index]
    else:
        names_between = box_names[target_index + 1:origin_index]

    if origin.name == "Cu":
        debug_mode = True
    else:
        debug_mode = False

    max_lane_number = 0
    for name_between in names_between:
        between_object = component_box_dict[name_between]
        if name_between == "ABSOLUTE":
            continue

        if between_object not in connections and between_object not in connections.values():
            continue

        if between_object in connections:
            if connections[between_object] is target:
                continue

        if between_object not in lane_numbers:
            continue

        if lane_numbers[between_object] > max_lane_number:
            max_lane_number = lane_numbers[between_object]

    lane_number = max_lane_number + 1
    lane_numbers[origin] = lane_number
    lane_numbers[target] = lane_number

    return lane_number


class DiagramCanvas:
    def __init__(self, left_side_arrows, component_boxes, right_side_arrows, component_categories, colors):
        """
        Creates diagram of instrument file with given boxes and arrows

        Makes diagram with column of boxes with arrows between them. The boxes
        are described by the ComponentBox class and arrows by Arrow class. Some
        arrows are drawn on the left side, AT and ROTATED relationships, while
        more advanced connections are on the right side. A legend is provided
        where the colors corresponding to component categories are shown along
        with the arrow colors used for different features. The right side
        arrows only show up in the legend when in use to reduce clutter. When
        using this diagram in matplotlib widget mode, it is possible get more
        information on each component by hovering the mouse of the beginning
        the component box.
        """
        self.left_side_arrows = left_side_arrows
        self.component_boxes = component_boxes
        self.right_side_arrows = right_side_arrows
        self.all_arrows = left_side_arrows + right_side_arrows
        self.component_categories = component_categories
        self.colors = colors

        # Identify cases where multiple written input goes to or from same box
        arrow_connections = {}
        for arrow in self.right_side_arrows:
            if arrow.origin not in arrow_connections:
                arrow_connections[arrow.origin] = 1
            else:
                arrow_connections[arrow.origin] += 1

            if arrow.target not in arrow_connections:
                arrow_connections[arrow.target] = 1
            else:
                arrow_connections[arrow.target] += 1

        for key in arrow_connections:
            if arrow_connections[key] > 1:
                displacements = list(np.linspace(-0.16, 0.16, arrow_connections[key]))
                over_populated_box = key
                for arrow in self.right_side_arrows:
                    if arrow.origin is over_populated_box:
                        arrow.set_origin_congested(True)
                        if not arrow.connection:
                            arrow.set_box_offset_origin(displacements.pop())

                    if arrow.target is over_populated_box:
                        arrow.set_target_congested(True)
                        if not arrow.connection:
                            arrow.set_box_offset_target(displacements.pop())

        # Style constants
        self.FIG_HEIGHT_PER_BOX = 0.4
        self.FIG_WIDTH_PER_LANE = 0.33
        self.FIG_WIDTH_PER_WEIGHTED_CHARACTER = 0.122
        self.FIG_EXTRA_WIDTH_FOR_TEXT = 0.15
        self.FIG_LEFT_MARGIN = self.FIG_WIDTH_PER_LANE * 0.5
        self.FIG_RIGHT_MARGIN = self.FIG_WIDTH_PER_LANE * 0.5
        self.FIG_LEGEND_HEADLINE = 0.2
        self.FIG_RIGHT_SIDE_MINIMUM_SPACE = 3

        self.graph_height = self.FIG_HEIGHT_PER_BOX * len(component_boxes)

        # Distribute boxes over graph height
        margin = 0.5/len(component_boxes)
        box_height_centers = np.linspace(1 - margin, margin, len(component_boxes))
        box_height = (1 - 2 * margin) / len(component_boxes)
        for box, y_pos in zip(component_boxes, box_height_centers):
            box.set_y(y_pos)
            box.set_box_height(box_height)

        lane_numbers = [x.lane for x in left_side_arrows] + [0]
        self.highest_lane_left = max(lane_numbers)

        lane_numbers = [x.lane for x in right_side_arrows] + [0]
        self.highest_lane_right = max(lane_numbers)

        weighted_box_names = [x.weighted_name_length for x in component_boxes]
        self.characters_in_longest_name = max(weighted_box_names)

        self.left_space = self.highest_lane_left * self.FIG_WIDTH_PER_LANE
        self.box_space = self.characters_in_longest_name * self.FIG_WIDTH_PER_WEIGHTED_CHARACTER + self.FIG_EXTRA_WIDTH_FOR_TEXT
        self.right_space = self.highest_lane_right * self.FIG_WIDTH_PER_LANE

        self.right_space = max(self.right_space, self.FIG_RIGHT_SIDE_MINIMUM_SPACE)

        self.graph_width = self.FIG_LEFT_MARGIN + self.left_space + self.box_space + self.right_space + self.FIG_RIGHT_MARGIN

        self.text_start_graph = (self.FIG_LEFT_MARGIN + self.left_space) / self.graph_width
        self.text_end_graph = (self.FIG_LEFT_MARGIN + self.left_space + self.box_space) / self.graph_width

        lane_width = self.left_space/self.graph_width/self.highest_lane_left

        # Rescale all
        for arrow in self.all_arrows:
            arrow.set_lane_width(lane_width)
            arrow.set_lane_offset(0.18)
            arrow.set_arrow_width(0.02 / self.graph_height)

        for box in self.component_boxes:
            box.set_box_indent(self.FIG_EXTRA_WIDTH_FOR_TEXT/self.graph_width)
            box.set_x(self.text_start_graph)  # Places boxes so they get name_width space

        # Prepare legend
        all_categories = list(set(component_categories.values()))
        all_categories.sort()

        # Colors from http://vrl.cs.brown.edu/color
        category_colors = ["#7487fb", "#81cc4c", "#e586fe", "#fe707d",
                           "#00d618", "#ffa300", "#cc9966", "#53c6ef",
                           "#baa3c6", "#aebf8a"]

        needed_colors = category_colors[:len(all_categories)]
        self.category_color_dict = dict(zip(all_categories, needed_colors))

        active_categories = []
        for box in self.component_boxes:
            if box.component_object is None:
                continue

            category = component_categories[box.component_object.component_name]
            if category not in active_categories:
                active_categories.append(category)

        self.legend_height = self.FIG_LEGEND_HEADLINE + self.FIG_HEIGHT_PER_BOX * (len(all_categories) // 2)

        self.make_legend()

    def make_legend(self):

        box_top = 1 - self.FIG_LEGEND_HEADLINE / self.legend_height

        fig, ax = plt.subplots(figsize=(7.0, self.legend_height))
        ax.set(xlim=(0, 1), ylim=(0, 1))
        ax.axis("off")

        bbox = dict(boxstyle="round", facecolor="white", edgecolor="white")

        ax.text(0.37, 1.05, "Legend", va="center", ha="center", fontweight="semibold", bbox=bbox, fontsize="large")

        legend_boxes = [ComponentBox(name="Arm")]
        for category, color in self.category_color_dict.items():
            box = ComponentBox(name=category)
            box.set_background_color(color)
            legend_boxes.append(box)

        # Color components boxes after same color scheme
        for box in self.component_boxes:
            if box.component_object is None:
                continue

            component_type = box.component_object.component_name
            if component_type == "Arm":
                box.set_background_color("white")
            else:
                component_category = self.component_categories[component_type]
                box.set_background_color(self.category_color_dict[component_category])

        batch_cut = len(legend_boxes) // 2
        batches = [legend_boxes[:batch_cut], legend_boxes[batch_cut:]]

        batch_end = 0.0
        for batch in batches:
            margin = 0.5 / len(batch)
            box_height_centers = np.linspace(box_top, margin, len(batch))
            box_height = (1 - 2 * margin) / len(batch)
            for box, y_pos in zip(batch, box_height_centers):
                box.set_x(batch_end)
                box.set_y(y_pos)
                box.set_box_height(box_height)
                box.set_box_indent(self.FIG_EXTRA_WIDTH_FOR_TEXT / self.graph_width)

                box.plot_box(ax)

            fig.canvas.draw()
            for box in batch:
                box.calculate_bbox_dimensions(ax, self.graph_width)

            box_ends = [x.graph_box_end for x in batch]
            batch_end = max(box_ends)

        # Always show AT and RELATIVE, but the others only when present
        show_GROUP = False
        show_JUMP = False
        show_Union = False
        for arrow in self.all_arrows:
            if arrow.kind == "GROUP":
                show_GROUP = True
            if arrow.kind == "JUMP":
                show_JUMP = True
            if arrow.kind == "Union":
                show_Union = True

        arrow_width = 0.012
        AT_HEIGHT = 0.83
        START_WIDTH = 0.45
        TEXT_WIDTH_INDENT = 0.01
        DISPLACEMENT = 0.2
        TEXT_DISPLACEMENT = 0.08
        LINE_LENGTH = 0.33

        current_displacement = 0
        ax.arrow(x=START_WIDTH, y=AT_HEIGHT + current_displacement, dx=LINE_LENGTH, dy=0, color=self.colors["AT"],
                 length_includes_head=True, width=arrow_width,
                 head_width=5.0 * arrow_width, head_length=2.5 * arrow_width)
        ax.text(START_WIDTH+TEXT_WIDTH_INDENT, AT_HEIGHT + TEXT_DISPLACEMENT + current_displacement,
                "RELATIVE AT", va="center", weight="semibold")

        current_displacement -= DISPLACEMENT
        ax.arrow(x=START_WIDTH, y=AT_HEIGHT+current_displacement, dx=LINE_LENGTH, dy=0, color=self.colors["ROTATED"],
                 length_includes_head=True, width=arrow_width,
                 head_width=5.0 * arrow_width, head_length=2.5 * arrow_width)
        ax.text(START_WIDTH + TEXT_WIDTH_INDENT, AT_HEIGHT + current_displacement + TEXT_DISPLACEMENT,
                "RELATIVE ROTATED", va="center", weight="semibold")

        if show_Union:
            current_displacement -= DISPLACEMENT
            ax.arrow(x=START_WIDTH, y=AT_HEIGHT + current_displacement, dx=LINE_LENGTH, dy=0,
                     color=self.colors["Union"], length_includes_head=True, width=arrow_width,
                     head_width=5.0 * arrow_width, head_length=2.5 * arrow_width)
            ax.text(START_WIDTH + TEXT_WIDTH_INDENT, AT_HEIGHT + current_displacement + TEXT_DISPLACEMENT,
                    "Union", va="center", weight="semibold")

        if show_JUMP:
            current_displacement -= DISPLACEMENT
            ax.arrow(x=START_WIDTH, y=AT_HEIGHT+current_displacement, dx=LINE_LENGTH, dy=0,
                     color=self.colors["JUMP"], length_includes_head=True, width=arrow_width,
                     head_width=5.0 * arrow_width, head_length=2.5 * arrow_width)
            ax.text(START_WIDTH + TEXT_WIDTH_INDENT, AT_HEIGHT+current_displacement+TEXT_DISPLACEMENT,
                    "JUMP", va="center", weight="semibold")

        if show_GROUP:
            current_displacement -= DISPLACEMENT
            ax.plot([START_WIDTH, START_WIDTH+LINE_LENGTH], 2*[AT_HEIGHT + current_displacement],
                    color=self.colors["GROUP"])
            ax.text(START_WIDTH + TEXT_WIDTH_INDENT, AT_HEIGHT + current_displacement + TEXT_DISPLACEMENT,
                    "GROUP", va="center", weight="semibold")

    def plot(self):
        fig, ax = plt.subplots(figsize=(self.graph_width, self.graph_height))
        ax.set(xlim=(0, 1), ylim=(0, 1))
        ax.axis("off")

        # Start by placing scatter points corresponding to the start of each box
        box_x = []
        box_y = []
        box_info = []
        for box in self.component_boxes:
            box_x.append(box.position_x + box.box_indent)
            box_y.append(box.position_y)
            if box.component_object is None:
                info = box.name
            else:
                info = component_description(box.component_object)
            box_info.append(info)

        # These scatter points will be the basis for mouse hovering showing annotations
        sc = ax.scatter(box_x, box_y, color="white")

        # Plot all the boxes
        for box in self.component_boxes:
            box.plot_box(ax)

        fig.canvas.draw()
        for box in self.component_boxes:
            # Calculate the box end position, requires they are already drawn
            box.calculate_bbox_dimensions(ax, self.graph_width)

        for arrow in self.left_side_arrows:
            # Plot arrows on left side
            arrow.plot_left_side(ax)

        for arrow in self.right_side_arrows:
            # Plot arrows on right side
            arrow.plot_right_side(ax, self.text_end_graph)

        # Create anotation box that will be shown when hovering the mouse over a box
        annot = ax.annotate("", xy=(0, 0), xytext=(20, 10), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"), annotation_clip=False)
        annot.set_visible(False)

        # Helper function to update the anotation box with correct text
        def update_annot(ind):
            pos = sc.get_offsets()[ind["ind"][0]]
            annot.xy = pos
            text = "{}".format(" ".join([box_info[n] for n in ind["ind"]]))
            annot.set_text(text)
            annot.get_bbox_patch().set_facecolor([0.95, 0.95, 0.95])

        # Helper function to detect hovering and update annotation accordingly
        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                cont, ind = sc.contains(event)
                if cont:
                    update_annot(ind)
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                else:
                    if vis:
                        annot.set_visible(False)
                        fig.canvas.draw_idle()

        # Connect the hover function to the canvas event signal
        fig.canvas.mpl_connect("motion_notify_event", hover)

        # Show the figure
        plt.show()


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


class Arrow:
    """
    Helper class for creating arrows with connections
    """
    def __init__(self, origin, target, kind=None, description=None):
        """
        Arrow object with origin Component_box and target component_box
        """
        self.origin = origin
        self.target = target
        self.kind = kind
        self.description=description

        self.lane = None
        self.sub_lane = 0
        self.lane_width = None
        self.lane_offset = 0

        self.box_offset_origin = 0
        self.box_offset_target = 0

        self.origin_linestyle = "-"
        self.color = "blue"
        self.arrow_width = 0.003
        self.connection = False

        self.origin_congested = False
        self.target_congested = False

    def set_lane(self, lane):
        self.lane = lane

    def set_sub_lane(self, lane):
        self.sub_lane = lane

    def set_lane_width(self, lane_width):
        self.lane_width = lane_width

    def set_lane_offset(self, offset):
        self.lane_offset = offset

    def get_lane_value(self):
        return self.lane_width * (self.lane + self.sub_lane * self.lane_offset)

    def set_connection(self, value):
        self.connection = value

    def set_origin_congested(self, value):
        self.origin_congested = value

    def set_target_congested(self, value):
        self.target_congested = value

    def set_box_offset_origin(self, value):
        """
        In units of box height
        """
        self.box_offset_origin = value

    def get_box_offset_origin(self):
        return self.origin.box_height * self.box_offset_origin

    def set_box_offset_target(self, value):
        """
        In units of box height
        """
        self.box_offset_target = value

    def get_box_offset_target(self):
        return self.target.box_height * self.box_offset_target

    def set_arrow_width(self, value):
        self.arrow_width = value

    def set_linestyle(self, value):
        self.origin_linestyle = value

    def plot_left_side(self, ax):
        origin_x = self.origin.get_text_start()
        origin_y = self.origin.position_y + self.get_box_offset_origin()

        origin_lane_x = origin_x - self.get_lane_value()
        origin_lane_y = origin_y

        ax.plot([origin_x, origin_lane_x], [origin_y, origin_lane_y],
                color=self.color, linestyle=self.origin_linestyle)

        target_x = self.target.get_text_start()
        target_y = self.target.position_y + self.get_box_offset_target()

        target_lane_x = target_x - self.get_lane_value()
        target_lane_y = target_y

        ax.plot([origin_lane_x, target_lane_x], [origin_lane_y, target_lane_y], color=self.color)

        arrow_length = self.target.get_text_start() - target_lane_x
        ax.arrow(x=target_lane_x, y=target_lane_y,
                 dx=arrow_length, dy=0,
                 color=self.color, length_includes_head=True,
                 width=self.arrow_width, head_width=5.0*self.arrow_width,
                 head_length=7.0*self.arrow_width)

    def plot_right_side(self, ax, text_end):
        origin_x = self.origin.get_text_end()
        origin_y = self.origin.position_y + self.get_box_offset_origin()

        origin_lane_x = text_end + self.get_lane_value()
        origin_lane_y = origin_y

        ax.plot([origin_x, origin_lane_x], [origin_y, origin_lane_y],
                color=self.color, linestyle=self.origin_linestyle)

        if self.description is not None and not self.origin_congested:
            bbox = dict(boxstyle="round", facecolor="white", edgecolor="white")
            ax.text(0.5*(origin_x + origin_lane_x), origin_lane_y,
                    self.description, ha="center", va="center", bbox=bbox)

        target_y = self.target.position_y + self.get_box_offset_target()

        target_lane_x = text_end + self.get_lane_value()
        target_lane_y = target_y

        ax.plot([origin_lane_x, target_lane_x], [origin_lane_y, target_lane_y], color=self.color)

        if self.connection:
            mid_point = 0.5*(target_lane_x + self.target.get_text_end())
            ax.plot([target_lane_x, self.target.get_text_end()],
                    [target_lane_y, target_lane_y], color=self.color)
        else:
            arrow_length = target_lane_x - self.target.get_text_end()
            mid_point = target_lane_x - 0.5*arrow_length
            ax.arrow(x=target_lane_x, y=target_lane_y,
                     dx=-arrow_length, dy=0,
                     color=self.color, length_includes_head=True,
                     width=self.arrow_width, head_width=5.0*self.arrow_width,
                     head_length=7.0*self.arrow_width)

        if self.description is not None and not self.target_congested:
            bbox = dict(boxstyle="round", facecolor="white", edgecolor="white")
            ax.text(mid_point, target_lane_y,
                    self.description, ha="center", va="center", bbox=bbox)


def component_description(component):
    """
    Returns string of information about the component

    Includes information on required parameters if they are not yet
    specified. Information on the components are added when the
    class is used as a superclass for classes describing each
    McStas component. Uses mathtext for bold and italics.
    """
    string = ""

    if len(component.c_code_before) > 1:
        string += component.c_code_before + "\n"
    if len(component.comment) > 1:
        string += "// " + component.comment + "\n"
    if component.SPLIT != 0:
        string += "SPLIT " + str(component.SPLIT) + " "
    string += "COMPONENT " + str(component.name)
    string += " = $\\bf{" + str(component.component_name).replace("_", "\_") + "}$\n"
    for key in component.parameter_names:
        val = getattr(component, key)
        parameter_name = key
        if val is not None:
            unit = ""
            if key in component.parameter_units:
                unit = "[" + component.parameter_units[key] + "]"
            if isinstance(val, Parameter):
                val_string = val.name
            elif isinstance(val, DeclareVariable):
                val_string = val.name
            else:
                val_string = str(val)

            value = "$\\bf{" + val_string.replace("_", "\_").replace('\"', "''").replace('"', "\''") + "}$"
            string += "  $\\bf{" + parameter_name.replace("_", "\_") + "}$"
            string += " = " + value + " " + unit + "\n"
        else:
            if component.parameter_defaults[key] is None:
                string += "  $\\bf{" + parameter_name.replace("_", "\_") + "}$"
                string += " : $\\bf{Required\ parameter\ not\ yet\ specified}$\n"

    if not component.WHEN == "":
        string += component.WHEN + "\n"

    string += "AT " + str(component.AT_data)
    if component.AT_reference is None:
        string += " $\\it{ABSOLUTE}$\n"
    else:
        string += " RELATIVE $\\it{" + component.AT_reference.replace("_", "\_") + "}$\n"

    if component.ROTATED_specified:
        string += "ROTATED " + str(component.ROTATED_data)
        if component.ROTATED_reference is None:
            string += " $\\it{ABSOLUTE}$\n"
        else:
            string += " $\\it{" + component.ROTATED_reference.replace("_", "\_") + "}$\n"

    if not component.GROUP == "":
        string += "GROUP " + component.GROUP + "\n"
    if not component.EXTEND == "":
        string += "EXTEND %{" + "\n"
        string += component.EXTEND + "%}" + "\n"
    if not component.JUMP == "":
        string += "JUMP " + component.JUMP + "\n"
    if len(component.c_code_after) > 1:
        string += component.c_code_after + "\n"

    return string.strip()



