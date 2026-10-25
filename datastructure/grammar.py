import collections.abc
from collections.abc import MutableSet, MutableMapping

from datastructure.edge import Edge
from datastructure.graph import Graph
from datastructure.helper import ParameterOccurrence


class Grammar:
    def __init__(self, graph, max_parameters, terminal_func, rank_func, size_func):
        """Initializes a grammar object.
        :param graph: used as the start_rule of this grammar. start_rule has the name 0 implicitly. Should be a graph.
        :param terminal_func: decides, if a symbol is used as an terminal. (e.g. type == str --> terminal symbol)
        :param rank_func: calculates the rank of a terminal rule.
        :param size_func: calculates the size of a terminal rule."""
        self.max_parameters = -max_parameters - 1
        self.rules: dict[..., Graph] = {self.max_parameters: graph}
        self.is_terminal = terminal_func
        self.terminal_rank = rank_func
        self.terminal_size = size_func
        # the statements above are functional programming. it is possible now to invoke grammar.is_terminal(...)
        self._parameters_marked_for_deletion: MutableMapping[ParameterOccurrence, bool] = dict()

    def __delitem__(self, key):
        """Deletes a rule with a given ID/Name.
        :param key: rule name to delete."""
        del self.rules[key]

    def __getitem__(self, item):
        """:returns a rule with a given ID/Name. Uses object[item]-Syntax"""
        return self.rules[item]

    def __len__(self):
        """:returns the number of Rules including the start_rule"""
        return len(self.rules)

    def __str__(self):
        """:returns a readable representation of this grammar object"""
        return self.rules.__str__()

    __repr__ = __str__  # both methods are the same now.

    def __iter__(self):
        """:returns an iterable over the rules within this grammar. Can be used by: for rule in grammar: ..."""
        return self.rules.__iter__()

    def get_start_rule(self) -> Graph:
        """:returns the start_rule at location max_parameters"""
        return self[self.max_parameters]

    def get_unused_nonterminal(self):
        """:return the next ID not associated with a rule"""
        i = self.max_parameters
        while i in self.rules or self.is_terminal(i):
            i -= 1
        return i

    def get_unused_nonterminal_generator(self):
        i = self.max_parameters
        while True:
            if i in self.rules or self.is_terminal(i):
                i -= 1
            else:
                yield i
                i -= 1

    def rank_of_rule(self, rule_name):
        """:param rule_name: name of an existing rule.
        :returns the rank of the Rule with the given name.
        """
        if self.is_terminal(rule_name):  # e.g. type(rule_name) is int:
            return self.terminal_rank(rule_name)
        else:
            return self[rule_name].get_rank()

    def size_of_rule(self, rule_name):
        """:param rule_name: name of an existing rule.
        :returns the size of the Rule with the given name.
        """
        if self.is_terminal(rule_name):  # e.g. type(rule_name) is int:
            return self.terminal_size(rule_name)
        else:
            return self[rule_name].size_of()

    def size_of_whole_grammar(self):
        """:return the size of the while grammar"""
        return sum((self.rules[g].size_of() for g in self.rules.keys()))

    def add_rule(self, rule_name, rule):
        """Method used for adding a rule. Note that there is no check, if there is a rule with the given Name.
        :param rule_name: name of the new added rule.
        :param rule: the new added rule. Should be of type Graph."""
        self.rules[rule_name] = rule

    def delete_all_rules_except_start_rule(self):
        """Deletes all rules except the start rule. Only decompress uses this when the start rule is fully rebuild. """
        self.rules = {self.max_parameters: self.rules[self.max_parameters]}

    def __copy__(self):
        c_grammar = Grammar(Graph(), -self.max_parameters - 1, self.is_terminal, self.terminal_rank, self.terminal_size)
        for rule, graph in self.rules.items():
            c_grammar.rules[rule] = graph.__copy__()
        return c_grammar

    def delete_parameters_marked_for_deletion(self):
        for parameter, already_deleted in self._parameters_marked_for_deletion.items():
            if not already_deleted:
                self._delete_parameter(parameter)
        self._parameters_marked_for_deletion = dict()

    def add_parameter_for_deletion(self, parameter: ParameterOccurrence, instant_delete=False):
        if parameter not in self._parameters_marked_for_deletion or not self._parameters_marked_for_deletion[parameter]:
            if instant_delete:
                self._delete_parameter(parameter)
                self._parameters_marked_for_deletion[parameter] = True
            else:
                self._parameters_marked_for_deletion[parameter] = False

    def _delete_parameter(self, parameter: ParameterOccurrence):
        edge = self[parameter.get_position().rule].edges[parameter.get_position().position_in_rule]
        if edge.get_all_nodes()[parameter.get_position().position_in_edge] != parameter.get_parameter():
            raise RuntimeError(f"Parameter is not where it should be!!!")
        edge = Edge(
            edge.get_label(),
            *edge.get_all_nodes()[:parameter.get_position().position_in_edge],
            *edge.get_all_nodes()[parameter.get_position().position_in_edge + 1:]
        )
        self[parameter.get_position().rule].edges[parameter.get_position().position_in_rule] = edge
