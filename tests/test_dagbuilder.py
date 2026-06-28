from pathlib import Path

import pytest

from src.dagbuilder import build_dag, execution_order, ready_steps
from src.registry import Context, Step
from tests.conftest import make_step


def test_empty_graph():
    g = build_dag([])
    assert g.number_of_nodes() == 0
    assert execution_order(g) == []
    assert ready_steps(g, set()) == []


def test_single_node_carries_step_payload():
    def run(ctx: Context) -> None:
        pass

    step = make_step("solo", run)
    g = build_dag([step])
    assert g.nodes["solo"]["step"] is step


def test_linear_execution_order():
    steps = [
        make_step("a", lambda ctx: None),
        make_step("b", lambda ctx: None, depends_on=["a"]),
        make_step("c", lambda ctx: None, depends_on=["b"]),
    ]
    assert execution_order(build_dag(steps)) == ["a", "b", "c"]


def test_diamond_graph_orders_roots_before_merge():
    steps = [
        make_step("root", lambda ctx: None),
        make_step("left", lambda ctx: None, depends_on=["root"]),
        make_step("right", lambda ctx: None, depends_on=["root"]),
        make_step("merge", lambda ctx: None, depends_on=["left", "right"]),
    ]
    order = execution_order(build_dag(steps))
    assert order.index("root") < order.index("left")
    assert order.index("root") < order.index("right")
    assert order.index("left") < order.index("merge")
    assert order.index("right") < order.index("merge")


def test_ready_steps_exposes_parallel_roots():
    steps = [
        make_step("a", lambda ctx: None),
        make_step("b", lambda ctx: None),
        make_step("c", lambda ctx: None, depends_on=["a", "b"]),
    ]
    g = build_dag(steps)
    assert set(ready_steps(g, set())) == {"a", "b"}
    assert ready_steps(g, {"a"}) == ["b"]
    assert ready_steps(g, {"a", "b"}) == ["c"]
    assert ready_steps(g, {"a", "b", "c"}) == []


def test_build_dag_unknown_dep_raises():
    with pytest.raises(ValueError, match="a -> unknown dep missing"):
        build_dag([make_step("a", lambda ctx: None, depends_on=["missing"])])


def test_build_dag_duplicate_step_name_raises():
    with pytest.raises(ValueError, match="Duplicate step_name"):
        build_dag(
            [
                make_step("a", lambda ctx: None),
                make_step("a", lambda ctx: None),
            ]
        )


@pytest.mark.parametrize(
    "steps",
    [
        [make_step("a", lambda ctx: None, depends_on=["a"])],
        [
            make_step("a", lambda ctx: None, depends_on=["b"]),
            make_step("b", lambda ctx: None, depends_on=["a"]),
        ],
        [
            make_step("a", lambda ctx: None, depends_on=["c"]),
            make_step("b", lambda ctx: None, depends_on=["a"]),
            make_step("c", lambda ctx: None, depends_on=["b"]),
        ],
    ],
)
def test_build_dag_cycle_raises(steps):
    with pytest.raises(ValueError, match="Cycle detected"):
        build_dag(steps)
