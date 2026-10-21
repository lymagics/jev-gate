from hamcrest import assert_that, calling, equal_to, has_length, raises

from jev_gate.section import Section


def test_names_the_new_path():
    assert_that(
        Section(
            "diff --git a/old name.py b/old name.py\nindex 1..2 100644\n"
            "--- a/old name.py\n+++ b/old name.py\n@@ -1 +1 @@\n-a\n+b\n"
        ).path(),
        equal_to("old name.py"),
        "A section must name the file it changes",
    )


def test_names_the_old_path_of_a_deleted_file():
    assert_that(
        Section(
            "diff --git a/gone.rb b/gone.rb\ndeleted file mode 100644\n"
            "--- a/gone.rb\n+++ /dev/null\n@@ -1 +0,0 @@\n-x\n"
        ).path(),
        equal_to("gone.rb"),
        "A deleted file must be named by its old path",
    )


def test_names_a_binary_file_from_its_header():
    assert_that(
        Section(
            "diff --git a/img/логотип.png b/img/логотип.png\n"
            "Binary files a/img/логотип.png and b/img/логотип.png differ\n"
        ).path(),
        equal_to("img/логотип.png"),
        "A binary file must be named from the diff header",
    )


def test_unquotes_quoted_paths():
    assert_that(
        Section(
            'diff --git "a/tab\\there.txt" "b/tab\\there.txt"\n'
            '--- "a/tab\\there.txt"\n+++ "b/tab\\there.txt"\n@@ -1 +1 @@\n-1\n+2\n'
        ).path(),
        equal_to("tab\\there.txt"),
        "A quoted path must lose its quotes",
    )


def test_refuses_a_section_without_files():
    assert_that(
        calling(Section("diff --git nonsense\n").path),
        raises(Exception, "names no file"),
        "A section without file names must fail",
    )


def test_splits_into_hunks():
    assert_that(
        Section(
            "diff --git a/k.ts b/k.ts\n--- a/k.ts\n+++ b/k.ts\n"
            "@@ -1 +1 @@\n-a\n+b\n@@ -40 +40 @@\n-c\n+d\n"
        ).hunks(),
        has_length(2),
        "A section must hold each of its hunks",
    )


def test_prints_its_text():
    assert_that(
        str(Section("diff --git a/q b/q\n")),
        equal_to("diff --git a/q b/q\n"),
        "A section must print its raw text",
    )


def test_names_the_file_despite_an_added_line_that_looks_like_a_header():
    assert_that(
        Section(
            "diff --git a/lib/zq.py b/lib/zq.py\n--- a/lib/zq.py\n+++ b/lib/zq.py\n"
            "@@ -1 +1,2 @@\n kept\n+++ 7 odd\n"
        ).path(),
        equal_to("lib/zq.py"),
        "A body line starting with '+++ ' must not rename the file",
    )
