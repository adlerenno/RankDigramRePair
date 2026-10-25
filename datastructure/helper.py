from copy import deepcopy
from typing import Self, Any, Generator

from scipy.constants import grain

from datastructure.enums import NodeType


class EdgePosition:

    def __init__(self, rule, position_in_rule: int):
        self.rule = rule
        self.position_in_rule: int = position_in_rule

    def __str__(self):
        return f"{self.rule}, {self.position_in_rule}"

    def __eq__(self, other: Self) -> bool:
        return self.rule == other.rule and self.position_in_rule == other.position_in_rule

    __repr__ = __str__

    def __hash__(self):
        return hash((self.rule, self.position_in_rule))


class Position(EdgePosition):

    def __init__(self, rule, position_in_rule, position_in_edge):
        super().__init__(rule, position_in_rule)
        self.position_in_edge = position_in_edge

    def inside_position(self, other) -> bool:
        """
        Returns true if and only if both position are inside the same rule and edge.
        :param other: The other position
        :return: True if both position are inside the same rule and edge, False otherwise
        """
        return super().__eq__(other)

    def __eq__(self, other: Self) -> bool:
        if isinstance(other, Position):
            return super().__eq__(other) and self.position_in_edge == other.position_in_edge
        else:
            return super().__eq__(other)

    def __str__(self):
        return f"({super().__str__()}, {self.position_in_edge})"

    __repr__ = __str__

    def __hash__(self):
        return hash((self.rule, self.position_in_rule, self.position_in_edge))


class ExtendedPosition(Position):
    def __init__(self, rule, position_in_rule, edge_label, position_in_edge, node):
        super().__init__(rule, position_in_rule, position_in_edge)
        self.node = node
        self.edge_label = edge_label

    def __eq__(self, other: Self) -> bool:
        if not isinstance(other, ExtendedPosition):
            return False
        tmp = super().__eq__(other) and self.edge_label == other.edge_label and self.node == other.node
        return tmp

    def __hash__(self):
        return hash((self.rule, self.position_in_rule, self.edge_label, self.position_in_edge))

    def get_as_edge_position(self):
        return EdgePosition(self.rule, self.position_in_rule)


class ParameterOccurrence:
    def __init__(self, parameter, position: Position):
        self.parameter = parameter
        self.position = position

    def get_parameter(self):
        return self.parameter

    def get_position(self):
        return self.position

    def __str__(self):
        return f"{self.parameter}: {self.position}"

    __repr__ = __str__


class BenchmarkResult:

    def __init__(self, compression_rate, label_digram_percent):
        self.compression_rate = compression_rate
        self.label_digram_percent = label_digram_percent


class ParameterPath:

    def __init__(self, parameter, parameter_position: ExtendedPosition):
        self.parameter = parameter
        self.path: list[ExtendedPosition] = [parameter_position, ]
        self.edge_at_the_end: EdgePosition | None = None

        self.needed_paths: dict[EdgePosition, list[Self]] = dict()

    def get_parameter(self) -> ...:
        return self.parameter

    def get_start(self) -> ExtendedPosition:
        return self.path[0]

    def get_intermediate(self) -> list[ExtendedPosition]:
        return self.path[1:]

    def get_end(self) -> EdgePosition:
        return self.edge_at_the_end

    def get_needed_path_for_edge(self, edge_position: EdgePosition) -> list[Self]:
        return self.needed_paths[edge_position]

    def get_all_needed_paths(self) -> list[Self]:
        return [path for path_list in self.needed_paths.values() for path in path_list]

    def __eq__(self, other: Self) -> bool:
        return (self.parameter == other.parameter and
                self.path == other.path and
                self.edge_at_the_end == other.edge_at_the_end and
                self._needed_paths_similar(other.needed_paths))

    def _needed_paths_similar(self, other_needed_paths: dict[EdgePosition, list[Self]]) -> bool:
        for edge_pos, paths in self.needed_paths.items():
            if edge_pos not in other_needed_paths:
                return False
            self_parameters = {path.parameter for path in paths}
            other_parameters = {path.parameter for path in other_needed_paths[edge_pos]}
            if self_parameters != other_parameters:
                return False
        return True

    def __str__(self):
        return f"({self.parameter}: {self.path}, ({self.edge_at_the_end}) | {self.needed_paths})"

    __repr__ = __str__

    def includes_position(self, position: ExtendedPosition):
        for p in self.path:
            if p == position:
                return True


