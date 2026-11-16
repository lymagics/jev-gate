import os

import pytest
from hamcrest import assert_that, contains_exactly, equal_to

from fakes import FakeLines, FakeTree
from jev_gate.changed_tests import ChangedTests
from jev_gate.directory import PackDirectory


def packs():
    return PackDirectory(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "jev_gate", "packs")
    ).packs()


def test_offers_edited_tests_only():
    assert_that(
        [
            candidate.name()
            for candidate in ChangedTests(
                FakeTree(
                    {
                        "t.py": "def test_a():\n    assert 1\n\ndef test_b():\n    assert 2\n"
                    }
                ),
                FakeTree(
                    {
                        "t.py": "def test_a():\n    assert 10\n\ndef test_b():\n    assert 2\n\n"
                        "def test_new():\n    assert 3\n"
                    }
                ),
                packs(),
                FakeLines({"t.py": {2, 7, 8}}),
            )
        ],
        contains_exactly("test_a"),
        "Only tests that existed and changed must be offered",
    )


def test_states_both_versions():
    assert_that(
        next(
            iter(
                ChangedTests(
                    FakeTree({"s.rb": 'it "works" do\n  assert true\nend\n'}),
                    FakeTree({"s.rb": 'it "works" do\n  refute false\nend\n'}),
                    packs(),
                    FakeLines({"s.rb": {2}}),
                )
            )
        )
        .state(("before", "after"))
        .payload(),
        equal_to(
            {
                "before": 'it "works" do\n  assert true\nend',
                "after": 'it "works" do\n  refute false\nend',
            }
        ),
        "A changed test must state both versions",
    )


def test_ignores_tests_of_new_files():
    assert_that(
        list(
            ChangedTests(
                FakeTree({}),
                FakeTree({"new_test.py": "def test_fresh():\n    assert 1\n"}),
                packs(),
                FakeLines({"new_test.py": {1, 2}}),
            )
        ),
        equal_to([]),
        "A test in a new file must not count as changed",
    )


# TODO: Bug: a new test is paired with an older namesake in another class, see https://github.com/lymagics/jev-gate/pull/53
@pytest.mark.skip(
    reason="Bug: a new test is paired with an older namesake, see https://github.com/lymagics/jev-gate/pull/53"
)
def test_ignores_new_test_that_shares_a_name_with_an_old_one():
    assert_that(
        list(
            ChangedTests(
                FakeTree(
                    {
                        "shelf_test.py": "class TestCart:\n"
                        "    def test_empty(self):\n"
                        "        assert 41\n"
                    }
                ),
                FakeTree(
                    {
                        "shelf_test.py": "class TestCart:\n"
                        "    def test_empty(self):\n"
                        "        assert 41\n"
                        "\n\nclass TestShelf:\n"
                        "    def test_empty(self):\n"
                        "        assert 97\n"
                    }
                ),
                packs(),
                FakeLines({"shelf_test.py": {4, 5, 6, 7, 8}}),
            )
        ),
        equal_to([]),
        "A brand-new test must not count as a changed version of an older test "
        "with the same name in another class",
    )
