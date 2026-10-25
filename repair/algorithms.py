import random
from collections.abc import Iterable, MutableSequence
from copy import deepcopy
from functools import reduce

from progress.bar import Bar

from datastructure.adjacenytype import SimpleAdjacencyType, LabelAdjacencyType
from datastructure.digram import SimpleDigram, LabelDigram, Digram
from datastructure.edge import Edge
from datastructure.enums import *
from datastructure.grammar import Grammar
from datastructure.graph import Graph
from datastructure.helper import RuleCallWrapper, ParameterOccurrence, Position, EdgePosition, ParameterPath, \
    ParameterPathsBuilder, ExtendedPosition, ParameterPaths, ChangeHelper
from datastructure.monogram import Monogram, MonogramRuleCreator
from repair.helper import extract_parameters, get_node_type, _clean_edge, extract_parameter_occurrences, \
    get_all_occurrences
from repair.rules import DigramRuleCreator

DEBUG = None


def repair(grammar, logic, advanced) -> float:
    """Main method of RePair algorithm.
     :param logic: The used logic for selecting the next digram
     :param grammar: a grammar with a start_rule.
     :param advanced: Use the advanced method to create rules
     :returns used label digrams divided with all used digrams."""
    from main import DEBUG as D
    global DEBUG
    DEBUG = D

    # Step 1: Digram replacing
    if DEBUG:
        print("Start digram replacing")
    label_digram_percent = replace_digrams(grammar, logic, advanced)

    # Step 2: Monogram Replacing
    if DEBUG:
        print("Start monogram replacing")
    replace_monograms(grammar)

    # Step 3: Pruning
    if DEBUG:
        print("Start pruning")
    if advanced:
        prune_advanced(grammar)
    else:
        prune(grammar)

    if DEBUG:
        print("Repair finished")
    return label_digram_percent


def replace_digrams(grammar, logic, advanced) -> float:
    used_simple_digrams = 0
    used_label_digrams = 0
    start_rule = grammar.get_start_rule()

    # node_edge_simple_adjacency_dict is a dictionary.
    # At index i, it contains a dict mapping an AdjacencyType to its frequency at the node i
    node_edge_simple_adjacency_dict, node_edge_label_adjacency_dict = create_node_edge_adjacency_dicts(start_rule,
                                                                                                       advanced)

    # simple_digram_count is a dictionary mapping adjacency_types to its frequency within the start_rule
    simple_digram_count = count_simple_digrams(node_edge_simple_adjacency_dict)
    label_digram_count = count_label_digrams(node_edge_label_adjacency_dict)

    digram_to_replace = get_digram_to_replace(grammar, simple_digram_count, label_digram_count, logic)
    if digram_to_replace is not None:
        new_rule = create_new_rule_for_digram(digram_to_replace, grammar, advanced)
        while should_continue_replacing_digram(digram_to_replace, simple_digram_count, label_digram_count, new_rule,
                                               grammar):
            count_real_replacements = 0
            for pos1, pos2 in get_all_occurrences(start_rule, digram_to_replace, advanced):
                old_edges = (start_rule[pos1], start_rule[pos2])
                new_edge = new_rule.get_hyperedge_for_edges(*old_edges)
                start_rule[min(pos1, pos2)] = new_edge
                del start_rule[max(pos1, pos2)]
                count_real_replacements += 1

            if DEBUG:
                print(
                    f"Replaced {count_real_replacements} digrams. Expected replacements: "
                    f"{simple_digram_count[digram_to_replace] if digram_to_replace.get_type() == DigramType.SIMPLE else label_digram_count[digram_to_replace]}")

            if count_real_replacements > 0:
                # print(grammar)
                grammar.add_rule(new_rule.rule_name, new_rule.rule)
                if new_rule.digram.get_type() == DigramType.SIMPLE:
                    used_simple_digrams += 1
                elif new_rule.digram.get_type() == DigramType.LABEL:
                    used_label_digrams += 1
                else:
                    raise RuntimeError(f"Unexpected digram type: {new_rule.digram.get_type()}")
            node_edge_simple_adjacency_dict, node_edge_label_adjacency_dict = create_node_edge_adjacency_dicts(
                start_rule, advanced)
            simple_digram_count = count_simple_digrams(node_edge_simple_adjacency_dict)
            label_digram_count = count_label_digrams(node_edge_label_adjacency_dict)

            digram_to_replace = get_digram_to_replace(grammar, simple_digram_count, label_digram_count, logic)
            new_rule = create_new_rule_for_digram(digram_to_replace, grammar, advanced)
    if used_simple_digrams + used_label_digrams == 0:
        return -1
    return used_label_digrams / (used_simple_digrams + used_label_digrams)


def calculate_changes(grammar: Grammar, parameter_paths: ParameterPaths) -> list[ChangeHelper]:
    if DEBUG:
        print("Calculate Changes for each rule")
    helpers: dict[int, ChangeHelper] = dict()
    unused_nonterminal_generator = grammar.get_unused_nonterminal_generator()
    seen_needed_paths: list[ParameterPath] = list()
    seen_needed_position: list[EdgePosition] = list()
    for rule, graph in grammar.rules.items():
        helpers[rule] = ChangeHelper(rule, graph, unused_nonterminal_generator)
    for path in parameter_paths:
        helpers[path.get_end().rule].add_position_to_change(path.get_end(), path.get_parameter(), True)
        label = grammar[path.get_end().rule][path.get_end().position_in_rule].label
        if get_node_type(label) == NodeType.NODE:
            helpers[path.get_end().rule]._to_delete_in_copy.add(label)
        for position in reversed(path.get_intermediate()):
            helpers[position.rule].add_position_to_delete(position, True)
            if get_node_type(position.edge_label) == NodeType.RULE:
                helpers[position.rule].add_position_to_change(
                    EdgePosition(position.rule, position.position_in_rule), helpers[position.edge_label].new_rule, True
                )
        helpers[path.get_start().rule].add_position_to_delete(path.get_start(), False)
        if get_node_type(path.get_start().edge_label) == NodeType.RULE:
            helpers[path.get_start().rule].add_position_to_change(
                EdgePosition(path.get_start().rule, path.get_start().position_in_rule),
                helpers[path.get_start().edge_label].new_rule,
                False
            )
        for needed_path in path.get_all_needed_paths():
            if needed_path not in seen_needed_paths:
                seen_needed_paths.append(needed_path)
                if needed_path.get_end() not in seen_needed_position:
                    seen_needed_position.append(needed_path.get_end())
                    helpers[needed_path.get_end().rule].add_position_to_change(
                        needed_path.get_end(), helpers[needed_path.get_end().rule].get_max_node_number_plus_1(), False
                    )
                for position in reversed(needed_path.get_intermediate()):
                    if position not in seen_needed_position:
                        seen_needed_position.append(position)
                        helpers[position.rule].add_node_to_edge(
                            EdgePosition(position.rule, position.position_in_rule),
                            helpers[position.rule].get_max_node_number_plus_1()
                        )
                helpers[needed_path.get_start().rule].add_node_to_edge(
                    EdgePosition(needed_path.get_start().rule, needed_path.get_start().position_in_rule),
                    helpers[needed_path.get_parameter()].new_rule
                )

    return list(helpers.values())


