import random
import statistics
from collections.abc import Iterable

from datastructure.enums import DigramLogic
from datastructure.grammar import Grammar
from datastructure.helper import BenchmarkResult
from examples.randomExamples import get_random_grammar
from repair.algorithms import repair

activate_visualizer = False
DEBUG = False

if activate_visualizer:
    from visualize import visualizer


def main():
    """
    This is the starting point of this code. It was written for python version 3.12.3
    Below one can define which random graphs should get generated and on which strategies/logics these graphs should get testet.
    They are given as a tuple.
    One can also define how many repeats should be performed. For 10 repeats the algorithm will generate 10 random graphs for each configuration.
    Note, that the different logics get tested on the same graphs, so that comparisons between these logics is easily possible.

    Currently only advanced=False is supported!
    """
    # grammar = get_random_grammar(10, 1000, 10)
    # test_compression(grammar, DigramLogic.MOST_SAVE, False)

    logics = (DigramLogic.SIMPLE, DigramLogic.LABEL, DigramLogic.MOST_SAVE,)
    advanced = (False,)
    node_counts = (10,)
    edge_counts = (1000,)
    different_edge_counts = (10,)
    repeats = 10

    benchmark_random_grammar_multi(logics, advanced, node_counts, edge_counts, different_edge_counts, repeats)


def test_compression(grammar, logic, advanced):
    size_before = grammar.get_start_rule().size_of()

    if activate_visualizer:
        visualizer.visualize_grammar(grammar, wait_for_show=False, window_title="Original Grammar")

    label_percent = repair(grammar, logic, advanced)

    if activate_visualizer:
        visualizer.visualize_grammar(grammar, wait_for_show=False, window_title="Compressed Grammar")

    print(f"Size before compression: {size_before}")
    print(f"Size after compression: {grammar.size_of_whole_grammar()}")
    print(f"Ratio: {grammar.size_of_whole_grammar() / size_before}")
    print(f"Label Percent: {label_percent}")


def benchmark_compression_rate(grammar: Grammar, logic: DigramLogic, advanced: bool) -> BenchmarkResult:
    old_size = grammar.size_of_whole_grammar()
    label_digram_percent = repair(grammar, logic, advanced)
    new_size = grammar.size_of_whole_grammar()
    return BenchmarkResult(new_size / old_size, label_digram_percent)


def benchmark_compression_rate_random_grammar(logic: DigramLogic, advanced: bool, node_count, edge_count,
                                              different_edge_count, repeats=1, seed=None) -> Iterable[BenchmarkResult]:
    results = []
    for i in range(repeats):
        grammar = get_random_grammar(node_count, edge_count, different_edge_count, seed)
        result = benchmark_compression_rate(grammar, logic, advanced)
        results.append(result)
        if seed is not None:
            seed += 1
    return results


def analyse_compression(results: Iterable[BenchmarkResult], opt_string=None):
    mean = statistics.mean((result.compression_rate for result in results))
    median = statistics.median((result.compression_rate for result in results))
    variance = statistics.variance((result.compression_rate for result in results))

    digram_mean = statistics.mean((result.label_digram_percent for result in results))
    digram_median = statistics.median((result.label_digram_percent for result in results))
    digram_variance = statistics.variance((result.label_digram_percent for result in results))
    print("----Compression rates----")
    if opt_string is not None:
        print(opt_string)
    print(f"Mean: {mean}")
    print(f"Median: {median}")
    print(f"Variance: {variance}")
    print("---LabelDigram percent---")
    print(f"---Mean: {digram_mean}")
    print(f"---Median: {digram_median}")
    print(f"---Variance: {digram_variance}")
    print("-------------------------")
    return mean


def benchmark_random_grammar_multi(logics, advanced, node_counts, edge_counts, different_edge_counts, repeats=1):
    if not isinstance(logics, Iterable):
        logics = [logics, ]
    if not isinstance(advanced, Iterable):
        advanced = [advanced, ]
    if not isinstance(node_counts, Iterable):
        node_counts = [node_counts, ]
    if not isinstance(edge_counts, Iterable):
        edge_counts = [edge_counts, ]
    if not isinstance(different_edge_counts, Iterable):
        different_edge_counts = [different_edge_counts, ]

    rates = dict()

    for node_count in node_counts:
        for edge_count in edge_counts:
            for different_edge_count in different_edge_counts:
                seed = random.randint(1, 100000)
                for logic in logics:
                    for a in advanced:
                        while True:
                            benchmark_results = benchmark_compression_rate_random_grammar(logic, a, node_count,
                                                                                          edge_count,
                                                                                          different_edge_count, repeats,
                                                                                          seed)
                            describing_string = f"Logic:'{logic}' Advanced:{a} Nodes:{node_count} Edges:{edge_count} DifferentEdges:{different_edge_count}"
                            mean = analyse_compression(benchmark_results, describing_string)
                            rates[describing_string] = mean
                            break

    min_describing_string = min(rates, key=rates.get)
    print(f"Best compression ({rates[min_describing_string]}) with settings: {min_describing_string}")


if __name__ == "__main__":
    main()
