from abc import ABC, abstractmethod
from builtins import staticmethod
from collections import defaultdict
from functools import reduce
from typing import override

from datastructure.digram import Digram
from datastructure.edge import Edge
from datastructure.enums import DigramType, NodeType
from datastructure.grammar import Grammar
from datastructure.graph import Graph
from repair.helper import get_node_type, _clean_edge


class DigramRuleCreator(ABC):
    """This class is used as a creator for the new Rule from a digram and to replace
    two edges by a new hyperedge with correct order of nodes."""

    def __init__(self, digram, grammar):
        """ Constructs the class as well as the new rule object (instance of class graph)

        :param digram: Should be of type Digram.
        :param grammar: Should be the grammar object where the digram is replaced.
        """
        self.digram = digram
        self.grammar = grammar

        if digram is not None:
            labels = self._get_labels(digram)
            ranks = self._get_ranks(grammar, digram, labels)
            edges = self._get_edges(digram, labels, ranks)

            self.rule = Graph(edges, ranks[0] + ranks[1] - 1)
            self.rule_name = grammar.get_unused_nonterminal()
            # print(f"Constructed {self.rule_name}: {self.rule} from these edges {edges}")

    @staticmethod
    def get_rule_creator(digram: Digram, grammar: Grammar, advanced: bool):
        match digram.get_type():
            case DigramType.SIMPLE:
                if advanced:
                    return SimpleDigramRuleCreatorAdvanced(digram, grammar)
                else:
                    return SimpleDigramRuleCreator(digram, grammar)
            case DigramType.LABEL:
                if advanced:
                    return LabelDigramRuleCreatorAdvanced(digram, grammar)
                else:
                    return LabelDigramRuleCreator(digram, grammar)

    @abstractmethod
    def _get_labels(self, digram):
        pass

    @abstractmethod
    def _get_ranks(self, grammar, digram, labels):
        pass

    @abstractmethod
    def _get_edges(self, digram, labels, ranks):
        pass

    @staticmethod
    @abstractmethod
    def _build_edge(label, connection_type, rank_of_rule, node_offset):
        """Help method to create one of the edges used within the new rule of a digram
                    :param label: the label of the returned edge
                    :param connection_type: the node 0 will have this connection_type.
                    :param rank_of_rule: rank of the new created rule.
                    :param node_offset: Used to shift all node ids. Should not be 0!
                    :returns one edge that will be used in the rule."""
        pass

    def get_rule(self):
        """:returns the rule as a graph object. """
        return self.rule

    def get_rule_name(self):
        """:returns the name of the new constructed rule."""
        return self.rule_name

    def get_shared_node(self, edges):
        return edges[0].get_all_nodes()[self.digram[0][1]]

    @staticmethod
    def _delete_shared_node(l, position):
        del l[position]
        return l

    def get_hyperedge_for_edges(self, *edges: Edge) -> Edge:
        """Creates a hyperedge for the two edges after the ruling to the represented Rule.
        Note that the order of edge_1 and edge_2 must be given as it fits to the digram.

        :param edges: Catches up every position argument. Should be exactly two edges.
        :returns a non-terminal describing the given edges."""
        nodes = list(map(lambda e: list(e.get_all_nodes()), edges))
        shared_node = self.get_shared_node(edges)

        l1 = self._delete_shared_node(nodes[0], self.digram[0].get_connection_type())
        if self.digram.get_type() == DigramType.SIMPLE:
            l2 = self._delete_shared_node(nodes[1], self.digram[1].get_connection_type())
        else:
            l2 = self._delete_shared_node(nodes[1], self.digram.get_connection_type())

        temp = Edge(self.rule_name, shared_node, *l1, *l2)
        return temp

    @abstractmethod
    def _include_in_second_edge(self, digram, connection_type):
        pass


class SimpleDigramRuleCreator(DigramRuleCreator):
    def _include_in_second_edge(self, digram, connection_type):
        raise NotImplementedError("Not implemented yet")

    def _get_ranks(self, grammar, digram, labels):
        return [grammar.rank_of_rule(rule_name) for rule_name in labels]

    def _get_edges(self, digram, labels, ranks):
        return [self._build_edge(labels[0], digram[0].get_connection_type(), ranks[0], 1),
                self._build_edge(labels[1], digram[1].get_connection_type(), ranks[1], ranks[0])]

    @staticmethod
    def _build_edge(label, connection_type, rank_of_rule, node_offset):
        nodes = list(range(node_offset, rank_of_rule + node_offset - 1))
        nodes.insert(connection_type, 0)
        return Edge(label, *nodes)

    def _get_labels(self, digram):
        return [digram[i].get_label() for i in range(len(digram))]