def prune(grammar: Grammar):
    did_change = True
    while did_change:
        did_change = False
        parameter_paths, unfinished_paths = get_all_parameter_paths(grammar)
        if len(unfinished_paths) > 0:
            if DEBUG:
                print("The grammar has parameter paths which are not ending.")

        for rule_to_prune, call in calculate_rule_call_counts(grammar, parameter_paths).items():
            if should_continue_inserting_rules(rule_to_prune, call, grammar):
                if DEBUG:
                    print("Prune: ", call)

                if call.total_calls_as_parameter > 0:
                    if DEBUG:
                        print(
                            f"Rule {rule_to_prune} has {call.total_calls_as_parameter} calls as parameter. Start Converting them to normal calls first")
                    rule_helpers = calculate_changes(grammar, call.get_parameter_paths())

                    if DEBUG:
                        print("Perform Changes")
                    for helper in rule_helpers:
                        if helper.copy:
                            grammar.rules[helper.new_rule] = deepcopy(grammar[helper.rule])

                        for position, new_value in helper.to_change_in_copy.items():
                            if isinstance(position, ExtendedPosition):
                                old_nodes = list(grammar.rules[helper.new_rule][position.position_in_rule].nodes)
                                old_nodes[position.position_in_edge] = new_value
                                grammar.rules[helper.new_rule][position.position_in_rule].nodes = old_nodes
                            else:
                                grammar.rules[helper.new_rule][position.position_in_rule].label = new_value
                        for position, new_value in helper.to_change.items():
                            if isinstance(position, ExtendedPosition):
                                if helper.copy:
                                    old_nodes = list(grammar.rules[helper.new_rule][position.position_in_rule].nodes)
                                    old_nodes[position.position_in_edge] = new_value
                                    grammar.rules[helper.new_rule][position.position_in_rule].nodes = old_nodes
                                old_nodes = list(grammar.rules[helper.rule][position.position_in_rule].nodes)
                                old_nodes[position.position_in_edge] = new_value
                                grammar.rules[helper.rule][position.position_in_rule].nodes = old_nodes
                            else:
                                if helper.copy:
                                    grammar.rules[helper.new_rule][position.position_in_rule].label = new_value
                                grammar.rules[helper.rule][position.position_in_rule].label = new_value

                        position_helper: dict[int, set[int]] = dict()
                        for position in helper.to_delete_positions_in_copy:
                            if position.position_in_rule in position_helper:
                                position_helper[position.position_in_rule].add(position.position_in_edge)
                            else:
                                position_helper[position.position_in_rule] = {position.position_in_edge}
                        for edge_index, node_indices in position_helper.items():
                            old_nodes = list(grammar.rules[helper.new_rule][edge_index].nodes)
                            for node_index in sorted(node_indices, reverse=True):
                                del old_nodes[node_index]
                            grammar.rules[helper.new_rule][edge_index].nodes = old_nodes
                        position_helper: dict[int, set[int]] = dict()
                        for position in helper.to_delete_positions:
                            if position.position_in_rule in position_helper:
                                position_helper[position.position_in_rule].add(position.position_in_edge)
                            else:
                                position_helper[position.position_in_rule] = {position.position_in_edge}
                        for edge_index, node_indices in position_helper.items():
                            old_nodes = list(grammar.rules[helper.rule][edge_index].nodes)
                            for node_index in sorted(node_indices, reverse=True):
                                del old_nodes[node_index]
                            grammar.rules[helper.rule][edge_index].nodes = old_nodes
                            if helper.copy:
                                old_nodes = list(grammar.rules[helper.new_rule][edge_index].nodes)
                                for node_index in sorted(node_indices, reverse=True):
                                    del old_nodes[node_index]
                                grammar.rules[helper.new_rule][edge_index].nodes = old_nodes

                        for edge_position, nodes in helper.to_add.items():
                            edge = grammar[helper.rule][edge_position.position_in_rule]
                            old_nodes = list(edge.nodes)
                            old_nodes.extend(nodes)
                            edge.nodes = old_nodes
                            if helper.copy:
                                edge = grammar[helper.new_rule][edge_position.position_in_rule]
                                old_nodes = list(edge.nodes)
                                old_nodes.extend(nodes)
                                edge.nodes = old_nodes

                        for rule, graph in grammar.rules.items():
                            for edge_index in range(len(graph)):
                                edge = graph[edge_index]
                                for node_index in range(len(edge.nodes)):
                                    node = edge[node_index]
                                    if node == rule_to_prune:
                                        raise RuntimeError("No")

                        if helper.copy:
                            for edge_index in range(len(grammar[helper.new_rule])):
                                edge = grammar[helper.new_rule][edge_index]
                                if get_node_type(edge.label) == NodeType.NODE:
                                    edge.label -= helper.get_amount_of_smaller_deletions_in_copy(edge.label)
                                nodes = list(edge.nodes)
                                for node_index in range(len(nodes)):
                                    if get_node_type(nodes[node_index]) == NodeType.NODE:
                                        nodes[node_index] -= helper.get_amount_of_smaller_deletions_in_copy(
                                            nodes[node_index])
                                edge.nodes = nodes
                        for edge_index in range(len(grammar[helper.rule])):
                            edge = grammar[helper.rule][edge_index]
                            if get_node_type(edge.label) == NodeType.NODE:
                                edge.label -= helper.get_amount_of_smaller_deletions_in_real(edge.label)
                            nodes = list(edge.nodes)
                            for node_index in range(len(nodes)):
                                if get_node_type(nodes[node_index]) == NodeType.NODE:
                                    nodes[node_index] -= helper.get_amount_of_smaller_deletions_in_real(
                                        nodes[node_index])
                            edge.nodes = nodes

                    if DEBUG:
                        print("Done converting parameter calls to normal calls! Continuing with normal pruning")

                count_real_replacements = 0

                for rule_name in grammar:
                    graph = grammar[rule_name]
                    for index in range(len(graph)):
                        edge = graph[index]
                        if edge.get_label() == rule_to_prune:
                            edges = get_edges_for_hyperedge(edge, grammar[edge.get_label()])

                            graph[index] = edges[0]
                            graph.extend(edges[1:])

                            count_real_replacements += 1

                del grammar.rules[rule_to_prune]
                if DEBUG:
                    print(f"Successfully pruned rule {rule_to_prune} with {count_real_replacements} real replacements")
                did_change = True
                break


