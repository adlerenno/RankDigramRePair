import random
from datastructure.edge import Edge
from datastructure.grammar import Grammar
from datastructure.graph import Graph


def get_test_grammar() -> Grammar:
    S = Graph([Edge(-34, -36, -35, 2, 3, 4, "c"), Edge(-35, -38, -39, 0, 1, "a")])

    g = Grammar(S, 32, lambda x: x in ["a", "b", "c"], lambda x: 2, lambda x: 3)

    A = Graph([Edge(1, 0, -37, 2, 3, 4), Edge(0, -39, 4, 3, "b"), Edge(-39, 3, 4, 5)])
    B= Graph([Edge(0,1,2,3,4), Edge(1,2,3,4)])
    C=Graph([Edge(0,1,2,3)])
    D=Graph([Edge("a",0,1),Edge("b",0,2),Edge("c",2,1)])
    E=Graph([Edge(0,2,1,3),Edge(3,1,2)])
    F=Graph([Edge("a",0,1),Edge(2,1,0)])

    g.add_rule(g.get_unused_nonterminal(), A)
    g.add_rule(g.get_unused_nonterminal(), B)
    g.add_rule(g.get_unused_nonterminal(), C)
    g.add_rule(g.get_unused_nonterminal(), D)
    g.add_rule(g.get_unused_nonterminal(), E)
    g.add_rule(g.get_unused_nonterminal(), F)

    return g


def get_best_grammar() ->Grammar:
    edges_with_same_label = [Edge("Label", random.randrange(10), random.randrange(10)) for _ in
             range(500)]
    edges_with_different_label = [Edge(f"Label{i}", random.randrange(10), random.randrange(10)) for i in range(500)]

    edge_list = {edge.label for edge in edges_with_same_label + edges_with_different_label}

    graph = Graph(edges_with_same_label + edges_with_different_label)

    return Grammar(graph, 32, lambda x: x in edge_list, lambda x: 2, lambda x: 3)