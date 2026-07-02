from orchflow.evals.context import Context
from orchflow.evals.turn import Turn
from orchflow.providers.aws.messages import (
    build_converse_messages,
    cache_point,
    text_block,
)


def test_cached_initial_message():
    turn = Turn(1, [], [])
    msgs = build_converse_messages(turn, initial="Write a memo.", cache_initial=True)
    assert msgs[0]["content"][0] == text_block("Write a memo.")
    assert msgs[0]["content"][1] == cache_point()


def test_retry_keeps_cache_on_initial():
    turn = Turn(2, ["draft"], ["fix sizing"])
    msgs = build_converse_messages(turn, initial="Write a memo.", cache_initial=True)
    assert msgs[0]["content"][1] == cache_point()
    assert len(msgs) == 3
