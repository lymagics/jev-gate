import pytest
from hamcrest import assert_that, calling, contains_exactly, raises

from jev_gate.gates_file import GatesFile
from jev_gate.valid_gates_file import ValidGatesFile

CATALOG = {
    "test": {"fields": ["phrase", "message"], "modes": ["diff", "full"]},
    "hunk": {"fields": ["path", "after"], "modes": ["diff"]},
}


def valid(text: str) -> ValidGatesFile:
    return ValidGatesFile(GatesFile(text, CATALOG), text, CATALOG)


def skipping(entries: str) -> str:
    return (
        "model: m\ngates:\n"
        "  - {id: g, scope: test, state: [phrase], ask: q, fail_above: 0.5}\n"
        f"skip: {entries}\n"
    )


def test_accepts_a_well_formed_file():
    assert_that(
        [
            gate.name()
            for gate in valid(
                "model: jev-1.13.0\noversize: skip\npaths: {include: ['**'], exclude: []}\n"
                "scopes:\n  story:\n    fields: [phrase]\n    packs:\n"
                "      ruby: {match: '(call) @candidate', fields: {}, defaults: {}}\n"
                "gates:\n"
                "  - id: failure-message-disagrees-with-name\n    rule: testing.md 1.3\n"
                "    scope: test\n    state: [phrase, message]\n    ask: Does it differ?\n"
                "    fail_above: 0.9\n    modes: [diff, full]\n    oversize: fail\n"
                "    allow: [test_legacy]\n"
                "  - {id: stories, scope: story, state: [phrase], ask: 'Is it vague?', "
                "fail_above: 0}\n"
                "skip:\n  - {gates: [stories], path: 'old/**', name: x, reason: Legacy}\n"
            ).gates("diff")
        ],
        contains_exactly("failure-message-disagrees-with-name", "stories"),
        "A well-formed gates file must give its gates",
    )


