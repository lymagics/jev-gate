import pytest
from hamcrest import assert_that, calling, contains_exactly, equal_to, raises

from fakes import BrokenModel, EchoModel, FakeCandidates, FakeModel, OversizedModel
from jev_gate.candidate import FieldCandidate
from jev_gate.gate import YamlGate
from jev_gate.lenient_gate import LenientGate
from jev_gate.span import Span
from jev_gate.trial import Trial


def gate(name: str, scope: str, state: list[str], threshold: float) -> YamlGate:
    return YamlGate(
        {
            "id": name,
            "scope": scope,
            "state": state,
            "ask": f"{name}?",
            "fail_above": threshold,
        },
        "fail",
    )


def test_gives_exit_codes_per_gate_and_candidate():
    assert_that(
        [
            verdict.code()
            for verdict in Trial(
                [
                    gate("loud", "type", ["name"], 0.5),
                    gate("calm", "type", ["name"], 0.5),
                ],
                FakeCandidates(
                    [FieldCandidate("type", "Mgr", Span("m.cs", 4, 9), {"name": "Mgr"})]
                ),
                FakeModel({"loud": 0.97, "calm": 0.03}),
                2,
            ).verdicts()
        ],
        contains_exactly(1, 0),
        "Each gate must judge each admitted candidate",
    )


def test_shares_one_request_among_gates_with_the_same_state():
    assert_that(
        [
            verdict.code()
            for verdict in Trial(
                [gate("a", "type", ["name"], 0.15), gate("b", "type", ["name"], 0.15)],
                FakeCandidates(
                    [FieldCandidate("type", "T", Span("t.go", 1, 1), {"name": "T"})]
                ),
                EchoModel(0.1),
                1,
            ).verdicts()
        ],
        contains_exactly(1, 1),
        "Two gates with one state must be asked in one request of two questions",
    )


def test_splits_requests_by_state_fields():
    assert_that(
        [
            verdict.code()
            for verdict in Trial(
                [
                    gate("one", "test", ["phrase"], 0.15),
                    gate("two", "test", ["message", "phrase"], 0.15),
                ],
                FakeCandidates(
                    [
                        FieldCandidate(
                            "test",
                            "t",
                            Span("t.py", 1, 1),
                            {"phrase": "p", "message": "m"},
                        )
                    ]
                ),
                EchoModel(0.1),
                1,
            ).verdicts()
        ],
        contains_exactly(0, 1),
        "Gates with different state must not see each other's fields",
    )


def test_asks_nothing_for_a_skipped_gate():
    assert_that(
        [
            verdict.code()
            for verdict in Trial(
                [
                    gate("judged", "type", ["name"], 0.5),
                    LenientGate(
                        gate("excused", "type", ["name"], 0.5),
                        [{"name": "Handler", "reason": "The SDK names it"}],
                    ),
                ],
                FakeCandidates(
                    [
                        FieldCandidate(
                            "type", "Handler", Span("h.py", 2, 5), {"name": "H"}
                        )
                    ]
                ),
                FakeModel({"judged": 0.99}),
                1,
            ).verdicts()
        ],
        contains_exactly(1, 0),
        "A skipped gate must not be asked, while the other gate still judges",
    )


def test_counts_candidates_left_out_for_unwritten_facts():
    assert_that(
        [
            verdict.count
            for verdict in Trial(
                [gate("returns-bool", "function", ["name", "returns"], 0.5)],
                FakeCandidates(
                    [
                        FieldCandidate(
                            "function", "f", Span("a.js", 1, 1), {"name": "f"}
                        ),
                        FieldCandidate(
                            "function", "g", Span("a.js", 5, 5), {"name": "g"}
                        ),
                    ]
                ),
                FakeModel({}),
                1,
            ).verdicts()
        ],
        contains_exactly(2),
        "Candidates without a written fact must be counted once per gate",
    )


def test_blocks_oversized_candidates():
    assert_that(
        [
            verdict.code()
            for verdict in Trial(
                [gate("whole-file", "file", ["text"], 0.5)],
                FakeCandidates(
                    [FieldCandidate("file", "huge", Span("huge", 1, 1), {"text": "…"})]
                ),
                OversizedModel("64k"),
                1,
            ).verdicts()
        ],
        contains_exactly(2),
        "An oversized candidate must block by default",
    )


def test_fails_when_the_model_fails():
    assert_that(
        calling(
            Trial(
                [gate("g", "type", ["name"], 0.5)],
                FakeCandidates(
                    [FieldCandidate("type", "X", Span("x", 1, 1), {"name": "X"})]
                ),
                BrokenModel("rate limited after retries"),
                3,
            ).verdicts
        ),
        raises(Exception, "rate limited"),
        "A model failure must stop the trial",
    )


@pytest.mark.repeat(3)
def test_keeps_verdict_order_under_threads():
    assert_that(
        [
            verdict.candidate.name()
            for verdict in Trial(
                [gate("g", "variable", ["name"], 0.0)],
                FakeCandidates(
                    [
                        FieldCandidate(
                            "variable",
                            f"v{index}",
                            Span("v.py", index, index),
                            {"name": "x"},
                        )
                        for index in range(1, 201)
                    ]
                ),
                FakeModel({"g": 0.5}),
                16,
            ).verdicts()
        ],
        equal_to([f"v{index}" for index in range(1, 201)]),
        "Verdicts must keep candidate order when judged in parallel",
    )
