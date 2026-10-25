from abc import abstractmethod, ABC

from datastructure.edge import Edge


class AdjacencyType(tuple, ABC):
    def __new__(cls, label, connection_type):
        """Fixes an AdjacencyType to a label and an connection_type

        :param label: Label of the adjacency type. Can be anything hashable.
        :param connection_type: A connection type is a natural number (with 0). It must fit to the rank of the label."""
        return tuple.__new__(AdjacencyType, (label, connection_type))

    def get_label(self) -> ...:
        """:returns the label of this AdjacencyType."""
        return self[0]

    def get_connection_type(self) -> int:
        """:returns the connection type of this AdjacencyType."""
        return self[1]

    def is_allowed_edge(self, edge: Edge) -> bool:
        return self.get_label() == edge.get_label()


class SimpleAdjacencyType(AdjacencyType):
    pass


class LabelAdjacencyType(AdjacencyType):
    def __new__(cls, label, connection_type, rank):
        return tuple.__new__(LabelAdjacencyType, (label, connection_type, rank))

    def get_rank(self):
        return self[2]


class SecondLabelAdjacencyType(tuple):
    def __new__(cls, connection_type, rank):
        return tuple.__new__(SecondLabelAdjacencyType, (connection_type, rank))

    def get_connection_type(self):
        return self[0]

    def get_rank(self):
        return self[1]

    def is_allowed_edge(self, edge: Edge, advanced: bool) -> bool:
        return self.get_rank() == edge.get_rank(advanced)