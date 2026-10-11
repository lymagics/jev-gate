import os
import re

import pytest
import yaml
from hamcrest import assert_that, has_items, matches_regexp

from jev_gate.gates_file import GatesFile
from jev_gate.valid_gates_file import ValidGatesFile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def catalog() -> dict[str, dict]:
    with open(os.path.join(ROOT, "jev_gate", "scopes.yml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def examples() -> list[str]:
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as stream:
        text = stream.read()
    return [
        block
        for block in re.findall(r"```yaml\n(.*?)```", text, re.DOTALL)
        if "uses:" not in block
    ]


@pytest.mark.parametrize("text", examples())
def test_shows_only_gates_files_that_pass_validation(text: str):
    assert_that(
        ValidGatesFile(GatesFile(text, catalog()), text, catalog()).model(),
        matches_regexp(r"^jev-\d+\.\d+\.\d+$"),
        "Every gates file in the README must pass validation and pin a model",
    )


def test_shows_a_gate_for_every_built_in_scope():
    assert_that(
        {
            gate["scope"]
            for text in examples()
            for gate in yaml.safe_load(text)["gates"]
        },
        has_items(*catalog()),
        "The README must show a gate for each built-in scope",
    )
