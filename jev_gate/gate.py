from jev_gate.contracts import Answer, Candidate, Gate, Verdict
from jev_gate.verdicts import Blocked, Fired, Passed, Skipped


class YamlGate(Gate):
    def __init__(self, data: dict, oversize: str):
        self.data = data
        self.oversize = oversize

    def name(self) -> str:
        return self.data["id"]

    def admits(self, candidate: Candidate) -> bool:
        return candidate.scope() == self.data[
            "scope"
        ] and candidate.name() not in self.data.get("allow", [])

    def excuses(self, candidate: Candidate) -> list[Verdict]:
        return []

    def fields(self) -> tuple[str, ...]:
        return tuple(self.data["state"])

    def question(self) -> str:
        return self.data["ask"]

    def verdict(self, candidate: Candidate, answer: Answer) -> Verdict:
        result: Verdict = Passed(self.name())
        if answer.oversized() and self.data.get("oversize", self.oversize) == "skip":
            result = Skipped(self.name(), candidate, "it is too large for the model")
        elif answer.oversized():
            result = Blocked(self.name(), candidate)
        elif answer.probability() > float(self.data["fail_above"]):
            result = Fired(
                self.name(),
                str(self.data.get("rule", "")),
                candidate,
                answer.probability(),
            )
        return result
