import re

from jev_gate.hunk import Hunk


class Section:
    def __init__(self, text: str):
        self.text = text

    def path(self) -> str:
        names = {
            side: self._unquoted(name)
            for side, name in re.findall(
                r"^(---|\+\+\+) (.+?)\t?$",
                re.split(r"^@@ ", self.text, maxsplit=1, flags=re.MULTILINE)[0],
                re.MULTILINE,
            )
        }
        chosen = names.get("+++", "/dev/null")
        if chosen == "/dev/null":
            chosen = names.get("---", self._header())
        return re.sub(r"^[ab]/", "", chosen)

    def hunks(self) -> list[Hunk]:
        pieces = re.split(r"^(?=@@ )", self.text, flags=re.MULTILINE)[1:]
        return [Hunk(self.path(), piece) for piece in pieces]

    def __str__(self) -> str:
        return self.text

    def _header(self) -> str:
        found = re.match(
            r"diff --git (?:\"?a/.+?\"?) \"?(b/.+?)\"?$", self.text, re.MULTILINE
        )
        if found is None:
            raise Exception("The diff section names no file")
        return found.group(1)

    def _unquoted(self, name: str) -> str:
        return name[1:-1] if len(name) > 1 and name[0] == name[-1] == '"' else name
