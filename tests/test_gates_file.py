from hamcrest import assert_that, calling, contains_exactly, equal_to, raises

from jev_gate.candidate import FieldCandidate
from jev_gate.gates_file import GatesFile
from jev_gate.span import Span

CATALOG = {
    "file": {"fields": ["path", "text"], "modes": ["diff", "full"]},
    "hunk": {"fields": ["path", "before", "after"], "modes": ["diff"]},
    "type": {"fields": ["name"], "modes": ["diff", "full"]},
}


def test_gives_the_pinned_model():
    assert_that(
        GatesFile("model: jev-9.9.9\ngates: []\n", CATALOG).model(),
        equal_to("jev-9.9.9"),
        "The pinned model must be given",
    )


def test_keeps_only_gates_of_the_mode():
    assert_that(
        [
            gate.name()
            for gate in GatesFile(
                "model: m\ngates:\n"
                "  - {id: both, scope: type, state: [name], ask: q, fail_above: 0.5}\n"
                "  - {id: only-full, scope: type, state: [name], ask: q, fail_above: 0.5,"
                " modes: [full]}\n"
                "  - {id: hunky, scope: hunk, state: [after], ask: q, fail_above: 0.5}\n",
                CATALOG,
            ).gates("full")
        ],
        contains_exactly("both", "only-full"),
        "Full mode must drop diff-only gates and gates restricted to diff",
    )


def test_skips_only_the_gates_an_entry_names():
    assert_that(
        [
            gate.admits(FieldCandidate("type", "Parser", Span("p/parser.py", 1, 2), {}))
            for gate in GatesFile(
                "model: m\nskip:\n  - {gates: [named], path: 'p/*', reason: API}\n"
                "gates:\n"
                "  - {id: named, scope: type, state: [name], ask: q, fail_above: 0.5}\n"
                "  - {id: other, scope: type, state: [name], ask: q, fail_above: 0.5}\n",
                CATALOG,
            ).gates("diff")
        ],
        contains_exactly(False, True),
        "A skip entry must silence only the gates it names",
    )


def test_lists_scopes_in_use():
    assert_that(
        GatesFile(
            "model: m\ngates:\n"
            "  - {id: a, scope: type, state: [name], ask: q, fail_above: 0.1}\n"
            "  - {id: b, scope: file, state: [text], ask: q, fail_above: 0.1}\n"
            "  - {id: c, scope: type, state: [name], ask: r, fail_above: 0.2}\n",
            CATALOG,
        ).scopes("diff"),
        contains_exactly("file", "type"),
        "Each scope in use must be listed once",
    )


def test_groups_custom_queries_by_pack():
    assert_that(
        GatesFile(
            "model: m\ngates: []\nscopes:\n  story:\n    fields: [phrase]\n"
            "    packs:\n      ruby: {match: '(call) @candidate'}\n",
            CATALOG,
        ).queries(),
        equal_to({"ruby": {"story": {"match": "(call) @candidate"}}}),
        "Custom queries must be grouped by pack",
    )


def test_includes_everything_by_default():
    assert_that(
        GatesFile("model: m\ngates: []\n", CATALOG)
        .mask()
        .matches("any/where/at all.txt"),
        equal_to(True),
        "Without paths every file must be included",
    )


def test_applies_path_exclusions():
    assert_that(
        GatesFile("model: m\ngates: []\npaths:\n  exclude: ['**/*.lock']\n", CATALOG)
        .mask()
        .matches("deep/Cargo.lock"),
        equal_to(False),
        "Excluded paths must not be selected",
    )


def test_refuses_broken_yaml():
    assert_that(
        calling(GatesFile("model: [unclosed\n", CATALOG).model),
        raises(Exception, "not valid YAML"),
        "Broken YAML must fail",
    )
