class IndexConnection:
    def __init__(self, start_index, end_index):
        self.start_index = start_index
        self.end_index = end_index

        if start_index <= end_index:
            self.interval_start = start_index
            self.interval_end = end_index
        else:
            self.interval_start = end_index
            self.interval_end = start_index

    def compatible_with(self, new):
        """
        Check if the new interval can coexist with the existing
        """
        if new.interval_end > self.interval_start and new.interval_start < self.interval_end:
            return False

        return True


class Lane:
    def __init__(self):
        self.connections = []

    def add_connection(self, start_index, end_index):
        """
        If possible adds connection and returns True, otherwise returns False
        """
        new_connection = IndexConnection(start_index, end_index)

        # A line can skip on either start or end, not both
        skipped_end = False
        skipped_start = False

        # Check if there is room for this lane
        for connection in self.connections:
            # Check for number of reasons for connection being allowed
            if connection.start_index == new_connection.start_index and not skipped_end:
                # Allow connections to collide when the start index matches
                skipped_start = True
                continue

            if connection.end_index == new_connection.end_index and not skipped_start:
                # Allow connections to collide when the end index matches
                skipped_end = True
                continue

            if connection.compatible_with(new_connection):
                # Allow if there are no index overlap in lane
                continue

            # If connection incompatible, return false
            return False

        # No problems, this connection can be included in this lane
        self.connections.append(new_connection)
        return True


class Connection:
    def __init__(self, origin, target, info=None):
        """
        Describes a connection between origin and target with lane number

        Can contain info as well which can be used for example to mark
        if the connection is part of a certain group.
        """
        self.origin = origin
        self.target = target
        self.lane_number = None
        self.info = info

    def set_lane_number(self, value):
        self.lane_number = value


class ConnectionList:
    def __init__(self):
        """
        List of connections with utility functions

        Can distribute the connections over a number of lanes to ensure all
        connections can be seen without crossing that provide ambitious
        interpretations.
        """
        self.connections = []

    def add(self, origin, target, info=None):
        self.connections.append(Connection(origin, target, info=info))

    def get_connections(self):
        return self.connections

    def get_origins(self):
        return [x.origin for x in self.connections]

    def get_targets(self):
        return [x.target for x in self.connections]

    def get_pairs(self):
        return zip(self.get_origins(), self.get_targets())

    def get_targets_for_origin(self, given_origin):

        return_targets = []
        for origin, target in self.get_pairs():
            if origin == given_origin:
                return_targets.append(target)

        return return_targets

    def distribute_lane_numbers(self, box_names):
        lanes = []

        for connection in self.connections:
            start_index = box_names.index(connection.origin.name)
            end_index = box_names.index(connection.target.name)

            proposed_lane = 0
            while True:
                if proposed_lane >= len(lanes):
                    lanes.append(Lane())

                if lanes[proposed_lane].add_connection(start_index=start_index, end_index=end_index):
                    connection.set_lane_number(proposed_lane + 1)
                    break

                proposed_lane += 1

