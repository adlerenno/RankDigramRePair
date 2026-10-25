from collections.abc import MutableSequence, Iterable

from datastructure.digram import Digram
from datastructure.edge import Edge, get_node_type
from datastructure.enums import NodeType, DigramType
from datastructure.graph import Graph
from datastructure.helper import ParameterOccurrence, Position


def extract_parameters(edge: Edge):
    parameters = []
    for node in edge:
        if get_node_type(node) != NodeType.NODE:
            parameters.append(node)
    return parameters


def extract_parameter_occurrences(edge: Edge, current_rule, current_edge_position):
    parameters = []
    for index in range(len(edge.get_all_nodes())):
        node = edge[index]
        if get_node_type(node) != NodeType.NODE:
            parameters.append(ParameterOccurrence(node, Position(current_rule, current_edge_position, index)))
    return parameters


def _clean_edge(edge: Edge) -> Iterable[...]:
    cleaned_edge = []
    for node in edge:
        if get_node_type(node) == NodeType.NODE:
            cleaned_edge.append(node)
    return cleaned_edge


def get_all_occurrences(graph: Graph, digram: Digram, advanced: bool = False):
    helper = DigramOccurrenceHelper(graph, digram, advanced)
    occurrence = helper.get_next_occurrence()
    while occurrence is not None:
        yield occurrence
        occurrence = helper.get_next_occurrence()


class DigramOccurrenceHelper:

    def __init__(self, graph: Graph, digram: Digram, advanced: bool = False):
        self.graph = graph
        self.digram = digram
        self.start = 0
        self.current_first_edges: dict[int, list[int]] = {}
        self.current_second_edges: dict[int, list[int]] = {}
        self.advanced = advanced

    def get_next_occurrence(self):
        for i in range(self.start, len(self.graph)):
            edge: Edge = self.graph[i]
            if self.digram.is_allowed_edge(0, edge, self.advanced):
                connection_type = self.digram[0].get_connection_type()
                node = edge.get_node(connection_type, self.advanced)
                if node in self.current_second_edges:
                    possible_partners = self.current_second_edges[node]
                    for other_edge in possible_partners:
                        if i != other_edge:
                            possible_partners.remove(other_edge)
                            if self.digram.is_allowed_edge(0, self.graph[other_edge], self.advanced):
                                other_node = self.graph[other_edge].get_node(self.digram[0].get_connection_type(),
                                                                             self.advanced)
                                if other_node in self.current_first_edges:
                                    if other_edge in self.current_first_edges[other_node]:
                                        self.current_first_edges[other_node].remove(other_edge)
                            self.start = i
                            return i, other_edge
                if node in self.current_first_edges:
                    self.current_first_edges[node].append(i)
                else:
                    self.current_first_edges[node] = [i]

            if self.digram.is_allowed_edge(1, edge, self.advanced):
                connection_type = self.digram[1].get_connection_type()
                node = edge.get_node(connection_type, self.advanced)
                if node in self.current_first_edges:
                    possible_partners = self.current_first_edges[node]
                    for other_edge in possible_partners:
                        if i != other_edge:
                            possible_partners.remove(other_edge)
                            if self.digram.is_allowed_edge(1, self.graph[other_edge], self.advanced):
                                other_node = self.graph[other_edge].get_node(self.digram[1].get_connection_type(),
                                                                             self.advanced)
                                if other_node in self.current_second_edges:
                                    if other_edge in self.current_second_edges[other_node]:
                                        self.current_second_edges[other_node].remove(other_edge)
                            if self.digram.is_allowed_edge(0, edge, self.advanced):
                                i_node = edge.get_node(self.digram[0].get_connection_type(), self.advanced)
                                if i_node in self.current_first_edges:
                                    if i in self.current_first_edges[i_node]:
                                        self.current_first_edges[i_node].remove(i)
                            self.start = i
                            return other_edge, i
                if node in self.current_second_edges:
                    self.current_second_edges[node].append(i)
                else:
                    self.current_second_edges[node] = [i]
        return None
