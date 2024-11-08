class Arrow:
    """
    Helper class for creating arrows with connections
    """
    def __init__(self, origin, target, lane=None, kind=None, description=None):
        """
        Arrow object with origin Component_box and target component_box
        """
        self.origin = origin
        self.target = target
        self.kind = kind
        self.description=description

        self.lane = lane
        self.sub_lane = 0
        self.lane_width = None
        self.lane_offset = 0

        self.box_offset_origin = 0
        self.box_offset_target = 0

        self.origin_linestyle = "-"
        self.color = "blue"
        self.alpha = 1.0
        self.arrow_width = 0.003
        self.arrow_length = 0.01
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

    def set_arrow_length(self, value):
        self.arrow_length = value

    def set_linestyle(self, value):
        self.origin_linestyle = value

    def set_alpha(self, value):
        self.alpha = value

    def plot_left_side(self, ax):
        # stop a bit before the lane and make a little triangle
        triangle_leg_x = 0.25 * self.arrow_length
        triangle_leg_y = 2.0 * self.arrow_width

        # box to lane
        origin_x = self.origin.get_text_start()
        origin_y = self.origin.position_y + self.get_box_offset_origin()

        origin_lane_x = origin_x - self.get_lane_value()
        origin_lane_y = origin_y

        entry_point_x = origin_lane_x + triangle_leg_x

        x_points = [origin_x, entry_point_x]
        y_points = [origin_y, origin_lane_y]

        # lane
        target_x = self.target.get_text_start()
        target_y = self.target.position_y + self.get_box_offset_target()

        target_lane_x = target_x - self.get_lane_value()
        target_lane_y = target_y

        exit_point_x = target_lane_x + triangle_leg_x

        # Plot lane but ease in and out of the lane with a small triangle
        x_points += [entry_point_x, origin_lane_x, origin_lane_x, target_lane_x, origin_lane_x, exit_point_x]
        y_points += [origin_lane_y, origin_lane_y + triangle_leg_y, origin_lane_y + triangle_leg_y,
                     target_lane_y - triangle_leg_y, target_lane_y - triangle_leg_y, target_lane_y]
        ax.plot(x_points, y_points, color=self.color, linestyle=self.origin_linestyle)

        # lane to box
        arrow_length = self.target.get_text_start() - target_lane_x - triangle_leg_x
        ax.arrow(x=target_lane_x + triangle_leg_x, y=target_lane_y,
                 dx=arrow_length, dy=0,
                 color=self.color, length_includes_head=True,
                 width=self.arrow_width, head_width=5.0*self.arrow_width,
                 head_length=self.arrow_length)

    def plot_right_side(self, ax, text_end):
        # stop a bit before the lane and make a little triangle
        triangle_leg_x = 0.25 * self.arrow_length
        triangle_leg_y = 2.0 * self.arrow_width

        # origin to lane
        origin_x = self.origin.get_text_end()
        origin_y = self.origin.position_y + self.get_box_offset_origin()

        origin_lane_x = text_end + self.get_lane_value()
        origin_lane_y = origin_y

        entry_point_x = origin_lane_x - triangle_leg_x

        x_points = [origin_x, entry_point_x]
        y_points = [origin_y, origin_lane_y]

        """
        ax.plot([origin_x, entry_point_x], [origin_y, origin_lane_y],
                color=self.color, linestyle=self.origin_linestyle, alpha=self.alpha)
        """

        if self.description is not None and not self.origin_congested:
            bbox = dict(boxstyle="round", facecolor="white", edgecolor="white", alpha=0.85)
            ax.text(0.5*(origin_x + origin_lane_x), origin_lane_y,
                    self.description, ha="center", va="center", bbox=bbox)

        # lane
        target_y = self.target.position_y + self.get_box_offset_target()

        target_lane_x = text_end + self.get_lane_value()
        target_lane_y = target_y

        exit_point_x = target_lane_x - triangle_leg_x

        if target_lane_y < origin_lane_y:
            leg_dir = 1
        else:
            leg_dir = -1

        triangle_leg_y_dir = leg_dir * triangle_leg_y

        # Plot lane but ease in and out of it with a small triangle
        x_points += [entry_point_x, target_lane_x, origin_lane_x, target_lane_x, origin_lane_x, exit_point_x]
        y_points += [origin_lane_y, origin_lane_y - triangle_leg_y_dir, origin_lane_y - triangle_leg_y_dir,
                     target_lane_y + triangle_leg_y_dir, target_lane_y + triangle_leg_y_dir, target_lane_y]
        ax.plot(x_points, y_points, color=self.color, alpha=self.alpha, linestyle=self.origin_linestyle)

        # target
        if self.connection:
            mid_point = 0.5*(target_lane_x + self.target.get_text_end())
            ax.plot([target_lane_x - triangle_leg_x, self.target.get_text_end()],
                    [target_lane_y, target_lane_y], color=self.color, alpha=self.alpha)
        else:
            arrow_length = target_lane_x - self.target.get_text_end() - triangle_leg_x
            mid_point = target_lane_x - 0.5*arrow_length
            ax.arrow(x=target_lane_x - triangle_leg_x, y=target_lane_y,
                     dx=-arrow_length, dy=0,
                     color=self.color, length_includes_head=True,
                     width=self.arrow_width, head_width=5.0*self.arrow_width,
                     head_length=self.arrow_length, alpha=self.alpha)

        if self.description is not None and not self.target_congested:
            bbox = dict(boxstyle="round", facecolor="white", edgecolor="white", alpha=0.85)
            ax.text(mid_point, target_lane_y,
                    self.description, ha="center", va="center", bbox=bbox)