class ParameterPathsBuilder:

    def __init__(self):
        self.paths: list[ParameterPath] = []

    def start_new_path(
            self, parameter, parameter_position: ExtendedPosition, needed_paths: list[ParameterPath]
    ) -> None:
        new_path = ParameterPath(parameter, parameter_position)
        if needed_paths is not None:
            edge_position = EdgePosition(parameter_position.rule, parameter_position.position_in_rule)
            new_path.needed_paths[edge_position] = needed_paths
        self.paths.append(new_path)

    def finalize_paths_ending_in_edge_with_node(
            self, edge_position: EdgePosition, node: int, copy: bool
    ) -> list[ParameterPath]:
        result: list[ParameterPath] = list()
        index = 0
        while index < len(self.paths):
            path = self.paths[index]
            current_end = path.path[-1]
            from datastructure.edge import get_node_type
            match get_node_type(current_end.edge_label):
                case NodeType.RULE:
                    if current_end.edge_label == edge_position.rule and current_end.position_in_edge == node:
                        if copy:
                            self.paths[index] = deepcopy(path)
                        path.edge_at_the_end = edge_position
                        result.append(path)
                        if not copy:
                            del self.paths[index]
                        else:
                            index += 1
                    else:
                        index += 1
                case NodeType.NODE:
                    current_end_as_edge = EdgePosition(current_end.rule, current_end.position_in_rule)
                    if current_end_as_edge not in path.needed_paths.keys():
                        raise RuntimeError(f"Needed Path was not added to the parameter path!")
                    if (edge_position.rule in [path.get_start().node for path in path.needed_paths[current_end_as_edge]]
                            and current_end.position_in_edge == node):
                        if copy:
                            self.paths[index] = deepcopy(path)
                        path.edge_at_the_end = edge_position
                        result.append(path)
                        if not copy:
                            del self.paths[index]
                        else:
                            index += 1
                    else:
                        index += 1
                case _:
                    raise RuntimeError(f"Unexpected node type")
        if len(result) > 1:
            raise RuntimeError(f"There are multiple paths ending at the edge {edge_position}! Paths: {result}")
            # This should not happen, because the code goes one path at a time!!!
        return result

    def extend_path(
            self, node: int, position: ExtendedPosition, copy: bool, needed_paths: list[ParameterPath]
    ) -> None:
        index = 0
        while index < len(self.paths):
            path = self.paths[index]
            current_end = path.path[-1]
            from datastructure.edge import get_node_type
            match get_node_type(current_end.edge_label):
                case NodeType.RULE:
                    if current_end.edge_label == position.rule and current_end.position_in_edge == node:
                        if copy:
                            self.paths.insert(index, deepcopy(path))
                            index += 1
                        path.path.append(position)
                        if needed_paths is not None:
                            edge_position = EdgePosition(position.rule, position.position_in_rule)
                            if edge_position in path.needed_paths:
                                raise RuntimeError(
                                    f"Needed Path with the same End was already added to the neededParameters!")
                                # path.needed_paths[edge_position].extend(needed_paths)
                            else:
                                path.needed_paths[edge_position] = needed_paths
                    index += 1
                case NodeType.NODE:
                    current_end_as_edge = EdgePosition(current_end.rule, current_end.position_in_rule)
                    if current_end_as_edge not in path.needed_paths.keys():
                        raise RuntimeError(f"Needed Path was not added to the parameter path!")
                    if (position.rule in [path.get_start().node for path in path.needed_paths[current_end_as_edge]]
                            and current_end.position_in_edge == node):
                        if copy:
                            self.paths.insert(index, deepcopy(path))
                            index += 1
                        path.path.append(position)
                        if needed_paths is not None:
                            edge_position = EdgePosition(position.rule, position.position_in_rule)
                            if edge_position in path.needed_paths:
                                path.needed_paths[edge_position].extend(needed_paths)
                            else:
                                path.needed_paths[edge_position] = needed_paths
                    index += 1
                case _:
                    raise RuntimeError(f"Unexpected node type")


