from abc import ABC, abstractmethod
from collections.abc import Iterator


class Repository(ABC):
    @abstractmethod
    def output(self, *args: str) -> str:
        pass


class Tree(ABC):
    @abstractmethod
    def paths(self) -> list[str]:
        pass

    @abstractmethod
    def text(self, path: str) -> str:
        pass

    @abstractmethod
    def present(self, path: str) -> bool:
        pass


class Mask(ABC):
    @abstractmethod
    def matches(self, path: str) -> bool:
        pass


class Lines(ABC):
    @abstractmethod
    def touched(self, path: str, first: int, last: int) -> bool:
        pass


class Place(ABC):
    @abstractmethod
    def touches(self, lines: Lines) -> bool:
        pass

    @abstractmethod
    def properties(self) -> dict[str, str]:
        pass


class State(ABC):
    @abstractmethod
    def known(self) -> bool:
        pass

    @abstractmethod
    def payload(self) -> dict[str, str]:
        pass

    @abstractmethod
    def missing(self) -> str:
        pass


class Candidate(ABC):
    @abstractmethod
    def scope(self) -> str:
        pass

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def place(self) -> Place:
        pass

    @abstractmethod
    def state(self, fields: tuple[str, ...]) -> State:
        pass


class Candidates(ABC):
    @abstractmethod
    def __iter__(self) -> Iterator[Candidate]:
        pass


class Answer(ABC):
    @abstractmethod
    def oversized(self) -> bool:
        pass

    @abstractmethod
    def probability(self) -> float:
        pass


class Answers(ABC):
    @abstractmethod
    def answer(self, key: str) -> Answer:
        pass


class Model(ABC):
    @abstractmethod
    def answers(self, state: dict[str, str], questions: dict[str, str]) -> Answers:
        pass


class Log(ABC):
    @abstractmethod
    def error(self, place: Place, title: str, text: str):
        pass

    @abstractmethod
    def warning(self, place: Place, title: str, text: str):
        pass

    @abstractmethod
    def info(self, text: str):
        pass


class Verdict(ABC):
    @abstractmethod
    def report(self, log: Log):
        pass

    @abstractmethod
    def code(self) -> int:
        pass


class Gate(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def admits(self, candidate: Candidate) -> bool:
        pass

    @abstractmethod
    def excuses(self, candidate: Candidate) -> list[Verdict]:
        pass

    @abstractmethod
    def fields(self) -> tuple[str, ...]:
        pass

    @abstractmethod
    def question(self) -> str:
        pass

    @abstractmethod
    def verdict(self, candidate: Candidate, answer: Answer) -> Verdict:
        pass


class Sources(ABC):
    @abstractmethod
    def candidates(self, scope: str) -> Candidates:
        pass


class Connection(ABC):
    @abstractmethod
    def model(self, version: str) -> Model:
        pass


class Settings(ABC):
    @abstractmethod
    def model(self) -> str:
        pass

    @abstractmethod
    def gates(self, mode: str) -> list[Gate]:
        pass

    @abstractmethod
    def scopes(self, mode: str) -> list[str]:
        pass

    @abstractmethod
    def queries(self) -> dict[str, dict[str, dict]]:
        pass

    @abstractmethod
    def mask(self) -> Mask:
        pass
