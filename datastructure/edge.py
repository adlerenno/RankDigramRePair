from collections.abc import MutableSequence, Iterable

from datastructure.enums import NodeType
from datastructure.helper import ParameterOccurrence


def get_node_type(x):  # ToDo: Change -32 to grammar.max_parameters
    if isinstance(x, str):
        return NodeType.LABEL
    elif isinstance(x, int) and x < -32:
        return NodeType.RULE
    elif isinstance(x, int) and -32 <= x < 0:
        return NodeType.PARAMETER
    elif isinstance(x, int) and x >= 0:
        return NodeType.NODE
    else:
        raise ValueError("Type:", x, "not supported")


class Edge:
    def __init__(self, label, *nodes):
        """Inits a labeled Hyperedge.
        :param label: label of the new edge.
        :param nodes: all following arguments are treated as vertices."""
        self.label = label
        self.nodes = nodes

    def __repr__(self):
        """:returns a String representation of this edge object."""
        return "{}({})".format(self.label, ", ".join((str(n) for n in self.nodes)))

    __str__ = __repr__

    def __len__(self):
        """:returns the number of nodes attached to this edge. Should always be the same result as edge.rank()"""
        return self.get_rank()  # ToDo: Check if this messes up anything!!!

    def __getitem__(self, item) -> int | list[int]:
        """:returns the node with connection_type 'item'"""
        return self.nodes[item]

    def __iter__(self):
        """:returns an iterable looping over the attached nodes in order of their connection_types."""
        return self.nodes.__iter__()

    def get_all_nodes(self):
        """:returns a list of the attached nodes ordered after the connection_type."""
        return self.nodes

    def get_nodes_only(self):
        return [node for node in self.nodes if get_node_type(node) == NodeType.NODE]

    def get_parameters_only(self):
        return [node for node in self.nodes if get_node_type(node) != NodeType.NODE]

    def get_label(self):
        """:returns the label of this edge."""
        return self.label

    def get_rank(self, advanced=False):
        """:returns the rank of this edge"""
        if advanced:
            return self.get_rank_advanced()
        else:
            return len(self.nodes)

    def get_rank_advanced(self):
        counter = 0
        for node in self.nodes:
            if get_node_type(node) == NodeType.NODE:
                counter += 1
        return counter

    def is_hyperedge(self):
        """Method to determine, if an edge is a hyperedge. Used only by latex.py"""
        return self.get_rank() != 2

    def is_loop(self):
        """Method to determine, if an edge is normal and only connected to one node. Used only by latex.py"""
        return self.get_rank() == 2 and len(set(self.nodes)) == 1


    def get_node_from_edge(self, connection_type):
        if connection_type < len(self.nodes):
            return self.nodes[connection_type]
        else:
            return "x"

    def size_of(self):
        """:returns the size to save this edge. +1 is for the label of the Edge. """
        return len(self.nodes) + 1

    def rank(self):
        return self.get_rank(False)

    def __eq__(self, other):
        """:returns true if and only if self and other represent the same edge."""
        return self.label == other.get_label() and self.nodes == other.get_all_nodes()

    def delete_parameter(self, parameter: ParameterOccurrence):
        if self.nodes[parameter.get_position().position_in_edge] == parameter.get_parameter():
            self.nodes = (self.nodes[:parameter.get_position().position_in_edge] +
                          self.nodes[parameter.get_position().position_in_edge + 1:])
        else:
            raise RuntimeError(f"The parameter was not found in this edge!!!")

    def delete_parameters(self, parameters: Iterable[ParameterOccurrence]):
        sorted_parameters = sorted(parameters, reverse=True,
                                   key=lambda parameter: parameter.get_position().position_in_edge)
        for parameter in sorted_parameters:
            self.delete_parameter(parameter)

    def get_node(self, connection_type, advanced) -> int:
        if advanced:
            return self.get_nodes_only()[connection_type]
        else:
            return self.nodes[connection_type]
