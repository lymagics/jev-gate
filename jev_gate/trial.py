from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from jev_gate.contracts import Candidate, Candidates, Gate, Model, Verdict
from jev_gate.verdicts import LeftOut


class Trial:
    def __init__(
        self, gates: list[Gate], candidates: Candidates, model: Model, jobs: int
    ):
        self.gates = gates
        self.candidates = candidates
        self.model = model
        self.jobs = jobs

    def verdicts(self) -> list[Verdict]:
        requests: list[tuple[Candidate, dict[str, str], list[Gate]]] = []
        unknown: Counter[tuple[str, str]] = Counter()
        excused: list[Verdict] = []
        for candidate in self.candidates:
            excused.extend(v for gate in self.gates for v in gate.excuses(candidate))
            for fields, group in self._groups(candidate).items():
                state = candidate.state(fields)
                if state.known():
                    requests.append((candidate, state.payload(), group))
                else:
                    unknown.update((gate.name(), state.missing()) for gate in group)
        with ThreadPoolExecutor(max_workers=self.jobs) as pool:
            judged = list(pool.map(lambda request: self._judged(*request), requests))
        return (
            [verdict for verdicts in judged for verdict in verdicts]
            + excused
            + [
                LeftOut(gate, field, count)
                for (gate, field), count in sorted(unknown.items())
            ]
        )

    def _groups(self, candidate: Candidate) -> dict[tuple[str, ...], list[Gate]]:
        groups: dict[tuple[str, ...], list[Gate]] = {}
        for gate in self.gates:
            if gate.admits(candidate):
                groups.setdefault(tuple(sorted(gate.fields())), []).append(gate)
        return groups

    def _judged(self, candidate: Candidate, state: dict[str, str], group: list[Gate]):
        answers = self.model.answers(
            state, {gate.name(): gate.question() for gate in group}
        )
        return [gate.verdict(candidate, answers.answer(gate.name())) for gate in group]
