from typing import TextIO

from jev_gate.contracts import Log, Place


class PlainLog(Log):
    def __init__(self, stream: TextIO):
        self.stream = stream

    def error(self, place: Place, title: str, text: str):
        self._line("error", place, title, text)

    def warning(self, place: Place, title: str, text: str):
        self._line("warning", place, title, text)

    def info(self, text: str):
        self.stream.write(f"{text}\n")
        self.stream.flush()

    def _line(self, kind: str, place: Place, title: str, text: str):
        properties = place.properties()
        location = "".join(
            f"{properties[key]}:" for key in ("file", "line") if key in properties
        )
        prefix = f"{location} " if location else ""
        self.stream.write(f"{prefix}{kind}: {title}: {' '.join(text.splitlines())}\n")
        self.stream.flush()