def get_edges_for_hyperedge(edge: Edge, graph: Graph) -> list[Edge]:
    edges: list[Edge] = list()
    for e in graph:
        label = e.get_label()
        if get_node_type(label) == NodeType.NODE:
            label = edge.get_node_from_edge(label)
        edges.append(Edge(label, *[edge.get_node_from_edge(node) for node in e.get_all_nodes()]))
    return edges


def prune_advanced(grammar: Grammar):
    did_change = True
    while did_change:
        did_change = False
        for rule, call in calculate_rule_call_counts(grammar).items():
            if should_continue_inserting_rules_advanced(rule, call, grammar):
                # ToDo: Optimierung umsetzen, also trotz call_as_parameter ein Inlinen ermöglichen (und umsetzen, falls es Speicherplatz spart)
                if DEBUG:
                    print("Prune: ", call)

                parameters = []
                index = 0
                while index < len(grammar.get_start_rule()):
                    positive_index = len(grammar.get_start_rule()) - 1 - index
                    edge = grammar.get_start_rule()[positive_index]
                    # if get_node_type(edge.get_label()) != NodeType.RULE or edge.get_label() != rule:
                    # Falls diese Kante ein Aufruf der einzusetzenden Regel ist, dann werden die Parameter einfach
                    # auf die neuen Kanten übertragen
                    new_parameters = extract_parameter_occurrences(edge, grammar.max_parameters, positive_index)
                    parameters.extend(new_parameters)
                    if get_node_type(edge.get_label()) == NodeType.PARAMETER:
                        raise RuntimeError("The start rule should not have an edge with a parameter as the label!")
                    elif get_node_type(edge.get_label()) == NodeType.RULE:  # Hyperedge
                        if edge.get_label() == rule:
                            current_position = Position(grammar.max_parameters, positive_index, -1)
                            edges = _inline_call(grammar, edge, parameters, True, current_position)
                            # Diese Kanten können keine weiteren Kanten dieser Regel beinhalten,
                            # da der Graph ansonsten unendlich viele Kanten hätte (Rekursion).
                            # Allerdings müssen die Parameter zugeordnet werden, aus diesem Grund werden diese Kanten
                            # trotzdem noch einmal durchlaufen.
                            for t in edges:
                                if get_node_type(t.get_label()) == NodeType.PARAMETER:
                                    raise RuntimeError(
                                        "The start rule should not have an edge with a parameter as the label!")
                            grammar.get_start_rule()[positive_index] = edges[0]
                            grammar.get_start_rule().insert(positive_index + 1, *edges[1:])

                            index += len(edges) - 1  # -1, weil später noch um eins erhöht wird
                            # index -= 1  # -1, weil später noch um eins erhöht wird
                        else:
                            _prune_rec_advanced(rule, grammar, edge.get_label(), parameters)
                    index += 1
                if calculate_rule_call_counts(grammar)[rule].get_rule_calls() > 0:
                    raise RuntimeError(f"Rule {rule} was pruned, but is still used in the grammar")
                del grammar.rules[rule]
                grammar.delete_parameters_marked_for_deletion()
                if DEBUG:
                    print(f"Successfully pruned rule {rule}")
                did_change = True
                # temp_grammar = grammar.__copy__()
                # decompress(temp_grammar)
                break


def _prune_rec_advanced(
        rule_to_prune,
        grammar: Grammar,
        current_rule,
        parameters: MutableSequence[ParameterOccurrence]
):
    index = 0
    while index < len(grammar[current_rule]):
        edge = grammar[current_rule][::-1][index]
        positive_index = len(grammar[current_rule]) - 1 - index

        parameter = None
        if get_node_type(edge.get_label()) == NodeType.PARAMETER:
            # If edge label is a parameter, then get the correct label from the parameters list before
            # adding the other parameters. Alternatively the new_parameters can be inserted before the
            # last parameter in the list
            parameter = parameters.pop(-1)

        # if get_node_type(edge.get_label()) != NodeType.RULE or edge.get_label() != rule:
        # Falls diese Kante ein Aufruf der einzusetzenden Regel ist, dann werden die Parameter einfach
        # auf die neuen Kanten übertragen
        new_parameters = extract_parameter_occurrences(edge, current_rule, positive_index)
        parameters.extend(new_parameters)
        if get_node_type(edge.get_label()) == NodeType.PARAMETER:
            if get_node_type(parameter.get_parameter()) == NodeType.RULE:
                edge = Edge(parameter.get_parameter(), *edge.get_all_nodes())
        if get_node_type(edge.get_label()) == NodeType.RULE:  # Hyperedge
            if edge.get_label() == rule_to_prune:
                edges = _inline_call(grammar, edge, parameters)
                # Diese Kanten können keine weiteren Kanten dieser Regel beinhalten,
                # da der Graph ansonsten unendlich viele Kanten hätte (Rekursion).
                # Daher müssen diese nicht noch einmal angefasst werden.
                grammar[current_rule][positive_index] = edges[0]
                grammar[current_rule].insert(positive_index + 1, *edges[1:])
                index += len(edges) - 1  # -1, weil später noch um eins erhöht wird
            else:
                _prune_rec_advanced(rule_to_prune, grammar, edge.get_label(), parameters)
        index += 1


def add_parameters_to_edge(
        edge: Edge,
        parameters: MutableSequence[...],
        grammar: Grammar,
        rec_call=False
) -> MutableSequence[ParameterOccurrence]:
    needed_parameters: MutableSequence[...] = list()
    if get_node_type(edge.get_label()) == NodeType.RULE:
        for inside_edge in grammar[edge.get_label()][::-1]:
            needed_parameters += add_parameters_to_edge(inside_edge, parameters, grammar, True)
    elif get_node_type(edge.get_label()) == NodeType.PARAMETER:
        parameter = parameters.pop(-1)
        needed_parameters.append(parameter)
        needed_parameters += add_parameters_to_edge(
            Edge(parameter, *edge.get_all_nodes()),
            parameters,
            grammar,
            True)
    if not rec_call:
        edge.nodes = edge.get_nodes_only() + needed_parameters[::-1] + edge.get_parameters_only()
        return parameters
    else:
        return needed_parameters


