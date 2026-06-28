import networkx as nx
from utils.log import get_logger
from src.dagbuilder import ready_steps
from src.registry import Context, Step

LOGGER = get_logger(__file__)


def run_workflow(g: nx.DiGraph, ctx: Context) -> Context:
    completed: set[str] = set()
    skipped: set[str] = set()

    while len(completed) + len(skipped) < g.number_of_nodes():
        batch = [n for n in ready_steps(g, completed) if n not in skipped]
        if not batch:
            err = "Deadlock: no runnable steps."
            LOGGER.error(err)
            raise RuntimeError(err)

        for name in batch:
            step: Step = g.nodes[name]["step"]
            try:
                result = step.caller_func(ctx)
                ctx.data[name] = result

                if step.eval_func and not step.eval_func(ctx, result):
                    skipped.add(name)
                    skipped.update(nx.descendants(g, name))
                    continue

                completed.add(name)

            except Exception as e:
                if step.failure_func:
                    step.failure_func(ctx, e)
                    skipped.add(name)
                    skipped.update(nx.descendants(g, name))
                else:
                    LOGGER.error("Step %s failed with no failure handler", name)
                    raise

    return ctx
