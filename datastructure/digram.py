from abc import abstractmethod, ABC
from typing import Self, override, Any, overload
from typing_extensions import SupportsIndex

from datastructure.adjacenytype import SimpleAdjacencyType, AdjacencyType, LabelAdjacencyType, SecondLabelAdjacencyType
from datastructure.edge import Edge
from datastructure.enums import DigramType


class Digram(tuple, ABC):
    @abstractmethod
    def get_type(self) -> DigramType:
        pass

    @abstractmethod
    def is_allowed_edge(self, adj_index: int, edge: Edge, advanced: bool = False) -> bool:
        pass


class SimpleDigram(Digram):
    """This class is used to represent a Digram. Note, that the order of the AdjacencyTypes is important when comparing,
    but it is not important within the graph-repair-algorithm."""

    def is_allowed_edge(self, adj_index: int, edge: Edge, advanced: bool = False) -> bool:
        return self[adj_index].is_allowed_edge(edge)

    def get_type(self) -> DigramType:
        return DigramType.SIMPLE

    def __new__(cls, adjacency_type_1: SimpleAdjacencyType, adjacency_type_2: SimpleAdjacencyType):
        """Fixes a Digram to two AdjacencyTypes.
        :param adjacency_type_1: first AdjacencyType.
        :param adjacency_type_2: second Adjacency Type."""
        return tuple.__new__(SimpleDigram, (adjacency_type_1, adjacency_type_2))

    def invert(self) -> Self:
        """:returns a Digram with the AdjacencyTypes in inverted order."""
        return SimpleDigram(self[1], self[0])

    # def __eq__(self, other):
    #    return super().__eq__(other) or (self[0] == other[1] and self[1] == other[0])

    # def __hash__(self):
    #    return super().__hash__()

    # def __str__(self):
    #    return 'Digram {}'.format(super().__str__())

    # repr__ = __str__


class LabelDigram(Digram):
    """This class is used to represent a labeled Digram."""

    def is_allowed_edge(self, adj_index: int, edge: Edge, advanced: bool = False) -> bool:
        if adj_index == 0:
            return self[0].is_allowed_edge(edge)
        else:
            return self[1].is_allowed_edge(edge, advanced)

    def get_type(self) -> DigramType:
        return DigramType.LABEL

    def __new__(cls, label_adjacency_type, connection_type, rank):
        """Fixes a Digram to two AdjacencyTypes.
        :param label_adjacency_type: The LabelAdjacencyType of the first edge.
        :param connection_type: The connection_type of the second edge
        :param rank: The rank of the second edge"""
        second_type = SecondLabelAdjacencyType(connection_type, rank)
        return tuple.__new__(LabelDigram, (label_adjacency_type, second_type))

    def get_label_adjacency_type(self) -> ...:
        return self[0]

    def get_connection_type(self) -> int:
        return self[1].get_connection_type()

    def get_rank(self) -> int:
        return self[1].get_rank()
