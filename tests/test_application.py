import os

from hamcrest import assert_that, calling, equal_to, has_item, raises, starts_with

from fakes import FakeConnection, FakeLog, FakeModel, OversizedModel
from jev_gate.application import Application
from scratch import Scratch

GATES = """model: jev-1.13.0
gates:
  - id: vague-type-name
    rule: eo.md 2.1
    scope: type
    state: [name]
    ask: Is `name` named after what it does rather than what it is?
    fail_above: 0.8
"""


def test_fails_the_pipeline_when_a_gate_fires():
    with Scratch("app-fires") as scratch:
        base = scratch.write({"g.yml": GATES, "a.py": "x = 1\n"}).commit("base")
        scratch.write({"a.py": "x = 1\n\nclass DataManager:\n    pass\n"}).commit("add")
        assert_that(
            Application(
                [
                    "--config",
                    os.path.join(scratch.path, "g.yml"),
                    "--base",
                    base,
                    "--root",
                    scratch.path,
                ],
                FakeConnection(FakeModel({"vague-type-name": 0.93})),
                FakeLog(),
            ).code(),
            equal_to(1),
            "A fired gate must exit with code 1",
        )


def test_passes_when_no_gate_fires():
    with Scratch("app-passes") as scratch:
        scratch.write({"g.yml": GATES, "b.py": "class Invoice:\n    pass\n"}).commit(
            "only"
        )
        assert_that(
            Application(
                [
                    "--config",
                    os.path.join(scratch.path, "g.yml"),
                    "--mode",
                    "full",
                    "--root",
                    scratch.path,
                ],
                FakeConnection(FakeModel({"vague-type-name": 0.12})),
                FakeLog(),
            ).code(),
            equal_to(0),
            "A clean run must exit with code 0",
        )


def test_judges_nothing_untouched_in_diff_mode():
    with Scratch("app-untouched") as scratch:
        base = scratch.write(
            {"g.yml": GATES, "c.py": "class Helper:\n    pass\n"}
        ).commit("base")
        scratch.write({"notes.txt": "unrelated\n"}).commit("notes")
        assert_that(
            Application(
                [
                    "--config",
                    os.path.join(scratch.path, "g.yml"),
                    "--base",
                    base,
                    "--root",
                    scratch.path,
                ],
                FakeConnection(FakeModel({"vague-type-name": 0.99})),
                FakeLog(),
            ).code(),
            equal_to(0),
            "An untouched candidate must not be judged in diff mode",
        )


def test_blocks_on_an_oversized_candidate():
    with Scratch("app-oversized") as scratch:
        scratch.write({"g.yml": GATES, "d.py": "class Huge:\n    pass\n"}).commit(
            "only"
        )
        assert_that(
            Application(
                [
                    "--config",
                    os.path.join(scratch.path, "g.yml"),
                    "--mode",
                    "full",
                    "--root",
                    scratch.path,
                ],
                FakeConnection(OversizedModel("over 32k tokens")),
                FakeLog(),
            ).code(),
            equal_to(2),
            "An oversized candidate must exit with code 2 by default",
        )


def test_summarises_the_run():
    with Scratch("app-summary") as scratch:
        scratch.write({"g.yml": GATES, "e.py": "class Ledger:\n    pass\n"}).commit(
            "only"
        )
        log = FakeLog()
        Application(
            [
                "--config",
                os.path.join(scratch.path, "g.yml"),
                "--mode",
                "full",
                "--root",
                scratch.path,
            ],
            FakeConnection(FakeModel({"vague-type-name": 0.5})),
            log,
        ).code()
        assert_that(
            log.lines,
            has_item(
                starts_with("info jev-gate: 1 gate(s) in full mode gave 1 verdict(s)")
            ),
            "The run must end with a summary line",
        )


def test_refuses_diff_mode_without_base():
    assert_that(
        calling(
            Application(
                ["--mode", "diff"], FakeConnection(FakeModel({})), FakeLog()
            ).code
        ),
        raises(Exception, "needs --base"),
        "Diff mode without a base must fail",
    )


def test_refuses_unknown_arguments():
    assert_that(
        calling(
            Application(
                ["--colour", "red"], FakeConnection(FakeModel({})), FakeLog()
            ).code
        ),
        raises(Exception, "not understood"),
        "Unknown arguments must fail",
    )


def test_accepts_a_log_format():
    with Scratch("app-log") as scratch:
        scratch.write({"g.yml": GATES, "c.py": "class Ledger:\n    pass\n"}).commit(
            "only"
        )
        assert_that(
            Application(
                [
                    "--config",
                    os.path.join(scratch.path, "g.yml"),
                    "--mode",
                    "full",
                    "--log",
                    "plain",
                    "--root",
                    scratch.path,
                ],
                FakeConnection(FakeModel({"vague-type-name": 0.07})),
                FakeLog(),
            ).code(),
            equal_to(0),
            "The log format must be an understood argument",
        )


def test_refuses_an_unknown_log_format():
    assert_that(
        calling(
            Application(
                ["--mode", "full", "--log", "json"],
                FakeConnection(FakeModel({})),
                FakeLog(),
            ).code
        ),
        raises(Exception, "not understood"),
        "An unknown log format must fail",
    )


def test_refuses_too_few_jobs():
    assert_that(
        calling(
            Application(
                ["--mode", "full", "--jobs", "0"],
                FakeConnection(FakeModel({})),
                FakeLog(),
            ).code
        ),
        raises(Exception, "--jobs"),
        "Zero jobs must fail",
    )


def test_refuses_a_missing_gates_file():
    assert_that(
        calling(
            Application(
                ["--mode", "full", "--config", "no/such/gates-ω.yml"],
                FakeConnection(FakeModel({})),
                FakeLog(),
            ).code
        ),
        raises(Exception, "cannot be read"),
        "A missing gates file must fail",
    )


def test_refuses_a_base_outside_history():
    with Scratch("app-shallow") as scratch:
        scratch.write({"g.yml": GATES}).commit("only")
        assert_that(
            calling(
                Application(
                    [
                        "--config",
                        os.path.join(scratch.path, "g.yml"),
                        "--base",
                        "0123456789abcdef0123456789abcdef01234567",
                        "--root",
                        scratch.path,
                    ],
                    FakeConnection(FakeModel({})),
                    FakeLog(),
                ).code
            ),
            raises(Exception, "GIT_DEPTH: 0"),
            "A base missing from history must fail with a hint for GitHub and GitLab",
        )
