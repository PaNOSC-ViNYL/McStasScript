import copy

import matplotlib.pyplot as plt
import numpy as np

from mcstasscript.instrument_diagram.box import ComponentBox
from mcstasscript.instrument_diagram.component_description import component_description

class DiagramCanvas:
    def __init__(self, left_side_arrows, component_boxes, right_side_arrows,
                 component_categories, colors, intensity_diagnostics=None,
                 variable=None, limits=None):
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

        If intensity_diagnostics is given with an IntensityDiagnostics object,
        a graph of the intensity and n rays throughout the instrument is
        generated instead of the right side arrows.
        """
        self.left_side_arrows = left_side_arrows
        self.component_boxes = component_boxes
        self.right_side_arrows = right_side_arrows
        self.all_arrows = left_side_arrows + right_side_arrows
        self.component_categories = component_categories
        self.colors = colors

        self.variable = variable
        self.limits = limits
        if intensity_diagnostics is None:
            self.intensity_analysis_mode = False
        else:
            self.intensity_analysis_mode = True
            self.intensity_diagnostics = intensity_diagnostics

        # Identify cases where multiple written input goes to or from same box
        arrow_connections = {x: [] for x in self.component_boxes}
        for arrow in self.right_side_arrows:
            arrow_connections[arrow.origin].append(arrow)
            arrow_connections[arrow.target].append(arrow)

        for box in arrow_connections:
            arrows = arrow_connections[box]
            if len(arrows) > 1:  # Only look at cases with more than one arrow to / from box
                # Find unique kinds
                kinds_entry = set()
                kinds_exit = set()
                for arrow in arrows:
                    if arrow.target is box:
                        kinds_entry.add(arrow.kind)

                    if arrow.origin is box:
                        kinds_exit.add(arrow.kind)

                n_collected_arrows = len(kinds_entry) + len(kinds_exit)
                if n_collected_arrows == 1:
                    # If there is only one kind and direction, we are done
                    continue

                # Distribute placements on the box equally for the different kinds / with entry/exit kept apart
                displacements = list(np.linspace(-0.16, 0.16, n_collected_arrows))

                entry_displacements = {}
                exit_displacements = {}
                for arrow in arrows:

                    if arrow.target is box:
                        arrow.set_target_congested(True)  # Mark congested, avoids writing description on the line

                        if arrow.kind in entry_displacements:
                            arrow.set_box_offset_target(entry_displacements[arrow.kind])
                        else:
                            displacement = displacements.pop()
                            entry_displacements[arrow.kind] = displacement
                            arrow.set_box_offset_target(displacement)

                    if arrow.origin is box:
                        arrow.set_origin_congested(True) # Mark congested, avoids writing description on the line

                        if arrow.kind in exit_displacements:
                            arrow.set_box_offset_origin(exit_displacements[arrow.kind])
                        else:
                            displacement = displacements.pop()
                            exit_displacements[arrow.kind] = displacement
                            arrow.set_box_offset_origin(displacement)

        # Style constants
        self.FIG_HEIGHT_PER_BOX = 0.4
        self.FIG_WIDTH_PER_LANE = 0.33
        self.FIG_WIDTH_PER_WEIGHTED_CHARACTER = 0.122
        self.FIG_EXTRA_WIDTH_FOR_TEXT = 0.15
        self.FIG_LEFT_MARGIN = self.FIG_WIDTH_PER_LANE * 0.5
        self.FIG_RIGHT_MARGIN = self.FIG_WIDTH_PER_LANE * 0.5
        self.FIG_LEGEND_HEADLINE = 0.2
        if self.intensity_analysis_mode:
            self.FIG_RIGHT_SIDE_MINIMUM_SPACE = 5
        else:
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

        # Arrow width and height in graph units, compensate for graph size to roughly equalize
        arrow_width = 0.02 / (self.graph_height + 0.5) # added constant to avoid asymptote near 0
        arrow_length = 0.2 / (self.graph_width + 0.05)

        # Rescale all
        for arrow in self.all_arrows:
            arrow.set_lane_width(lane_width)
            arrow.set_lane_offset(0.18)
            arrow.set_arrow_width(arrow_width)
            arrow.set_arrow_length(arrow_length)

        for box in self.component_boxes:
            box.set_box_indent(self.FIG_EXTRA_WIDTH_FOR_TEXT/self.graph_width)
            box.set_x(self.text_start_graph)  # Places boxes so they get name_width space

        # Prepare legend
        all_categories = list(set(component_categories.values()))
        if "work directory" not in all_categories:
            all_categories.append("work directory")
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

    def make_legend(self):

        box_top = 1 - self.FIG_LEGEND_HEADLINE / self.legend_height

        fig, ax = plt.subplots(figsize=(6.2, self.legend_height))
        ax.set(xlim=(0, 1), ylim=(0, 1))
        ax.get_xaxis().set_ticks([])
        ax.get_yaxis().set_ticks([])

        bbox = dict(boxstyle="round", facecolor="white", edgecolor="white")

        ax.text(0.385, 1.03, "Legend", va="center", ha="center", fontweight="semibold", bbox=bbox, fontsize="large")

        legend_boxes = [ComponentBox("Arm")]
        for category, color in self.category_color_dict.items():
            box = ComponentBox(category)
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
        show_Union = False
        show_JUMP_target_index = False
        any_JUMP = False
        any_target_index = False
        for arrow in self.all_arrows:
            if arrow.kind == "GROUP":
                show_GROUP = True
            if arrow.kind == "JUMP":
                show_JUMP_target_index = True
                any_JUMP = True
            if arrow.kind == "target_index":
                show_JUMP_target_index = True
                any_target_index = True
            if arrow.kind == "Union":
                show_Union = True

        arrow_width = 0.012
        AT_HEIGHT = 0.83
        START_WIDTH = 0.47
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

        if show_JUMP_target_index:
            if any_JUMP and any_target_index:
                legend_text = "JUMP / target_index"
            elif any_JUMP:
                legend_text = "JUMP"
            elif any_target_index:
                legend_text = "target_index"

            current_displacement -= DISPLACEMENT
            ax.arrow(x=START_WIDTH, y=AT_HEIGHT+current_displacement, dx=LINE_LENGTH, dy=0,
                     color=self.colors["JUMP"], length_includes_head=True, width=arrow_width,
                     head_width=5.0 * arrow_width, head_length=2.5 * arrow_width)
            ax.text(START_WIDTH + TEXT_WIDTH_INDENT, AT_HEIGHT+current_displacement+TEXT_DISPLACEMENT,
                    legend_text, va="center", weight="semibold")

        if show_GROUP:
            current_displacement -= DISPLACEMENT
            ax.plot([START_WIDTH, START_WIDTH+LINE_LENGTH], 2*[AT_HEIGHT + current_displacement],
                    color=self.colors["GROUP"])
            ax.text(START_WIDTH + TEXT_WIDTH_INDENT, AT_HEIGHT + current_displacement + TEXT_DISPLACEMENT,
                    "GROUP", va="center", weight="semibold")

        box_y_coordinates = list(np.linspace(margin, box_top, 5))
        box_x_coordinate = 0.83

        # Check if any boxes are decorated for EXTEND or WHEN
        for box in self.component_boxes:
            if box.component_object is not None:
                if box.component_object.EXTEND != "":
                    EXTEND_box = copy.deepcopy(box)
                    EXTEND_box.name = "EXTEND"
                    EXTEND_box.background_color = "white"
                    EXTEND_box.set_x(box_x_coordinate)
                    EXTEND_box.set_y(box_y_coordinates.pop())
                    EXTEND_box.plot_box(ax)
                    break

        for box in self.component_boxes:
            if box.component_object is not None:
                if box.component_object.WHEN != "":
                    WHEN_box = copy.deepcopy(box)
                    WHEN_box.name = "WHEN"
                    WHEN_box.background_color = "white"
                    WHEN_box.set_x(box_x_coordinate)
                    WHEN_box.set_y(box_y_coordinates.pop())
                    WHEN_box.plot_box(ax)
                    break

    def plot(self):

        self.make_legend()

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

        if not self.intensity_analysis_mode:
            for arrow in self.right_side_arrows:
                # Plot arrows on right side
                arrow.plot_right_side(ax, self.text_end_graph)
        else:
            # Make insert with intensity and ray count graph

            # Find x coordinate of insert
            box_ends = [b.get_text_end() for b in self.component_boxes]
            latest_box_end = max(box_ends)
            remaining_space = 1.0 - latest_box_end
            axes_start_x = latest_box_end + 0.05 * remaining_space  # 0.1 works well if no names shown

            # Get y position for all boxes, but skip ABSOLUTE box
            y_positions = [box.position_y for box in self.component_boxes[1:]]
            y_spacing = y_positions[0] - y_positions[1]

            if self.variable is None:
                upper_y_lim = y_positions[0] + 0.5 * y_spacing
                lower_y_lim = y_positions[-1] - 0.5 * y_spacing
            else:
                upper_y_lim = y_positions[0]
                lower_y_lim = y_positions[-1]

            # Insert is done in figure coordinate system, need mother ax dimensions
            ax_pos = ax.get_position()

            # Find figure coordinates of the corners of the desired inset
            inset_y_bottom = ax_pos.y0 + lower_y_lim*(ax_pos.y1 - ax_pos.y0)
            inset_y_top = ax_pos.y0 + upper_y_lim*(ax_pos.y1 - ax_pos.y0)

            inset_x_start = ax_pos.x0 + axes_start_x*(ax_pos.x1 - ax_pos.x0)
            inset_x_end = ax_pos.x1

            # Create inset
            inset_ax = fig.add_axes((inset_x_start, inset_y_bottom,
                                     inset_x_end-inset_x_start,
                                     inset_y_top-inset_y_bottom))

            # Ensure the new axis is plotted under the old one for annotations to show up
            ax.set_zorder(4)

            # Plot graph, convey tick positions and ylimits to match main diagram
            self.intensity_diagnostics.run_general(variable=self.variable, limits=self.limits)
            self.intensity_diagnostics.plot(ax=inset_ax, fig=fig,
                                            y_tick_positions=y_positions,
                                            ylimits=[lower_y_lim, upper_y_lim],
                                            show_comp_names=False)


        # Create anotation box that will be shown when hovering the mouse over a box
        annot = ax.annotate("", xy=(0, 0), xytext=(20, 10), textcoords="offset points",
                            va="center", annotation_clip=False,
                            bbox=dict(boxstyle="round", fc="w"))
        annot.set_visible(False)

        # Helper function to update the anotation box with correct text
        def update_annot(ind):
            pos = sc.get_offsets()[ind["ind"][0]]
            annot.xy = pos

            n_lines_in_info = len(box_info[ind["ind"][0]].split("\n"))
            if n_lines_in_info > 4:
                annot.set_position((20, n_lines_in_info*(5 - pos[1]*10)))
            else:
                annot.set_position((20, 0))

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