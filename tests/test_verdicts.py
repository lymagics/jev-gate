import pytest
from hamcrest import assert_that, contains_exactly, empty, equal_to

from fakes import FakeLog
from jev_gate.candidate import FieldCandidate
from jev_gate.contracts import Verdict
from jev_gate.span import Span
from jev_gate.verdicts import Blocked, Fired, LeftOut, Passed, Skipped


@pytest.mark.parametrize(
    "verdict, code",
    [
        (Passed("g"), 0),
        (Fired("g", "r", FieldCandidate("type", "T", Span("t.go", 1, 1), {}), 0.9), 1),
        (Skipped("g", FieldCandidate("file", "big", Span("big", 1, 1), {}), "r"), 0),
        (Blocked("g", FieldCandidate("file", "big", Span("big", 1, 1), {})), 2),
        (LeftOut("g", "returns", 3), 0),
    ],
)
def test_gives_its_exit_code(verdict: Verdict, code: int):
    assert_that(
        verdict.code(),
        equal_to(code),
        f"{type(verdict).__name__} must exit with {code}",
    )


def test_passed_reports_nothing():
    log = FakeLog()
    Passed("quiet").report(log)
    assert_that(log.lines, empty(), "A pass must print nothing")


def test_fired_reports_gate_place_and_probability():
    log = FakeLog()
    Fired(
        "name-lies",
        "naming.md 2.1",
        FieldCandidate("type", "Manager", Span("m.py", 7, 9), {}),
        0.9312,
    ).report(log)
    assert_that(
        log.lines,
        contains_exactly(
            "error {'file': 'm.py', 'line': '7'} name-lies: name-lies fired on Manager at m.py:7 "
            "with probability 0.931 (naming.md 2.1)"
        ),
        "A violation must name gate, place, probability and rule",
    )


def test_skipped_warns_about_the_candidate():
    log = FakeLog()
    Skipped(
        "big-gate",
        FieldCandidate("file", "dump.sql", Span("dump.sql", 1, 1), {}),
        "Seed data, never read by people",
    ).report(log)
    assert_that(
        log.lines,
        contains_exactly(
            "warning {'file': 'dump.sql', 'line': '1'} big-gate: big-gate skipped dump.sql at "
            "dump.sql:1: Seed data, never read by people"
        ),
        "A skip must warn and name the candidate and the reason",
    )


def test_blocked_errors_about_the_candidate():
    log = FakeLog()
    Blocked(
        "big-gate", FieldCandidate("file", "a.min.js", Span("a.min.js", 1, 1), {})
    ).report(log)
    assert_that(
        log.lines,
        contains_exactly(
            "error {'file': 'a.min.js', 'line': '1'} big-gate: big-gate could not judge a.min.js "
            "at a.min.js:1 because it is too large for the model"
        ),
        "A block must fail and name the candidate",
    )


def test_left_out_warns_with_the_count():
    log = FakeLog()
    LeftOut("returns-bool", "returns", 17).report(log)
    assert_that(
        log.lines,
        contains_exactly(
            "warning {} returns-bool: returns-bool left out 17 candidate(s) whose language "
            "does not write down 'returns'"
        ),
        "Left-out candidates must be counted in one warning",
    )