class LabelDigramRuleCreator(DigramRuleCreator):

    def _include_in_second_edge(self, digram, connection_type):
        return connection_type != self.digram.get_connection_type()

    def _get_ranks(self, grammar, digram, labels):
        rank1 = grammar.rank_of_rule(labels[0])
        rank2 = digram.get_rank() + 1
        return [rank1, rank2]

    def _get_edges(self, digram, labels, ranks):
        edge1 = self._build_edge(labels[0], digram.get_label_adjacency_type().get_connection_type(), ranks[0], 2)
        edge2 = self._build_edge(labels[1], digram.get_connection_type(), ranks[1] - 1, ranks[0] + 1)
        return [edge1, edge2]

    def _get_labels(self, digram):
        label1 = digram.get_label_adjacency_type().get_label()
        label2 = 0
        return [label1, label2]

    @staticmethod
    def _build_edge(label, connection_type, rank_of_rule, node_offset):
        nodes = list(range(node_offset, rank_of_rule + node_offset - 1))
        nodes.insert(connection_type, 1)
        return Edge(label, *nodes)

    @override
    def get_hyperedge_for_edges(self, *edges):
        hyperedge = super().get_hyperedge_for_edges(*edges)
        edge = Edge(hyperedge.label, edges[1].get_label(), *hyperedge.get_all_nodes())
        return edge


class DigramRuleCreatorAdvanced(DigramRuleCreator, ABC):

    @override
    def get_shared_node(self, edges):
        return edges[0].get_nodes_only()[self.digram[0][1]]

    @staticmethod
    @override
    def _delete_shared_node(l, position):
        dirty_count = 0
        while position > 0:
            if get_node_type(l[dirty_count]) == NodeType.NODE:
                position -= 1
            dirty_count += 1
        while get_node_type(l[dirty_count]) != NodeType.NODE:
            dirty_count += 1
        del l[dirty_count]
        return l


class SimpleDigramRuleCreatorAdvanced(DigramRuleCreatorAdvanced, SimpleDigramRuleCreator):
    pass


class LabelDigramRuleCreatorAdvanced(DigramRuleCreatorAdvanced, LabelDigramRuleCreator):

    @override
    def _get_ranks(self, grammar, digram, labels):
        ranks = super()._get_ranks(grammar, digram, labels)
        ranks[1] += -1
        return ranks

    @override
    def _get_edges(self, digram, labels, ranks):
        edge1 = self._build_edge(labels[0], digram.get_label_adjacency_type().get_connection_type(), ranks[0], 1)
        edge2 = self._build_edge(labels[1], digram.get_connection_type(), ranks[1], ranks[0])
        return [edge1, edge2]

    @override
    def _get_labels(self, digram):
        labels = super()._get_labels(digram)
        labels[1] = -1
        return labels

    @override
    def get_hyperedge_for_edges(self, *edges):
        hyperedge = super().get_hyperedge_for_edges(*edges)
        edge = Edge(hyperedge.label, *hyperedge.get_all_nodes()[1:], hyperedge.get_all_nodes()[0])
        return edge

    @staticmethod
    @override
    def _build_edge(label, connection_type, rank_of_rule, node_offset):
        nodes = list(range(node_offset, rank_of_rule + node_offset - 1))
        nodes.insert(connection_type, 0)
        return Edge(label, *nodes)


class RuleInserter:
    def __init__(self, rule):
        self.rule = rule

    def get_rule(self):
        return self.rule

    def get_edges_for_hyperedge(self, hyperedge):
        edges = list()
        i = 0
        cleaned_hyperedge = _clean_edge(hyperedge)
        for edge in self.rule.get_edges():
            nodes = [cleaned_hyperedge[node] for node in edge]
            i += len(nodes)
            if get_node_type(edge.get_label()) == NodeType.PARAMETER:
                label = hyperedge[-1]
                hyperedge = hyperedge[:-1]
            else:
                label = edge.get_label()
            parameters, i = self._scan_for_parameters(hyperedge, i)
            edges.append(Edge(label, *nodes, *parameters))
        return edges

    def _scan_for_parameters(self, hyperedge, i):
        parameters = list()
        while i < len(hyperedge):
            if isinstance(hyperedge[i], str) or (isinstance(hyperedge[i], int) and hyperedge[i] < 0):
                parameters.append(hyperedge[i])
            else:
                return parameters, i
            i += 1
        return parameters, i
