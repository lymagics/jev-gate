import re


class Hunk:
    def __init__(self, path: str, text: str):
        self.path = path
        self.text = text

    def line(self) -> int:
        header = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", self.text)
        if header is None:
            raise Exception(f"The hunk of '{self.path}' has no readable header")
        return int(header.group(1))

    def before(self) -> str:
        return "".join(line[1:] for line in self._body() if line[:1] in (" ", "-"))

    def after(self) -> str:
        return "".join(line[1:] for line in self._body() if line[:1] in (" ", "+"))

    def added(self) -> set[int]:
        numbers = set()
        cursor = self.line()
        for line in self._body():
            if line[:1] == "+":
                numbers.add(cursor)
            if line[:1] in (" ", "+"):
                cursor += 1
        return numbers

    def _body(self) -> list[str]:
        return re.split(r"(?<=\n)", self.text)[1:]
