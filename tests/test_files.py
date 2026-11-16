import os

import pytest
from hamcrest import assert_that, contains_exactly, equal_to

from fakes import FakeTree
from jev_gate.files import Files
from jev_gate.git import GitRepository
from jev_gate.worktree import Worktree
from scratch import Scratch


def test_offers_each_text_file():
    assert_that(
        [
            candidate.name()
            for candidate in Files(FakeTree({"a.tf": "x", "b.yaml": "y: 1"}))
        ],
        contains_exactly("a.tf", "b.yaml"),
        "Every text file must be a candidate",
    )


def test_skips_binary_files():
    assert_that(
        [
            candidate.name()
            for candidate in Files(FakeTree({"p.bin": "\0\1\2", "t.txt": "ok"}))
        ],
        contains_exactly("t.txt"),
        "A file with NUL bytes must not be a text candidate",
    )


def test_states_path_and_text():
    assert_that(
        next(iter(Files(FakeTree({"in/ü.md": "# Τίτλος\n"}))))
        .state(("path", "text"))
        .payload(),
        equal_to({"path": "in/ü.md", "text": "# Τίτλος\n"}),
        "A file must state its path and text",
    )


def test_spans_the_whole_file():
    assert_that(
        next(iter(Files(FakeTree({"many.txt": "1\n2\n3\n4\n"})))).place().properties(),
        equal_to({"file": "many.txt", "line": "1"}),
        "A file must start at its first line",
    )


# TODO: Bug: a symlink to a directory crashes, see https://github.com/lymagics/jev-gate/pull/54
@pytest.mark.skip(
    reason="Bug: a symlink to a directory crashes the file scope, "
    "see https://github.com/lymagics/jev-gate/pull/54"
)
def test_skips_a_tracked_symlink_to_a_directory():
    with Scratch("files-symlink") as scratch:
        scratch.write({"shared/ß.cfg": "k=v", "notes.rst": "Ωmega"})
        os.symlink("shared", os.path.join(scratch.path, "linked"))
        scratch.commit("link a folder")
        assert_that(
            [
                candidate.name()
                for candidate in Files(
                    Worktree(GitRepository(scratch.path), scratch.path)
                )
            ],
            contains_exactly("notes.rst", "shared/ß.cfg"),
            "A symlink to a directory must not be read as a text file",
        )