def _inline_call(
        grammar: Grammar,
        hyperedge: Edge,
        parameters: MutableSequence[ParameterOccurrence],
        inline_parameter: bool = False,
        current_position: Position = None
):
    edges = []
    used_parameters: MutableSequence[ParameterOccurrence] = list()
    graph = grammar[hyperedge.get_label()]
    for edge in graph[::-1]:
        if get_node_type(edge.get_label()) == NodeType.PARAMETER:
            parameter: ParameterOccurrence = parameters.pop(-1)
            if inline_parameter:
                grammar.add_parameter_for_deletion(parameter, True)
                edge: Edge = Edge(parameter.get_parameter(), *edge.get_all_nodes())
                if parameter.get_position().inside_position(current_position):
                    used_parameters.append(parameter)
        edge: Edge = transform_edges([edge], hyperedge, True)[0]
        # ToDo: A rule can call itself with the help of parameters!!! So jumping over these parameters is not possible in advanced case!
        # new_parameters = _get_parameters_for_edges(edge, grammar, hyperedge, parameters)
        # edges.append(Edge(edge.get_label(), *edge.get_nodes_only(), *new_parameters[::-1], *edge.get_parameters_only()))
        edges.append(edge)
    hyperedge.delete_parameters(used_parameters)
    if inline_parameter:
        remaining_parameters = hyperedge.get_parameters_only()
        for edge in edges:
            remaining_parameters = add_parameters_to_edge(edge, remaining_parameters, grammar)
        if len(remaining_parameters) > 0:
            raise RuntimeError(f"There should not be any remaining parameter, but found: {remaining_parameters}")
    return edges[::-1]


def should_continue_inserting_rules(rule_to_prune, call: RuleCallWrapper, grammar: Grammar):
    """Returns true, if the current rule makes the grammar bigger as it would be when the rule is inlined. """
    if DEBUG:
        print(f"Calculating if {rule_to_prune} should be pruned")
    if rule_to_prune is None:
        return False

    additional_rules_size = 0

    # Since the rule will be inlined the parameter also gets deleted
    # Therefore, it will get subtracted when inlining the rule.
    parameter_calls = len(call.parameter_calls)

    frequency = call.rule_calls
    used_size = grammar.rank_of_rule(rule_to_prune) + 1
    rule_size = grammar.size_of_rule(rule_to_prune)  # + 1 is not needed.
    # Because: Regeln in Liste speichern und positive Zahlen in den anderen Alphabeten verbieten.
    # z.B.: Nodes(negativ ab -32),

    if call.total_calls_as_parameter > 0:
        # Add rule copies (only the rules where the parameter is needed) to additional_size
        for rule, edge_positions in call.get_parameter_paths().get_end_positions_grouped().items():
            for edge_pos in range(len(grammar[rule].edges)):
                if edge_pos in edge_positions:
                    additional_rules_size += grammar.size_of_rule(rule_to_prune)
                else:
                    additional_rules_size += grammar[rule].edges[edge_pos].size_of()

        # Add rule copies (only rules in the path of the parameter) to additional_size
        for rule, edges_and_nodes in call.get_parameter_paths().get_intermediate_positions_grouped().items():
            copied_size = grammar.size_of_rule(rule)
            for edge_position, node_positions in edges_and_nodes.items():
                copied_size -= len(node_positions)
            additional_rules_size += copied_size

    if DEBUG:
        print(f"{rule_to_prune} is counted {frequency} times. Used size is {used_size}, Rule size is {rule_size},"
              f" Additional rules need {additional_rules_size} more space and "
              f"{rule_to_prune} has {parameter_calls} calls over parameters")
    return frequency * used_size + rule_size > frequency * rule_size + additional_rules_size - parameter_calls


def should_continue_inserting_rules_advanced(rule, call: RuleCallWrapper, grammar):
    """Returns true, if the current rule makes the grammar bigger as it would be when the rule is inlined. """
    if rule is None or call.total_calls_as_parameter > 0:
        return False
    frequency = call.rule_calls
    used_size = grammar.rank_of_rule(rule) + 1
    rule_size = grammar.size_of_rule(rule)  # + 1 is not needed.
    # Because: Regeln in Liste speichern und positive Zahlen in den anderen Alphabeten verbieten.
    # z.B.: Nodes(negativ ab -32),
    if DEBUG:
        print(f"{rule} is counted {frequency} times. Used size is {used_size}, Rule size is {rule_size}")
    # Parameters that get inserted into the rule shorten themselves out in the equation.
    # So they don't need to be in this calculation
    return frequency * used_size + rule_size > frequency * rule_size


def calculate_rule_call_counts(grammar: Grammar, parameter_paths: ParameterPaths = None) -> dict[..., RuleCallWrapper]:
    if DEBUG:
        print("Calculate Rule Call Counts based on the parameter paths")
        from progress.bar import Bar
    result = {rule: RuleCallWrapper(rule) for rule in grammar.rules.keys()}
    for rule, graph in grammar.rules.items():
        for edge_index in range(len(graph)):
            #    print(f"calculate for rule {rule} for edge at index {edge_index}")
            edge = graph[edge_index]
            if get_node_type(edge.get_label()) == NodeType.RULE:
                result[edge.get_label()].count_call()
        paths = parameter_paths.get_paths_by_parameter(rule)
        if DEBUG:
            if len(paths.paths) > 0:
                bar = Bar(f"Calculating Rule Calls for Rule {rule}", max=len(paths.paths))
        for path in paths.paths:
            if DEBUG:
                bar.next()
            result[rule].count_parameter_call(path)

        if DEBUG:
            if len(paths.paths) > 0:
                bar.finish()

    # Exclude start rule
    del result[grammar.max_parameters]

    return result


