import networkx as nx

class SpatialGraph:
    """
    Manages the map of locations and connectivity.
    """
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_location(self, loc_id, metadata):
        """
        Add a location node.
        """
        self.graph.add_node(loc_id, **metadata)

    def connect_locations(self, loc_a, loc_b, distance=1, one_way=False):
        """
        Connect two locations.
        """
        self.graph.add_edge(loc_a, loc_b, weight=distance)
        if not one_way:
            self.graph.add_edge(loc_b, loc_a, weight=distance)

    def get_path(self, start, end):
        try:
            return nx.shortest_path(self.graph, start, end, weight='weight')
        except nx.NetworkXNoPath:
            return None
            
    def get_locations(self):
        return list(self.graph.nodes(data=True))