class ParameterPaths:

    def __init__(self, paths: list[ParameterPath]):
        self.paths: list[ParameterPath] = paths

    def get_ends_by_start(self, parameter_position: Position) -> list[EdgePosition]:
        return [path.get_end() for path in self.paths if path.get_start() == parameter_position]

    def get_paths_by_start(self, parameter_position: ExtendedPosition) -> Self:
        paths = []
        for path in self.paths:
            if path.get_start() == parameter_position:
                paths.append(path)
        return ParameterPaths(paths)


    def get_paths_by_parameter(self, parameter) -> Self:
        return ParameterPaths([path for path in self.paths if path.parameter == parameter])

    def __iter__(self):
        return self.paths.__iter__()

    def get_start_positions_grouped(self) -> dict[Any, dict[int, set[int]]]:
        result: dict[Any, dict[int, set[int]]] = dict()
        for path in self.paths:
            pos = path.get_start()
            if pos.rule not in result:
                result[pos.rule] = {pos.position_in_rule: {pos.position_in_edge, }}
            else:
                if pos.position_in_rule not in result[pos.rule]:
                    result[pos.rule][pos.position_in_rule] = {pos.position_in_edge, }
                else:
                    result[pos.rule][pos.position_in_rule].add(pos.position_in_edge)
        return result

    def get_end_positions_grouped(self) -> dict[Any, set[int]]:
        return {path.get_end().rule: {inner_path.get_end().position_in_rule
                                      for inner_path in self.paths
                                      if path.get_end().rule == inner_path.get_end().rule}
                for path in self.paths}

    def get_positions_grouped(self) -> dict[Any, dict[int, set[int]]]:
        result: dict[Any, dict[int, set[int]]] = dict()
        for path in self.paths:
            for pos in path.path:
                if pos.rule not in result:
                    result[pos.rule] = {pos.position_in_rule: {pos.position_in_edge, }}
                else:
                    if pos.position_in_rule not in result[pos.rule]:
                        result[pos.rule][pos.position_in_rule] = {pos.position_in_edge, }
                    else:
                        result[pos.rule][pos.position_in_rule].add(pos.position_in_edge)
        return result

    def get_intermediate_positions_grouped(self) -> dict[Any, dict[int, set[int]]]:
        result: dict[Any, dict[int, set[int]]] = dict()
        for path in self.paths:
            for pos in path.get_intermediate():
                if pos.rule not in result:
                    result[pos.rule] = {pos.position_in_rule: {pos.position_in_edge, }}
                else:
                    if pos.position_in_rule not in result[pos.rule]:
                        result[pos.rule][pos.position_in_rule] = {pos.position_in_edge, }
                    else:
                        result[pos.rule][pos.position_in_rule].add(pos.position_in_edge)
        return result

    def includes_position(self, position: ExtendedPosition) -> bool:
        for path in self.paths:
            if path.includes_position(position):
                return True

    def get_by_end(self, edge_pos: EdgePosition) -> Self:
        return ParameterPaths([path for path in self.paths if path.get_end() == edge_pos])

    def get_label_with_other_path(self, path: ParameterPath):
        possible_paths = list(range(len(self.paths)))
        for index in range(1, len(path.path)+1):
            possible_labels = {self.paths[i].parameter for i in possible_paths}
            match len(possible_labels):
                case 0:
                    raise RuntimeError("It is not possible to find exactly one label for that start")
                case 1:
                    return self.paths[possible_labels.pop()].parameter
            position = path.path[-index]
            for i in possible_paths:
                if len(self.paths) > i:
                    possible_paths.remove(i)
                possible_path = self.paths[i]
                if possible_path.path[-index] != position:
                    possible_paths.remove(i)
        possible_labels = {self.paths[i].parameter for i in possible_paths}
        if len(possible_labels) == 1:
            return self.paths[possible_labels.pop()].parameter
        else:
            raise RuntimeError("It is not possible to find exactly one label for that start")




