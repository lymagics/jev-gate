from hamcrest import assert_that, calling, equal_to, raises

from jev_gate.hunk import Hunk


def test_reads_its_new_start_line():
    assert_that(
        Hunk("m.py", "@@ -10,3 +12,4 @@ def run():\n a\n-b\n+c\n+d\n e\n").line(),
        equal_to(12),
        "A hunk must start where the new side starts",
    )


def test_reads_a_single_line_header():
    assert_that(
        Hunk("one.txt", "@@ -1 +1 @@\n-old\n+new\n").line(),
        equal_to(1),
        "A header without counts must still give a line",
    )


def test_refuses_a_broken_header():
    assert_that(
        calling(Hunk("bad.c", "@@ garbage @@\n+x\n").line),
        raises(Exception, "bad.c"),
        "A broken header must fail and name the file",
    )


def test_keeps_the_old_side():
    assert_that(
        Hunk("s.sql", "@@ -1,3 +1,3 @@\n keep\n-gone\n+born\n tail\n").before(),
        equal_to("keep\ngone\ntail\n"),
        "The old side must hold context and removed lines",
    )


def test_keeps_the_new_side():
    assert_that(
        Hunk("s.sql", "@@ -4,2 +4,3 @@\n ctx\n-was\n+is\n+also\n").after(),
        equal_to("ctx\nis\nalso\n"),
        "The new side must hold context and added lines",
    )


def test_numbers_added_lines_on_the_new_side():
    assert_that(
        Hunk(
            "n.go",
            "@@ -5,4 +7,5 @@\n a\n-b\n+B\n c\n+D\n\\ No newline at end of file\n",
        ).added(),
        equal_to({8, 10}),
        "Added lines must be numbered on the new side",
    )


def test_keeps_an_added_line_with_a_form_feed_whole():
    assert_that(
        Hunk("ff.py", "@@ -1 +1,2 @@\n x\n+q\x0cz\n+w\n").after(),
        equal_to("x\nq\x0cz\nw\n"),
        "A form feed inside a line must not split the line",
    )
