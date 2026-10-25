import hypernetx as hnx
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import networkx as nx

import time

from datastructure.edge import Edge
from datastructure.enums import NodeType
from repair.helper import extract_parameters, get_node_type, _clean_edge

mpl.use('Qt5Agg')


def visualize_graph(graph):
    edges = graph.edges
    edges = [list(edge) for edge in edges]

    h_graph = hnx.Hypergraph(edges)

    plt.subplots(figsize=(4, 4))
    plt.ion()
    hnx.draw(h_graph)
    wait()


def visualize_grammar(grammar, wait_for_show=False, window_title=None):
    plt.ion()
    fig, ax = plt.subplots(1, len(grammar), figsize=(len(grammar) * 5, 5))
    if window_title is not None:
        fig.canvas.manager.set_window_title(window_title)
    i = 0
    for rule, graph in grammar.rules.items():
        edges = graph.edges
        edges_dict = dict()
        for edge in edges:
            j = 0
            label = str(edge.get_label()) + "_" + str(j)
            while label in edges_dict:
                j += 1
                label = str(edge.get_label()) + "_" + str(j)
            edges_dict[label] = _clean_edge(edge)
            #edges_dict[label] = edge

        h_graph = hnx.Hypergraph(edges_dict)
        try:
            hnx.draw(h_graph, ax=ax[i])
            ax[i].set_title(f"Rule: {rule}")
            i += 1
        except TypeError:
            hnx.draw(h_graph, ax=ax)
            ax.set_title(f"Rule: {rule}")
    if wait_for_show:
        wait()
    plt.ioff()


def wait():
    plt.waitforbuttonpress()