@pytest.mark.parametrize(
    "text, reason",
    [
        ("- just\n- a list\n", "must be a YAML mapping"),
        ("model: jev-1.13.0\ngates: []\nextra: 1\n", "unknown keys"),
        ("gates: []\n", "must pin a model"),
        ("model: jev-latest\ngates: []\n", "is an alias"),
        ("model: jev-preview\ngates: []\n", "is an alias"),
        ("model: m\noversize: maybe\ngates: []\n", "not fail or skip"),
        ("model: m\npaths: [a]\ngates: []\n", "'paths' must be a mapping"),
        ("model: m\npaths: {include: a}\ngates: []\n", "must be a list of strings"),
        ("model: m\npaths: {only: [a]}\ngates: []\n", "unknown keys"),
        ("model: m\ngates: []\n", "at least one gate"),
        ("model: m\ngates: [plain]\n", "must be a mapping"),
        (
            "model: m\ngates:\n  - {id: g, scope: test}\n",
            "lacks state, ask, fail_above",
        ),
        (
            (
                "model: m\ngates:\n"
                "  - {id: 'bad id', scope: test, state: [phrase], ask: q, fail_above: 0.5}\n"
            ),
            "not a plain name",
        ),
        (
            (
                "model: m\ngates:\n"
                "  - {id: g, scope: nowhere, state: [phrase], ask: q, fail_above: 0.5}\n"
            ),
            "unknown scope 'nowhere'",
        ),
        (
            (
                "model: m\ngates:\n"
                "  - {id: g, scope: test, state: [source], ask: q, fail_above: 0.5}\n"
            ),
            "does not have",
        ),
        (
            "model: m\ngates:\n  - {id: g, scope: test, state: [], ask: q, fail_above: 0.5}\n",
            "does not have",
        ),
        (
            (
                "model: m\ngates:\n"
                "  - {id: g, scope: test, state: [phrase], ask: '  ', fail_above: 0.5}\n"
            ),
            "asks nothing",
        ),
        (
            "model: m\ngates:\n  - {id: g, scope: test, state: [phrase], ask: q, fail_above: 1}\n",
            "fail_above",
        ),
        (
            (
                "model: m\ngates:\n"
                "  - {id: g, scope: test, state: [phrase], ask: q, fail_above: true}\n"
            ),
            "fail_above",
        ),
        (
            (
                "model: m\ngates:\n"
                "  - {id: g, scope: test, state: [phrase], ask: q, fail_above: 0.5, modes: [ci]}\n"
            ),
            "unknown mode",
        ),
        (
            (
                "model: m\ngates:\n"
                "  - {id: g, scope: test, state: [phrase], ask: q, fail_above: 0.5, where: {}}\n"
            ),
            "unknown keys .'where'.",
        ),
        (
            (
                "model: m\ngates:\n"
                "  - {id: g, scope: test, state: [phrase], ask: q, fail_above: 0.5}\n"
                "  - {id: g, scope: test, state: [phrase], ask: r, fail_above: 0.6}\n"
            ),
            "must be unique",
        ),
        (skipping("[{gates: [g], name: n}]"), "entry 1 gives no reason"),
        (
            skipping(
                "[{gates: [g], name: n, reason: r}, {gates: [g], name: m, reason: ' '}]"
            ),
            "entry 2 gives no reason",
        ),
        (skipping("[{gates: [], name: n, reason: r}]"), "entry 1 names no gate"),
        (
            skipping("[{gates: [g, ghost], name: n, reason: r}]"),
            "entry 1 names unknown gates .'ghost'.",
        ),
        (
            skipping("[{gates: [g], reason: r}]"),
            "entry 1 sets neither 'path' nor 'name'",
        ),
        (
            skipping("[{gates: [g], name: n, reason: r, line: 12}]"),
            "entry 1 has unknown keys .'line'.",
        ),
        (
            skipping("[{gates: [g], name: [n], reason: r}]"),
            "entry 1 needs 'path' and 'name' as text",
        ),
        (skipping("[plain]"), "entry 1 must be a mapping"),
        (skipping("{gates: [g]}"), "'skip' must be a list"),
        ("model: m\nscopes: [x]\ngates: []\n", "'scopes' must be a mapping"),
        (
            "model: m\nscopes:\n  test: {fields: [a], packs: {}}\ngates: []\n",
            "reuses a built-in",
        ),
        ("model: m\nscopes:\n  s: plain\ngates: []\n", "must be a mapping"),
        (
            "model: m\nscopes:\n  s: {fields: [], packs: {}}\ngates: []\n",
            "must declare fields",
        ),
        (
            "model: m\nscopes:\n  s: {fields: [a], packs: {}}\ngates: []\n",
            "at least one pack",
        ),
        (
            "model: m\nscopes:\n  s: {fields: [a], packs: {ruby: {}}}\ngates: []\n",
            "needs a 'match'",
        ),
        ("model: [broken\n", "not valid YAML"),
    ],
)
def test_refuses_malformed_files(text: str, reason: str):
    assert_that(
        calling(valid(text).model), raises(Exception, reason), f"It must fail: {reason}"
    )


def test_refuses_an_unknown_mode():
    assert_that(
        calling(
            valid(
                "model: m\ngates:\n"
                "  - {id: g, scope: test, state: [phrase], ask: q, fail_above: 0.5}\n"
            ).gates
        ).with_args("partial"),
        raises(Exception, "'diff' or 'full'"),
        "An unknown mode must fail",
    )


def test_checks_before_giving_scopes():
    assert_that(
        calling(valid("model: jev-latest\n").scopes).with_args("diff"),
        raises(Exception, "alias"),
        "Scopes must not be given from an invalid file",
    )


def test_checks_before_giving_queries():
    assert_that(
        calling(valid("model: m\ngates: 3\n").queries),
        raises(Exception, "at least one gate"),
        "Queries must not be given from an invalid file",
    )


def test_checks_before_giving_the_mask():
    assert_that(
        calling(valid("oversize: skip\n").mask),
        raises(Exception, "pin a model"),
        "A mask must not be given from an invalid file",
    )
