from jev_gate.contracts import Answer, Candidate, Gate, Verdict
from jev_gate.glob import Glob
from jev_gate.verdicts import Skipped


class LenientGate(Gate):
    def __init__(self, origin: Gate, entries: list[dict]):
        self.origin = origin
        self.entries = entries

    def name(self) -> str:
        return self.origin.name()

    def admits(self, candidate: Candidate) -> bool:
        return self.origin.admits(candidate) and not self._matching(candidate)

    def excuses(self, candidate: Candidate) -> list[Verdict]:
        found = self._matching(candidate) if self.origin.admits(candidate) else []
        return self.origin.excuses(candidate) + [
            Skipped(self.name(), candidate, str(entry["reason"])) for entry in found[:1]
        ]

    def fields(self) -> tuple[str, ...]:
        return self.origin.fields()

    def question(self) -> str:
        return self.origin.question()

    def verdict(self, candidate: Candidate, answer: Answer) -> Verdict:
        return self.origin.verdict(candidate, answer)

    def _matching(self, candidate: Candidate) -> list[dict]:
        place = candidate.place().properties()
        return [
            entry
            for entry in self.entries
            if entry.get("name", candidate.name()) == candidate.name()
            and (
                "path" not in entry
                or ("file" in place and Glob(entry["path"]).matches(place["file"]))
            )
        ]
