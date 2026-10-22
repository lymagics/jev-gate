import yaml

from jev_gate.contracts import Gate, Mask, Settings
from jev_gate.gate import YamlGate
from jev_gate.lenient_gate import LenientGate
from jev_gate.paths import Paths


class GatesFile(Settings):
    def __init__(self, text: str, catalog: dict[str, dict]):
        self.text = text
        self.catalog = catalog

    def model(self) -> str:
        return self._document()["model"]

    def gates(self, mode: str) -> list[Gate]:
        return [
            LenientGate(
                YamlGate(gate, self._document().get("oversize", "fail")),
                [
                    entry
                    for entry in self._document().get("skip") or []
                    if gate["id"] in entry["gates"]
                ],
            )
            for gate in self._active(mode)
        ]

    def scopes(self, mode: str) -> list[str]:
        return sorted({gate["scope"] for gate in self._active(mode)})

    def queries(self) -> dict[str, dict[str, dict]]:
        result: dict[str, dict[str, dict]] = {}
        for scope, data in (self._document().get("scopes") or {}).items():
            for pack, rule in data["packs"].items():
                result.setdefault(pack, {})[scope] = rule
        return result

    def mask(self) -> Mask:
        paths = self._document().get("paths") or {}
        return Paths(paths.get("include", ["**"]), paths.get("exclude", []))

    def _active(self, mode: str) -> list[dict]:
        return [
            gate
            for gate in self._document()["gates"]
            if mode in gate.get("modes", ["diff", "full"])
            and mode in self._scopes()[gate["scope"]]["modes"]
        ]

    def _scopes(self) -> dict[str, dict]:
        custom = {
            name: {"fields": data["fields"], "modes": ["diff", "full"]}
            for name, data in (self._document().get("scopes") or {}).items()
        }
        return {**self.catalog, **custom}

    def _document(self) -> dict:
        try:
            document = yaml.safe_load(self.text)
        except yaml.YAMLError as e:
            raise Exception("The gates file is not valid YAML") from e
        return document
