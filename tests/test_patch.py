import pytest
from hamcrest import assert_that, equal_to

from jev_gate.patch import Patch


def test_finds_a_touched_range():
    assert_that(
        Patch(
            "diff --git a/w.py b/w.py\n--- a/w.py\n+++ b/w.py\n@@ -3,2 +3,3 @@\n x\n+y\n z\n"
        ).touched("w.py", 1, 4),
        equal_to(True),
        "A range around an added line must be touched",
    )


def test_ignores_an_untouched_range():
    assert_that(
        Patch(
            "diff --git a/w.py b/w.py\n--- a/w.py\n+++ b/w.py\n@@ -3,2 +3,3 @@\n x\n+y\n z\n"
        ).touched("w.py", 5, 900),
        equal_to(False),
        "A range after the added line must not be touched",
    )


def test_ignores_removed_lines():
    assert_that(
        Patch(
            "diff --git a/r.c b/r.c\n--- a/r.c\n+++ b/r.c\n@@ -1,3 +1,2 @@\n a\n-b\n c\n"
        ).touched("r.c", 1, 3),
        equal_to(False),
        "A pure removal adds and edits no line",
    )


def test_splits_into_sections():
    assert_that(
        [
            section.path()
            for section in Patch(
                "diff --git a/1.md b/1.md\n--- a/1.md\n+++ b/1.md\n@@ -1 +1 @@\n-a\n+b\n"
                "diff --git a/2.md b/2.md\n--- a/2.md\n+++ b/2.md\n@@ -1 +1 @@\n-c\n+d\n"
            ).sections()
        ],
        equal_to(["1.md", "2.md"]),
        "A patch must split per file",
    )


def test_has_no_sections_when_empty():
    assert_that(
        Patch("").sections(), equal_to([]), "An empty diff must have no sections"
    )


# TODO: Bug: quoted file names keep escapes, see https://github.com/lymagics/jev-gate/pull/64
@pytest.mark.skip(
    reason="Bug: git escapes in quoted file names are kept, "
    "see https://github.com/lymagics/jev-gate/pull/64"
)
def test_finds_a_touched_range_in_a_file_with_a_quote_in_its_name():
    assert_that(
        Patch(
            'diff --git "a/say \\"hi\\".py" "b/say \\"hi\\".py"\n'
            "index 7d4290a..72f6aaf 100644\n"
            '--- "a/say \\"hi\\".py"\t\n'
            '+++ "b/say \\"hi\\".py"\t\n'
            "@@ -1 +1,3 @@\n λ = 1\n+class Q:\n+    pass\n"
        ).touched('say "hi".py', 2, 2),
        equal_to(True),
        "A line added to a file whose name git quotes must be touched",
    )
