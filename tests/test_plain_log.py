import io

from hamcrest import assert_that, equal_to

from jev_gate.anywhere import Anywhere
from jev_gate.plain_log import PlainLog
from jev_gate.span import Span


def test_writes_an_error_as_a_compiler_line():
    stream = io.StringIO()
    PlainLog(stream).error(Span("lib/ü.py", 7, 9), "gate-α", "fired at 0.91")
    assert_that(
        stream.getvalue(),
        equal_to("lib/ü.py:7: error: gate-α: fired at 0.91\n"),
        "An error must become one line with its file, line and title",
    )


def test_writes_a_warning_without_file():
    stream = io.StringIO()
    PlainLog(stream).warning(Anywhere("ignored"), "gate-Ω", "left out 41")
    assert_that(
        stream.getvalue(),
        equal_to("warning: gate-Ω: left out 41\n"),
        "A warning without a place must start with its kind",
    )


def test_keeps_a_multiline_text_on_one_line():
    stream = io.StringIO()
    PlainLog(stream).error(Span("x,y:z.rb", 1, 1), "t", "100%\nsure\r\n::why")
    assert_that(
        stream.getvalue(),
        equal_to("x,y:z.rb:1: error: t: 100% sure ::why\n"),
        "Line breaks must not split a finding and nothing must be escaped",
    )


def test_writes_plain_info():
    stream = io.StringIO()
    PlainLog(stream).info("jev-gate: 3 verdicts")
    assert_that(
        stream.getvalue(), equal_to("jev-gate: 3 verdicts\n"), "Info must be plain text"
    )