def track_parameter_down(grammar, parameter_position: Position) -> set[EdgePosition]:
    result: set[EdgePosition] = set()
    labels = [grammar[parameter_position.rule][parameter_position.position_in_rule].get_label(), ]
    if get_node_type(labels[0]) == NodeType.NODE:
        params = track_parameter_up(grammar, EdgePosition(parameter_position.rule, parameter_position.position_in_rule))
        labels = [param for param in params]
    for label in labels:
        match get_node_type(label):
            case NodeType.RULE:
                graph = grammar[label]
                for edge_index in range(len(graph)):
                    edge = graph[edge_index]
                    if edge.get_label() == parameter_position.position_in_edge:
                        result.add(EdgePosition(label, edge_index))
                    else:
                        for node_index in range(len(edge)):
                            node = edge[node_index]
                            if node == parameter_position.position_in_edge:
                                result.update(track_parameter_down(grammar, Position(label, edge_index, node_index)))
            case _:
                raise RuntimeError(f"Cannot track parameter in position {parameter_position}")
                # ToDo: The label can be a normal label, because of the up search! Handle this!!!
    return result


def track_parameter_up(grammar, position: EdgePosition | Position) -> set[...]:
    raise NotImplementedError("Not implemented yet")


def _track_parameter_up(grammar, position: Position) -> set[EdgePosition]:
    raise NotImplementedError("Not implemented yet")


def get_all_parameter_paths(grammar: Grammar) -> tuple[ParameterPaths, list[ParameterPath]]:
    if DEBUG:
        print("Calculating all Parameter Paths")
    builder = ParameterPathsBuilder()
    paths = ParameterPaths(_get_all_parameter_paths(grammar, grammar.max_parameters, builder))
    unfinished_paths = builder.paths

    return paths, unfinished_paths


def _get_all_parameter_paths(grammar: Grammar, rule: ..., builder: ParameterPathsBuilder) -> list[ParameterPath]:
    result: list[ParameterPath] = []
    graph = grammar[rule]
    node_count: dict[int, int] = dict()
    for edge in graph:
        if get_node_type(edge.get_label()) == NodeType.NODE:
            if edge.get_label() not in node_count:
                node_count[edge.get_label()] = 1
            else:
                node_count[edge.get_label()] += 1
        for node in edge:
            if get_node_type(node) == NodeType.NODE:
                if node not in node_count:
                    node_count[node] = 1
                else:
                    node_count[node] += 1
    if DEBUG:
        if rule == grammar.max_parameters:
            bar = Bar(f"Calculating all parameter paths", max=len(graph))
    for edge_index in range(len(graph)):
        if DEBUG:
            if rule == grammar.max_parameters:
                bar.next()
        edge = graph[edge_index]
        new_paths = None
        if get_node_type(edge.get_label()) == NodeType.NODE:
            new_paths = builder.finalize_paths_ending_in_edge_with_node(
                EdgePosition(rule, edge_index),
                edge.get_label(),
                node_count[edge.get_label()] > 1
            )
            node_count[edge.get_label()] -= 1
            result.extend(new_paths)

        for node_index in range(len(edge)):
            node = edge[node_index]
            match get_node_type(node):
                case NodeType.RULE:  # | NodeType.LABEL:
                    builder.start_new_path(
                        node,
                        ExtendedPosition(rule, edge_index, edge.get_label(), node_index, node),
                        new_paths
                    )
                case NodeType.NODE:
                    builder.extend_path(
                        node,
                        ExtendedPosition(rule, edge_index, edge.get_label(), node_index, node),
                        node_count[node] > 1,
                        new_paths
                    )
                    node_count[node] -= 1
        match get_node_type(edge.get_label()):
            case NodeType.RULE:
                new_paths = _get_all_parameter_paths(grammar, edge.get_label(), builder)
                result.extend(new_paths)
            case NodeType.NODE:
                if new_paths is None or len(new_paths) > 1:
                    raise RuntimeError(
                        f"The edge {edge} in rule {rule} should have only one parameter filling the label!!!")
                else:
                    parameters = {path.parameter for path in new_paths}
                    # There should be only one parameter!!! Because the code goes one path at a time!!!
                    for parameter in parameters:
                        if get_node_type(parameter) == NodeType.RULE:
                            new_paths = _get_all_parameter_paths(grammar, parameter, builder)
                            result.extend(new_paths)

    if DEBUG:
        if rule == grammar.max_parameters:
            bar.finish()

    # Checks
    for node, count in node_count.items():
        if count != 0:
            raise RuntimeError(
                f"node_count dict should only have 0 as values at this point, but node {node} has value {count}")

    return result


def decompress(grammar: Grammar):
    print("Decompressing Grammar")
    i = 0
    while i < len(grammar.get_start_rule()):
        edge = grammar.get_start_rule()[i]
        if get_node_type(edge.get_label()) == NodeType.RULE:
            new_edges: list[Edge] = get_edges_for_hyperedge(edge, grammar[edge.get_label()])
            for tmp_e in new_edges:
                if get_node_type(tmp_e.get_label()) == NodeType.LABEL:
                    for tmp_n in tmp_e.get_all_nodes():
                        if get_node_type(tmp_n) != NodeType.NODE:
                            raise RuntimeError(f"Edge {tmp_e} is terminal but contains a fake node!")

            grammar.get_start_rule()[i] = new_edges[0]
            grammar.get_start_rule().extend(new_edges[1:])
        else:
            i += 1

    grammar.rules = {grammar.max_parameters: grammar.get_start_rule()}


def decompress_advanced(grammar):
    if DEBUG:
        print("Parameters in start rule:", count_parameters_in_start_rule(grammar))

    parameters = []
    edges = []
    for edge in grammar.get_start_rule()[::-1]:
        new_parameters = extract_parameters(edge)
        parameters.extend(new_parameters)
        if get_node_type(edge.get_label()) == NodeType.PARAMETER:
            raise RuntimeError("The start rule should not have an edge with a parameter as the label!")
        elif get_node_type(edge.get_label()) == NodeType.RULE:  # Hyperedge
            edges += _decompress_rec_advanced(grammar, edge.get_label(), edge, parameters)
        else:
            edges += [edge]

    grammar.rules = {grammar.max_parameters: Graph(edges)}
    # print(grammar)


