import random

from datastructure.edge import Edge
from datastructure.grammar import Grammar
from datastructure.graph import Graph


def get_random_grammar(node_count, edge_count, different_edge_count, seed=None) -> Grammar:
    seed = seed if seed is not None else random.randint(1, 10000)
    random.seed(seed)
    edge_list = list(map(lambda x: "edge{}".format(x), range(0, different_edge_count)))
    edges = [Edge(random.choice(edge_list), random.randrange(node_count), random.randrange(node_count)) for _ in
             range(edge_count)]

    graph = Graph(edges)

    return Grammar(graph, 32, lambda x: x in edge_list, lambda x: 2, lambda x: 3)


def get_random_test_grammar():
    edges = [Edge('edge0', 1, 0),
             Edge('edge0', 2, 2),
             Edge('edge0', 1, 2),
             Edge('edge0', 2, 0), ]

    graph = Graph(edges)

    def terminal_func(edge_label):
        result = edge_label in ['edge0', ]
        return result

    return Grammar(graph, 32, terminal_func, lambda x: 2, lambda x: 3)


def get_grammar_from_edges(edges):
    real_edges = list()
    nodes_list = set()
    for edge in edges:
        real_edges.append(Edge(edge[0], *edge[1:]))
        nodes_list.add(edge[0])

    graph = Graph(real_edges)

    def terminal_func(edge_label):
        result = edge_label in nodes_list
        return result

    return Grammar(graph, 32, terminal_func, lambda x: 2, lambda x: 3)

