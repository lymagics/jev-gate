import pytest
from hamcrest import assert_that, contains_exactly, equal_to, instance_of

from jev_gate.candidate import FieldCandidate
from jev_gate.gate import YamlGate
from jev_gate.lenient_gate import LenientGate
from jev_gate.sha import Sha
from jev_gate.span import Span
from jev_gate.verdicts import Skipped


@pytest.mark.parametrize(
    "entry",
    [
        {"path": "src/plugin/*.py", "name": "Parser"},
        {"path": "src/**"},
        {"name": "Parser"},
    ],
)
def test_refuses_a_candidate_every_set_key_matches(entry: dict):
    assert_that(
        LenientGate(YamlGate({"scope": "type"}, "fail"), [entry]).admits(
            FieldCandidate("type", "Parser", Span("src/plugin/parser.py", 12, 40), {})
        ),
        equal_to(False),
        f"A skip entry {entry} must keep the gate away from the candidate",
    )


@pytest.mark.parametrize(
    "entry",
    [
        {"path": "src/**", "name": "Lexer"},
        {"path": "lib/**/*.rb", "name": "Scanner"},
        {"name": "lexer"},
    ],
)
def test_admits_a_candidate_one_set_key_misses(entry: dict):
    assert_that(
        LenientGate(YamlGate({"scope": "type"}, "fail"), [entry]).admits(
            FieldCandidate("type", "Lexer", Span("lib/lexer.go", 3, 3), {})
        ),
        equal_to(True),
        f"A skip entry {entry} must not keep the gate away from the candidate",
    )


def test_admits_a_commit_to_an_entry_with_a_path():
    assert_that(
        LenientGate(
            YamlGate({"scope": "commit"}, "fail"), [{"path": "**", "reason": "x"}]
        ).admits(FieldCandidate("commit", "Fix it", Sha("9f" * 20), {})),
        equal_to(True),
        "A commit has no file, so a skip entry with a path must never match it",
    )


def test_excuses_a_skipped_candidate_once():
    assert_that(
        LenientGate(
            YamlGate({"id": "doer", "scope": "type"}, "fail"),
            [{"name": "Ωmega", "reason": "first"}, {"name": "Ωmega", "reason": "two"}],
        ).excuses(FieldCandidate("type", "Ωmega", Span("ω.py", 1, 1), {})),
        contains_exactly(instance_of(Skipped)),
        "A skipped candidate must give exactly one Skipped verdict",
    )


def test_excuses_nothing_the_gate_would_not_judge():
    assert_that(
        LenientGate(
            YamlGate({"id": "doer", "scope": "type", "allow": ["Kid"]}, "fail"),
            [{"name": "Kid", "reason": "a name the gate already allows"}],
        ).excuses(FieldCandidate("type", "Kid", Span("kid.kt", 8, 8), {})),
        equal_to([]),
        "An allowed candidate must give no Skipped verdict",
    )