def _decompress_rec_advanced(grammar, rule, hyperedge, parameters: MutableSequence[...]):
    edges = []
    graph = grammar[rule]
    for edge in graph[::-1]:
        parameter = None
        if get_node_type(edge.get_label()) == NodeType.PARAMETER:
            # If edge label is a parameter, then get the correct label from the parameters stack before
            # adding the other parameters. Alternatively the new_parameters can be inserted before the
            # last parameter in the list
            parameter = parameters.pop(-1)
        new_parameters = extract_parameters(edge)
        parameters.extend(new_parameters)

        if get_node_type(edge.get_label()) == NodeType.PARAMETER:
            if get_node_type(parameter) == NodeType.RULE:
                temp_edge = Edge(parameter, *edge.get_all_nodes())
                edges += transform_edges(_decompress_rec_advanced(grammar, parameter, temp_edge, parameters), hyperedge)
            else:
                edges += transform_edges([Edge(parameter, *edge.nodes)], hyperedge)
                # nodes = [hyperedge[node] for node in edge]
                # edges.append(Edge(parameter, *nodes))
        elif get_node_type(edge.get_label()) == NodeType.RULE:  # Hyperedge
            edges += transform_edges(_decompress_rec_advanced(grammar, edge.get_label(), edge, parameters), hyperedge)
        else:
            edges += transform_edges([edge], hyperedge)
    return edges


def count_parameters_in_start_rule(grammar, rule=None, hyperedge=(), parameters=None):
    if rule is None:
        rule = grammar.max_parameters
    if parameters is None:
        parameters = []
    graph = grammar[rule]
    count = 0
    for edge in graph[::-1]:
        new_parameters = extract_parameters(edge)
        parameters.extend(new_parameters[::-1])
        if get_node_type(edge.get_label()) == NodeType.PARAMETER:
            parameter = parameters.pop(0)
            count += 1
            if get_node_type(parameter) == NodeType.RULE:
                count += count_parameters_in_start_rule(grammar, parameter, edge, parameters)
        elif get_node_type(edge.get_label()) == NodeType.RULE:  # Hyperedge
            count += count_parameters_in_start_rule(grammar, edge.get_label(), edge, parameters)
    return count


def get_parameter_by_position(edge, position):
    i = 0
    for node in edge:
        if (isinstance(node, int) and node < -32) or isinstance(node,
                                                                str):  # ToDo: Change -32 to grammar.max_parameters
            if i == position:
                return node
            else:
                i += 1
    raise NotImplementedError("Not implemented yet")


def get_digram_to_replace(grammar, digram_count, label_digram_count, digram_type=DigramLogic.MOST_USED) -> Digram:
    digram = _get_digram_to_replace(grammar, digram_count, label_digram_count, digram_type)
    if DEBUG:
        print(f"Try replacing digram with type: '{digram.get_type()}' Digram to replace: {digram}")
    return digram


def _get_digram_to_replace(grammar, simple_digram_count, label_digram_count, digram_logic) -> Digram:
    """
    Returns a most used digram.
    Depending on the used logic either return a edgeDigram or a labelDigram
    :param simple_digram_count: The count of all edgeDigrams
    :param label_digram_count:  The count of all labelDigrams
    :param digram_logic:  Decide the type of the digram.
    """
    if digram_logic == DigramLogic.SIMPLE:
        return get_most_used_digram(simple_digram_count)
    elif digram_logic == DigramLogic.LABEL:
        return get_most_used_digram(label_digram_count)
    elif digram_logic == DigramLogic.MOST_USED:
        simple_digram = get_most_used_digram(simple_digram_count)
        label_digram: LabelDigram = get_most_used_digram(label_digram_count)
        if simple_digram_count[simple_digram] >= label_digram_count[label_digram]:
            return simple_digram
        else:
            return label_digram
    elif digram_logic == DigramLogic.RANDOM:
        temp_type = random.choice([DigramType.SIMPLE, DigramType.LABEL])
        if temp_type == DigramType.SIMPLE:
            return get_most_used_digram(simple_digram_count)
        else:
            return get_most_used_digram(label_digram_count)
    elif digram_logic == DigramLogic.MOST_SAVE:
        simple_digram = get_most_used_digram(simple_digram_count)
        if simple_digram is None:
            return _get_digram_to_replace(grammar, simple_digram_count, label_digram_count, DigramLogic.LABEL)
        simple_m = (grammar.rank_of_rule(simple_digram[0].get_label())
                    + grammar.rank_of_rule(simple_digram[1].get_label()) - 1) + 1
        simple_n = simple_digram_count[simple_digram]
        simple_g = (grammar.rank_of_rule(simple_digram[0].get_label()) + 1
                    + grammar.rank_of_rule(simple_digram[1].get_label()) + 1)
        simple_save = (simple_n * simple_g) - (simple_n * simple_m + simple_g)

        label_digram: LabelDigram = get_most_used_digram(label_digram_count)
        if label_digram is None:
            return simple_digram
        label_m = (grammar.rank_of_rule(label_digram[0].get_label())
                   + label_digram.get_rank() - 1) + 1
        label_n = label_digram_count[label_digram]
        label_g = grammar.rank_of_rule(label_digram[0].get_label()) + 1 + label_digram.get_rank() + 1
        label_save = (label_n * label_g) - (label_n * label_m + label_g)
        if DEBUG:
            print(
                f"Most used simple digram could save: {simple_save} and the most used label digram could save: {label_save}")
        if simple_save >= label_save:
            return simple_digram
        else:
            return label_digram

    else:
        raise ValueError(f"Invalid digram logic: {digram_logic}")


def get_most_used_digram(digram_count: dict[Digram, int]) -> Digram:
    return reduce(lambda x, y: x if digram_count[x] >= digram_count[y] else y, digram_count.keys()) \
        if len(digram_count.keys()) > 0 else None


def should_continue_replacing_digram(digram, simple_digram_count, label_digram_count, new_rule, grammar):
    """Here is the place, which decides if a replacement would reduce size.
    It should be used as a decision rule, not as a prediction.
    Returns true, if it should be replaced. """
    if digram is None:
        return False
    m = new_rule.get_rule().get_rank() + 1
    if digram.get_type() == DigramType.SIMPLE:
        n = simple_digram_count[digram]
        g = grammar.rank_of_rule(digram[0].get_label()) + 1 + grammar.rank_of_rule(digram[1].get_label()) + 1
    elif digram.get_type() == DigramType.LABEL:
        n = label_digram_count[digram]
        g = grammar.rank_of_rule(digram[0].get_label()) + 1 + digram.get_rank() + 1
    else:
        raise ValueError("Invalid digram type")
    result = n * m + g < n * g
    save = (n * m + g) - (n * g)
    if DEBUG:
        print(f"Should replace: '{result}' "
              f"Save:{save} m:{m} n:{n} g:{g} Rule: '{new_rule.rule_name}' --> {new_rule.get_rule()}")
    return result