class RuleCallWrapper:
    def __init__(self, rule):
        self.rule = rule
        self.rule_calls: int = 0
        self.parameter_calls: list[list[ParameterPath | int]] = []
        self.total_calls_as_parameter: int = 0

    def count_call(self):
        self.rule_calls += 1

    def get_rule_calls(self) -> int:
        return self.rule_calls

    def count_parameter_call(self, path: ParameterPath):
        self.total_calls_as_parameter += 1
        for c_path in self.parameter_calls:
            if c_path[0] == path:
                c_path[1] += 1
                break
        else:
            self.parameter_calls.append([path, 1])

    def __str__(self):
        return "Rule: " + str(self.rule) + " with count: " + str(
            self.rule_calls) + " and parameter count (total:" + str(self.total_calls_as_parameter) + ")"

    __repr__ = __str__

    def get_parameter_paths(self) -> ParameterPaths:
        return ParameterPaths([path for path, _ in self.parameter_calls])


class ChangeHelper:
    def __init__(self, rule, graph, new_rule_generator: Generator[int, Any, None]):
        from datastructure.graph import Graph
        self.rule = rule
        self.graph: Graph = graph
        self._new_rule_generator = new_rule_generator
        self._new_rule = rule
        self.to_change: dict[EdgePosition, Any] = dict()
        self.to_change_in_copy: dict[EdgePosition, Any] = dict()
        self.to_add: dict[EdgePosition, list[int]] = dict()
        self._to_delete_in_real: set[int] = set()
        self._to_delete_in_copy: set[int] = set()
        self.to_delete_positions: set[ExtendedPosition] = set()
        self.to_delete_positions_in_copy: set[ExtendedPosition] = set()
        self._copy = False


    @property
    def new_rule(self):
        if self.copy:
            return self._new_rule
        else:
            raise RuntimeError("Can not access new_rule without copy being set to True")

    @property
    def copy(self) -> bool:
        return self._copy

    @copy.setter
    def copy(self, copy: bool):
        if not copy and self._copy:
            raise ValueError("Copy should not be changed back to False")
        if not self._copy and copy:
            self._new_rule = next(self._new_rule_generator)
        self._copy = copy

    def check_integrity(self):
        for edge_index in range(len(self.graph)):
            edge = self.graph[edge_index]
            if ((edge.get_label() in self._to_delete_in_copy)
            ) and (
                    EdgePosition(self.rule, edge_index) not in self.to_change.keys() and
                    EdgePosition(self.rule, edge_index) not in self.to_change_in_copy.keys()
            ):
                raise RuntimeError(f"IntegrityError in rule {self.rule} for edge label at index {edge_index}")
            if ((edge.get_label() in self._to_delete_in_real)
            ) and (
                    EdgePosition(self.rule, edge_index) not in self.to_change.keys()
            ):
                raise RuntimeError(f"IntegrityError in rule {self.rule} for edge label at index {edge_index}")
            for node_index in range(len(edge)):
                node = edge[node_index]
                if (
                        (node in self._to_delete_in_copy) !=
                        (ExtendedPosition(
                            self.rule, edge_index, edge.get_label(), node_index, node
                        ) in self.to_delete_positions.union(self.to_delete_positions_in_copy))
                ) and (
                        ExtendedPosition(
                            self.rule, edge_index, edge.get_label(), node_index, node
                        ) not in self.to_change.keys() and
                        ExtendedPosition(
                            self.rule, edge_index, edge.get_label(), node_index, node
                        ) not in self.to_change_in_copy.keys()
                ):
                    raise RuntimeError(
                        f"IntegrityError in rule {self.rule} in edge at index {edge_index} for node at index {node_index}")
                if (
                        (node in self._to_delete_in_real) !=
                        (ExtendedPosition(
                            self.rule, edge_index, edge.get_label(), node_index, node
                        ) in self.to_delete_positions)
                ) and (
                        ExtendedPosition(
                            self.rule, edge_index, edge.get_label(), node_index, node
                        ) not in self.to_change.keys()
                ):
                    raise RuntimeError(
                        f"IntegrityError in rule {self.rule} in edge at index {edge_index} for node at index {node_index}")

    def add_node_to_edge(self, edge_position: EdgePosition, node_number: int):
        if edge_position in self.to_add:
            self.to_add[edge_position].append(node_number)
        else:
            self.to_add[edge_position] = [node_number]

    def add_position_to_change(self, position: EdgePosition, new_node, only_in_copy: bool, add_to_delete=False):
        if only_in_copy:
            if position not in self.to_change_in_copy:
                self.copy = True
                self.to_change_in_copy[position] = new_node
        else:
            if position not in self.to_change:
                self.to_change[position] = new_node

    def add_position_to_delete(self, position: ExtendedPosition, only_in_copy: bool):
        from datastructure.edge import get_node_type
        if only_in_copy:
            self.copy = True
            self.to_delete_positions_in_copy.add(position)
            if get_node_type(position.node) == NodeType.NODE:
                self._to_delete_in_copy.add(position.node)
        else:
            self.to_delete_positions.add(position)
            if get_node_type(position.node) == NodeType.NODE:
                self._to_delete_in_real.add(position.node)
                self._to_delete_in_copy.add(position.node)

    def get_amount_of_smaller_deletions_in_copy(self, node_number):
        return len([number for number in self._to_delete_in_copy if number < node_number])

    def get_amount_of_smaller_deletions_in_real(self, node_number):
        return len([number for number in self._to_delete_in_real if number < node_number])

    def get_max_node_number_plus_1(self):
        from datastructure.edge import get_node_type
        all_nodes = {node
                           for edge in self.graph.edges
                           for node in set(edge.nodes).union({edge.label})
                           if get_node_type(node) == NodeType.NODE}
        for node_list in self.to_add.values():
            for node in node_list:
                if get_node_type(node) == NodeType.NODE:
                    all_nodes.add(node)
        for node in self.to_change.values():
            if get_node_type(node) == NodeType.NODE:
                all_nodes.add(node)
        return max(all_nodes) + 1

    def get_smallest_unused_node_number(self):
        from datastructure.edge import get_node_type
        result = 0
        seen_nodes = set()
        for node_list in self.to_add.values():
            for node in node_list:
                if get_node_type(node) == NodeType.NODE:
                    seen_nodes.add(node)
        for node in self.to_change.values():
            if get_node_type(node) == NodeType.NODE:
                seen_nodes.add(node)
        for edge in self.graph:
            if get_node_type(edge.get_label()) == NodeType.NODE:
                seen_nodes.add(edge.get_label())
            for node in edge:
                if get_node_type(node) == NodeType.NODE:
                    seen_nodes.add(node)

        for node in sorted(seen_nodes):
            if result == node:
                result += 1
            else:
                return result
        return result


class SetLikeList(set):

    def __init__(self):
        self.list = []
        super().__init__()

    def add_element(self, __element, other):
        if __element not in self:
            self.list.append((__element, other))
        super().add(__element)

    def get_all(self):
        return self.list

