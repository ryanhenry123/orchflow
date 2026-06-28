import networkx as nx
from utils.log import get_logger
from src.registry import Step

LOGGER = get_logger(__file__)


def build_dag(steps: list[Step]) -> nx.DiGraph:
    g = nx.DiGraph()
    by_name = {s.step_name: s for s in steps}

    if len(by_name) != len(steps):
        err = "Duplicate step_name"
        LOGGER.error(err)
        raise ValueError(err)

    for step in steps:
        g.add_node(step.step_name, step=step)
        for dep in step.depends_on:
            if dep not in by_name:
                err = f"{step.step_name} -> unknown dep {dep}"
                LOGGER.error(err)
                raise ValueError(err)
            g.add_edge(dep, step.step_name)

    if not nx.is_directed_acyclic_graph(g):
        cycle = nx.find_cycle(g)
        err = f"Cycle detected: {cycle}"
        LOGGER.error(err)
        raise ValueError(err)

    return g


def execution_order(g: nx.DiGraph) -> list[str]:
    return list(nx.topological_sort(g))


def ready_steps(g: nx.DiGraph, completed: set[str]) -> list[str]:
    """Steps with deps all done"""
    return [
        n
        for n in g.nodes
        if n not in completed and all(p in completed for p in g.predecessors(n))
    ]
