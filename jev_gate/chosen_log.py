import argparse
from typing import TextIO

from jev_gate.contracts import Log, Place
from jev_gate.github_log import GithubLog
from jev_gate.plain_log import PlainLog


class ChosenLog(Log):
    def __init__(self, args: list[str], stream: TextIO):
        self.args = args
        self.stream = stream

    def error(self, place: Place, title: str, text: str):
        self._origin().error(place, title, text)

    def warning(self, place: Place, title: str, text: str):
        self._origin().warning(place, title, text)

    def info(self, text: str):
        self._origin().info(text)

    def _origin(self) -> Log:
        parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
        parser.add_argument("--log", nargs="?", const="github", default="github")
        name = parser.parse_known_args(self.args)[0].log
        return {"plain": PlainLog}.get(name, GithubLog)(self.stream)
