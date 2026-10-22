from jev_gate.anywhere import Anywhere
from jev_gate.contracts import Candidate, Log, Verdict


class Passed(Verdict):
    def __init__(self, gate: str):
        self.gate = gate

    def report(self, log: Log):
        pass

    def code(self) -> int:
        return 0


class Fired(Verdict):
    def __init__(self, gate: str, rule: str, candidate: Candidate, probability: float):
        self.gate = gate
        self.rule = rule
        self.candidate = candidate
        self.probability = probability

    def report(self, log: Log):
        log.error(
            self.candidate.place(),
            self.gate,
            f"{self.gate} fired on {self.candidate.name()} at {self.candidate.place()} "
            f"with probability {self.probability:.3f}"
            + (f" ({self.rule})" if self.rule else ""),
        )

    def code(self) -> int:
        return 1


class Skipped(Verdict):
    def __init__(self, gate: str, candidate: Candidate, reason: str):
        self.gate = gate
        self.candidate = candidate
        self.reason = reason

    def report(self, log: Log):
        log.warning(
            self.candidate.place(),
            self.gate,
            f"{self.gate} skipped {self.candidate.name()} at {self.candidate.place()}: "
            f"{self.reason}",
        )

    def code(self) -> int:
        return 0


class Blocked(Verdict):
    def __init__(self, gate: str, candidate: Candidate):
        self.gate = gate
        self.candidate = candidate

    def report(self, log: Log):
        log.error(
            self.candidate.place(),
            self.gate,
            f"{self.gate} could not judge {self.candidate.name()} at {self.candidate.place()} "
            "because it is too large for the model",
        )

    def code(self) -> int:
        return 2


class LeftOut(Verdict):
    def __init__(self, gate: str, field: str, count: int):
        self.gate = gate
        self.field = field
        self.count = count

    def report(self, log: Log):
        log.warning(
            Anywhere(self.gate),
            self.gate,
            f"{self.gate} left out {self.count} candidate(s) "
            f"whose language does not write down '{self.field}'",
        )

    def code(self) -> int:
        return 0
