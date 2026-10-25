from datastructure.edge import Edge
from datastructure.graph import Graph


class Monogram(tuple):
    def __new__(cls, label, connection_type_1, connection_type_2):
        """Fixes a Monogram to a label and two connection_types

        :param label: Label of the monogram
        :param connection_type_1: Should be the lower connection_type. A connection type is simply a number.
        :param connection_type_2: Should be the higher connection_type. A connection type is simply a number.
        connection_type_2 must be different from connection_type_1!"""
        return tuple.__new__(Monogram, (label, connection_type_1, connection_type_2))

    def get_label(self):
        """:returns the label of the Monogram."""
        return self[0]

class MonogramRuleCreator:
    """This class is used as a creator for the new Rule from a Monogram and to replace
    an edge by a new hyperedge with correct order of nodes.
    """
    def __init__(self, monogram, grammar):
        """Constructs the class as well as the new rule.

        :param monogram: Should be of type Monogram.
        :param grammar: Should be the grammar, where the Monogram should be applied to.
        """
        self.monogram = monogram

        def build_edge(label, connection_type_1, connection_type_2, rank_of_rule, node_offset):
            """Help method to create the edge used within the new rule of a monogram
            :param label: the label of the returned edge
            :param connection_type_1: this type should be repeated.
            :param connection_type_2: this characterizes the position of the repetition.
            :param rank_of_rule: rank of the new created rule.
            :param node_offset: Used to shift all node ids. Should be 0 to use minimal ids.
            :returns the edge that will be used in the rule."""
            nodes = list(range(node_offset, rank_of_rule + node_offset - 1))
            nodes.insert(connection_type_2, nodes[connection_type_1])
            return Edge(label, *nodes)
        if monogram is not None:
            rank = grammar.rank_of_rule(monogram.get_label())
            edges = [build_edge(monogram.get_label(), monogram[1], monogram[2], rank, 0)]
            self.rule = Graph(edges, rank - 1)
            self.rule_name = grammar.get_unused_nonterminal()

    def get_rule(self):
        """ :returns the rule as a graph object.
        The rule is created within the constructor, so here is no time needed."""
        return self.rule

    def get_rule_name(self):
        """:returns the name of the new rule."""
        return self.rule_name

    def get_hyperedge_for_edge(self, edge):
        """Creates a hyperedge for the edge corresponding to the monogram given while creating this object.
        :returns an edge object without the monogram[2] node.

        :param edge: edge where the given monogram can applied to (no check within). """
        nodes = list(edge.get_nodes())
        del nodes[self.monogram[2]]
        return Edge(self.rule_name, *nodes)