import os
import subprocess
import sys

import pytest
from hamcrest import all_of, assert_that, contains_string, equal_to, is_not

from scratch import Scratch

pytestmark = pytest.mark.deep

GATES = """model: jev-1.13.0
gates:
  - {id: g, scope: file, state: [text], ask: Is it empty?, fail_above: 0.5}
"""


def run(arguments: list[str], key: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "jev_gate", *arguments],
        capture_output=True,
        check=False,
        text=True,
        timeout=120,
        env={**os.environ, "TYPESAFE_API_KEY": key},
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )


def test_exits_with_two_without_an_api_key():
    with Scratch("main-key") as scratch:
        scratch.write({"g.yml": GATES}).commit("only")
        assert_that(
            run(
                [
                    "--config",
                    os.path.join(scratch.path, "g.yml"),
                    "--mode",
                    "full",
                    "--root",
                    scratch.path,
                ],
                "",
            ).returncode,
            equal_to(2),
            "A missing key must exit with code 2",
        )


def test_explains_the_failure_as_an_annotation():
    with Scratch("main-annotation") as scratch:
        scratch.write({"g.yml": "model: jev-latest\ngates: []\n"}).commit("only")
        assert_that(
            run(
                [
                    "--config",
                    os.path.join(scratch.path, "g.yml"),
                    "--mode",
                    "full",
                    "--root",
                    scratch.path,
                ],
                "k",
            ).stdout,
            contains_string("::error title=jev-gate::"),
            "A failure must print one error annotation with its reasons",
        )


def test_explains_the_failure_as_a_plain_line():
    with Scratch("main-plain") as scratch:
        scratch.write({"p.yml": "model: jev-newest\ngates: []\n"}).commit("one")
        assert_that(
            run(
                [
                    "--log",
                    "plain",
                    "--config",
                    os.path.join(scratch.path, "p.yml"),
                    "--mode",
                    "full",
                    "--root",
                    scratch.path,
                ],
                "key-π",
            ).stdout,
            all_of(contains_string("error: jev-gate: "), is_not(contains_string("::"))),
            "A plain failure must print one readable line without workflow commands",
        )