def create_node_edge_adjacency_dicts(rule, advanced):
    """Returns a dict. At index i, it contains a dict mapping an AdjacencyType to its frequency at the node i"""
    # ToDo: This does not work for advanced repair!!! Ignore fake nodes!!!
    node_edge_adjacency_dict = {}
    node_label_edge_adjacency_dict = {}
    for edge in rule:
        for connection_type in range(edge.get_rank(advanced)):
            simple_adjacency_type = SimpleAdjacencyType(edge.get_label(), connection_type)
            label_adjacency_type = LabelAdjacencyType(edge.label, connection_type, edge.get_rank(advanced))
            node = edge[connection_type]
            # Update process. Used to generate objects if they are not available.
            if node in node_edge_adjacency_dict:
                if simple_adjacency_type in node_edge_adjacency_dict[node]:
                    node_edge_adjacency_dict[node][simple_adjacency_type] += 1
                    node_label_edge_adjacency_dict[node][label_adjacency_type] += 1
                else:
                    node_edge_adjacency_dict[node][simple_adjacency_type] = 1
                    node_label_edge_adjacency_dict[node][label_adjacency_type] = 1
            else:
                node_edge_adjacency_dict[node] = {simple_adjacency_type: 1}
                node_label_edge_adjacency_dict[node] = {label_adjacency_type: 1}
    return node_edge_adjacency_dict, node_label_edge_adjacency_dict


def transform_edges(edges, hyperedge, keep_parameter=False):
    cleaned_hyperedge = _clean_edge(hyperedge)
    new_edges = []
    for edge in edges:
        nodes = []
        for node in edge:
            if get_node_type(node) == NodeType.NODE:
                nodes.append(cleaned_hyperedge[node])
            elif keep_parameter:
                nodes.append(node)
        new_edges.append(Edge(edge.get_label(), *nodes))
    return new_edges


def create_node_label_edge_adjacency_dict(rule):
    pass


