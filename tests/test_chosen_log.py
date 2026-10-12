import io

import pytest
from hamcrest import assert_that, equal_to

from jev_gate.chosen_log import ChosenLog
from jev_gate.span import Span


@pytest.mark.parametrize(
    ("args", "line"),
    [
        (["--log", "plain"], "q.java:5: error: g: hit\n"),
        (["--mode", "full", "--log=plain"], "q.java:5: error: g: hit\n"),
        ([], "::error file=q.java,line=5,title=g::hit\n"),
        (["--log", "github"], "::error file=q.java,line=5,title=g::hit\n"),
        (["--log", "teletype"], "::error file=q.java,line=5,title=g::hit\n"),
        (["--log"], "::error file=q.java,line=5,title=g::hit\n"),
    ],
)
def test_writes_in_the_format_the_arguments_ask_for(args: list[str], line: str):
    stream = io.StringIO()
    ChosenLog(args, stream).error(Span("q.java", 5, 6), "g", "hit")
    assert_that(stream.getvalue(), equal_to(line), f"{args} must pick the right log")


def test_writes_a_plain_warning():
    stream = io.StringIO()
    ChosenLog(["--log", "plain"], stream).warning(Span("w.ts", 88, 90), "h", "out")
    assert_that(
        stream.getvalue(),
        equal_to("w.ts:88: warning: h: out\n"),
        "A warning must reach the chosen log",
    )


def test_writes_info_unchanged():
    stream = io.StringIO()
    ChosenLog(["--log", "plain"], stream).info("jev-gate: 12 gate(s)")
    assert_that(
        stream.getvalue(),
        equal_to("jev-gate: 12 gate(s)\n"),
        "Info must reach the chosen log",
    )
