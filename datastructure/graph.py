from collections.abc import Iterable
from typing import List

from datastructure.edge import Edge


class Graph:
    def __init__(self, edges=None, rank=-1):
        """Inits a Graph object.
        :param edges: initial edges of this graph.
        :param rank: rank is the rank of the edge used to represent this rule.
        It's equal to the number of nodes in this graph.
        It's optional to use this field."""
        self.edges: List[Edge] = [] if edges is None else edges
        self._rank = rank

    def __iadd__(self, new_edge):
        """Used to add an edge to the Graph
        :param new_edge: the new edge."""
        self.edges += [new_edge]
        return self

    __add__ = __iadd__

    def get_edges(self) -> List[Edge]:
        """:returns all edges within this graph object."""
        return self.edges

    def __getitem__(self, id) -> Edge | List[Edge]:
        """:returns the edge at a given ID"""
        return self.edges[id]

    def __setitem__(self, id, new_edge: Edge):
        """Replaces a new edge at the given ID.
        :param id: id of the edge.
        :param new_edge: the new edge"""
        self.edges[id] = new_edge

    def __delitem__(self, id):
        """Deletes an edge at a given ID.
        :param id: id of the edge, which is going to be deleted."""
        del self.edges[id]

    def __str__(self):
        """:returns a string representation of this graph."""
        return "Graph {}".format(self.edges)

    __repr__ = __str__

    def __len__(self):
        """:returns the number of edges within the graph."""
        return len(self.edges)

    def size_of(self):
        """:returns the cumulative size of all rules."""
        return sum((e.size_of() for e in self.edges))

    def __iter__(self):
        """:returns an iterable over the edges. Used for loops"""
        return self.edges.__iter__()

    def rank(self):
        """:returns the rank field.
        Can be interpreted as the node count or as the rank of the non-terminal edges representing this rule."""
        return self._rank

    def get_rank(self):
        return self.rank()

    def extend(self, edges: Iterable[Edge]):
        """Adds the edges to this graph.
        :param edges: iterable over the new to add edges."""
        self.edges.extend(edges)

    def insert(self, position, *new_edges: Edge):
        """
        Insert the edges before the given position.
        :param position: The position to insert the new edges from.
        :param new_edges: the new edges to insert.
        """
        self.edges[position:position] = new_edges

    def __eq__(self, other):
        """:returns true, if and only if both graphs are equal. The order of the edges is not important."""
        result = True
        edges = self.get_edges().copy()
        for e in other.get_edges():
            for f in edges:
                if e == f:
                    edges.remove(f)
        if len(edges) != 0:
            result = False
        other_edges = other.get_edges().copy()
        for e in self.get_edges():
            for f in other_edges:
                if e == f:
                    other_edges.remove(f)
        if len(other_edges) != 0:
            result = False
        if not result:
            print("Wrong edges left side: ", edges)
            print("Wrong edges right side:", other_edges)
        return result

    def get_edges_per_node(self, node_only=True):
        edges_per_node = {}
        for edge in self.edges:
            if node_only:
                nodes = edge.get_nodes_only()
            else:
                nodes = edge.get_all_nodes()
            for node in nodes:
                if node not in edges_per_node:
                    edges_per_node[node] = [edge, ]
                else:
                    # if edge not in edges_per_node[node]:
                    edges_per_node[node].append(edge)
        return edges_per_node

    def remove_edge(self, edge):
        self.edges.remove(edge)

    def __copy__(self):
        return Graph(self.get_edges().copy(), self.rank())