def count_simple_digrams(node_edge_simple_adjacency_dict):
    """Returns a dictionary mapping digrams to their maximum occurrence-frequency. Note that the occurrence-frequency
    calculated here is just an upper bound"""
    simple_digram_count = {}
    for node in node_edge_simple_adjacency_dict.keys():
        simple_adjacency_type_dict = node_edge_simple_adjacency_dict[node]
        simple_keys = list(simple_adjacency_type_dict.keys())
        adjacency_type_count = len(simple_keys)

        # consider each pair of AdjacencyTypes at the given node as a digram.
        # Note, that digrams should have no oder of AdjacencyTypes.
        for i in range(adjacency_type_count):
            for j in range(i + 1, adjacency_type_count):
                _update_digram_count(simple_digram_count, SimpleDigram(simple_keys[i], simple_keys[j]),
                                     min(simple_adjacency_type_dict[simple_keys[i]],
                                         simple_adjacency_type_dict[simple_keys[j]]))
            # consider each self-pair as well. Note: it has another way of counting.
            _update_digram_count(simple_digram_count, SimpleDigram(simple_keys[i], simple_keys[i]),
                                 simple_adjacency_type_dict[simple_keys[i]] // 2)
    return simple_digram_count


def _update_digram_count(digram_count, digram, delta):
    """Updates the entry digram of simple_digram_count by delta. If the entry of digram would be <= 0, the entry is removed."""
    inverted_digram = digram.invert()  # Inverting Digrams is only sensible for SimpleDigrams. LabelDigrams return None
    if digram in digram_count:
        digram_count[digram] += delta
        if digram_count[digram] <= 0:
            del digram_count[digram]
    elif inverted_digram is not None and inverted_digram in digram_count:
        digram_count[inverted_digram] += delta
        if digram_count[inverted_digram] <= 0:
            del digram_count[inverted_digram]
    elif delta > 0:
        digram_count[digram] = delta


def count_label_digrams(node_label_edge_adjacency_dict):
    label_digram_count = {}
    for node, adjacency_types in node_label_edge_adjacency_dict.items():
        connection_types_by_rank = count_connection_types_by_rank(adjacency_types)

        label_adjacency_type_dict = node_label_edge_adjacency_dict[node]
        label_keys = list(label_adjacency_type_dict.keys())

        # consider each pair of AdjacencyTypes at the given node as a digram.
        # Note, that digrams should have no order of AdjacencyTypes.
        for adjacency_type, adjacency_occurrences in adjacency_types.items():
            for connection_type, connection_type_occurrences in connection_types_by_rank.items():
                for rank, occurrences in connection_type_occurrences.items():
                    digram_occurrences = 0
                    if connection_type == adjacency_type.get_connection_type():
                        digram_occurrences = min(occurrences - adjacency_occurrences, adjacency_occurrences) + (
                                adjacency_occurrences - digram_occurrences) // 2
                    else:
                        digram_occurrences = min(occurrences, adjacency_occurrences)
                    if digram_occurrences > 0:
                        digram = LabelDigram(adjacency_type, connection_type, rank)
                        if digram in label_digram_count:
                            label_digram_count[digram] += digram_occurrences
                        else:
                            label_digram_count[digram] = digram_occurrences
    return label_digram_count


def count_connection_types_by_rank(adjacency_types):
    connection_types = {}
    for adjacency_type, occurrences in adjacency_types.items():
        if adjacency_type.get_connection_type() not in connection_types:
            connection_types[adjacency_type.get_connection_type()] = {}
        if adjacency_type.get_rank() not in connection_types[adjacency_type.get_connection_type()]:
            connection_types[adjacency_type.get_connection_type()][adjacency_type.get_rank()] = occurrences
        else:
            connection_types[adjacency_type.get_connection_type()][adjacency_type.get_rank()] += occurrences
    return connection_types


def create_new_rule_for_digram(digram_to_replace, grammar, advanced):
    """Creates the new Rule object including a name of the new Rule
    Returns a DigramRuleCreator object to replace later more easily."""
    return DigramRuleCreator.get_rule_creator(digram_to_replace, grammar, advanced)


def _get_parameters_for_edges(
        edges: MutableSequence[Edge] | Edge, grammar: Grammar, hyperedge: Edge,
        parameters: MutableSequence[ParameterOccurrence]
) -> Iterable[...]:
    if isinstance(edges, Edge):
        edges = [edges]
    seen_parameters = []
    for edge in edges[::-1]:
        parameter = None
        if get_node_type(edge.get_label()) == NodeType.PARAMETER:
            # If edge label is a parameter, then get the correct label from the parameters stack before
            # adding the other parameters. Alternatively the new_parameters can be inserted before the
            # last parameter in the list
            parameter = parameters.pop(-1)
            seen_parameters.append(parameter)
        new_parameters = extract_parameters(edge)
        parameters.extend(new_parameters)

        if get_node_type(edge.get_label()) == NodeType.PARAMETER:
            if get_node_type(parameter) == NodeType.RULE:
                temp_edge = Edge(parameter, *edge.get_all_nodes())
                seen_parameters += _get_parameters_for_edges(grammar[parameter].edges, grammar, temp_edge, parameters)
        elif get_node_type(edge.get_label()) == NodeType.RULE:  # Hyperedge
            seen_parameters += _get_parameters_for_edges(grammar[edge.get_label()], grammar, edge, parameters)
    return seen_parameters


def replace_monograms(grammar: Grammar):
    start_rule = grammar.get_start_rule()

    # creates a dict mapping a monogram to a list of occurrences represented by indices of the start rule.
    monogram_count = count_monograms(start_rule)

    # get the most frequent rule
    monogram_to_replace = get_monogram_to_replace(monogram_count)
    if monogram_to_replace is not None:
        new_rule = create_new_rule_for_monogram(monogram_to_replace, grammar)

        # Main loop to replace monograms
        while should_continue_replacing_monogram(monogram_count, monogram_to_replace, new_rule, grammar):
            count_real_replacements = 0
            next_occurrence_generator = find_occurrence_of_monogram(monogram_to_replace, start_rule)
            # loop to replace all occurrences
            for index in next_occurrence_generator:
                old_edge = start_rule[index]
                if old_edge.get_label() == monogram_to_replace.get_label():
                    new_edge = new_rule.get_hyperedge_for_edge(old_edge)
                    # edge replacement
                    start_rule[index] = new_edge

                    # update of frequencies
                    update_monogram_dict(start_rule, index, old_edge, new_edge, monogram_count, monogram_to_replace)

                    # loop iteration updates: occurrences replacement loop
                    count_real_replacements += 1

            # loop iteration updates: digram replacement loop
            if count_real_replacements > 0:
                grammar.add_rule(new_rule.get_rule_name(), new_rule.get_rule())
            if monogram_to_replace in monogram_count:
                del monogram_count[monogram_to_replace]
            monogram_to_replace = get_monogram_to_replace(monogram_count)
            new_rule = create_new_rule_for_monogram(monogram_to_replace, grammar)

    if DEBUG:
        print("Successfully replaced monograms")


def get_monogram_to_replace(monogram_dict):
    """Returns the Redundant Rule type with the most occurrences"""
    return reduce(lambda x, y: x if monogram_dict[x] >= monogram_dict[y] else y, monogram_dict.keys()) \
        if len(monogram_dict.keys()) > 0 else None


def create_new_rule_for_monogram(monogram_to_replace, grammar):
    """Creates the new Rule object including a name of the new Rule
    Returns a RedundantRuleCreator object to replace later more easily"""
    return MonogramRuleCreator(monogram_to_replace, grammar)


def should_continue_replacing_monogram(monogram_dict, monogram_to_replace, new_rule, grammar):
    """Here is the place, which decides if an replacement would reduce size.
    It should be used as a decision rule, not as an prediction.
    Returns a bool """
    if monogram_to_replace is None:
        return False
    n = monogram_dict[monogram_to_replace]
    g = grammar.rank_of_rule(monogram_to_replace.get_label()) + 1
    m = new_rule.get_rule().rank() + 1
    return n * m + n * g < n * g


def find_occurrence_of_monogram(monogram_to_replace, start_rule):
    """Searches the next occurrence of a monogram within the start_rule
    Returns 1 indices pointing to the edge in the start_rule.

    We replace an edge with another one, so we can do this as a co-routine"""
    for i in range(0, len(start_rule)):
        edge = start_rule[i]
        if edge.get_label() == monogram_to_replace.get_label() \
                and edge[monogram_to_replace[1]] == edge[monogram_to_replace[2]]:
            yield i


def update_monogram_dict(start_rule, index, old_edge, new_edge, monogram_dict, replaced_monogram):
    """Updates the monogram_dict."""

    monogram_list = list(monogram_dict.keys())
    for monogram in monogram_list:

        # checks, if the Monogram is affected by the current replacement by testing,
        # in other words if the current edge is an occurrence of that monogram.
        if monogram.get_label() == old_edge.get_label() \
                and old_edge[monogram[1]] == old_edge[monogram[2]]:
            monogram_dict[monogram] -= 1
            if monogram_dict[monogram] == 0:
                del monogram_dict[monogram]
            # Check, if an occurrence must be a transform into one of a new monogram
            if monogram[1] != replaced_monogram[2] and monogram[2] != replaced_monogram[2]:
                first_type = monogram[1] - (0 if monogram[1] <= replaced_monogram[2] else 1)
                second_type = monogram[2] - (0 if monogram[2] <= replaced_monogram[2] else 1)
                if first_type < second_type:
                    new_monogram = Monogram(new_edge.get_label(), first_type, second_type)
                    if new_monogram in monogram_dict:
                        monogram_dict[new_monogram] += 1
                    else:
                        monogram_dict[new_monogram] = 1


def count_monograms(start_rule):
    """This method creates a dict listing the rules with redundant Node IDs, e.g. ('B', 1, 2, 2).
    Returns a dict mapping a Monogram to a list of indices i, so that start_rule[i] is an occurrence of that monogram.
    """
    monogram_dict = {}
    for edge_id in range(len(start_rule)):
        e = start_rule[edge_id]
        nodes_connection_type_dict = {}

        # builds a dict mapping nodes to their connection_types of edge e
        for connection_type in range(e.rank()):
            node = e[connection_type]
            if node not in nodes_connection_type_dict:
                nodes_connection_type_dict[node] = [connection_type]
            else:
                nodes_connection_type_dict[node].append(connection_type)

        # loops through the nodes and all multiple named nodes.
        for node in nodes_connection_type_dict.keys():
            connection_type_list = nodes_connection_type_dict[node]
            if len(connection_type_list) > 1:
                for i in range(len(connection_type_list)):
                    for j in range(i + 1, len(connection_type_list)):
                        monogram = Monogram(e.get_label(), connection_type_list[i], connection_type_list[j])
                        if monogram not in monogram_dict:
                            monogram_dict[monogram] = 1
                        else:
                            monogram_dict[monogram] += 1

    return monogram_dict
