import re

import yaml

from jev_gate.contracts import Gate, Mask, Settings


class ValidGatesFile(Settings):
    def __init__(self, origin: Settings, text: str, catalog: dict[str, dict]):
        self.origin = origin
        self.text = text
        self.catalog = catalog

    def model(self) -> str:
        self._check()
        return self.origin.model()

    def gates(self, mode: str) -> list[Gate]:
        self._check()
        self._require(
            mode in ("diff", "full"), f"The mode must be 'diff' or 'full', not '{mode}'"
        )
        return self.origin.gates(mode)

    def scopes(self, mode: str) -> list[str]:
        self._check()
        return self.origin.scopes(mode)

    def queries(self) -> dict[str, dict[str, dict]]:
        self._check()
        return self.origin.queries()

    def mask(self) -> Mask:
        self._check()
        return self.origin.mask()

    def _check(self):
        try:
            document = yaml.safe_load(self.text)
        except yaml.YAMLError as e:
            raise Exception("The gates file is not valid YAML") from e
        self._require(
            isinstance(document, dict), "The gates file must be a YAML mapping"
        )
        self._keys(
            document,
            {"model", "oversize", "paths", "scopes", "skip", "gates"},
            "The gates file",
        )
        self._model(document.get("model"))
        self._oversize(document.get("oversize", "fail"), "The gates file")
        self._paths(document.get("paths", {}))
        fields = {**self.catalog, **self._custom(document.get("scopes", {}))}
        gates = document.get("gates")
        self._require(
            isinstance(gates, list) and len(gates) > 0,
            "The gates file must list at least one gate",
        )
        for gate in gates:
            self._gate(gate, fields)
        names = [gate["id"] for gate in gates]
        self._require(
            len(names) == len(set(names)),
            f"Gate ids must be unique, but {sorted({n for n in names if names.count(n) > 1})} "
            "repeat",
        )
        skips = document.get("skip", [])
        self._require(isinstance(skips, list), "'skip' must be a list")
        for index, entry in enumerate(skips, 1):
            self._skip(entry, f"The skip entry {index}", names)

    def _model(self, model: object):
        self._require(
            isinstance(model, str) and model.strip() != "",
            "The gates file must pin a model, for example 'model: jev-1.13.0'",
        )
        self._require(
            not str(model).endswith(("-latest", "-preview")),
            f"The model '{model}' is an alias; pin a version such as 'jev-1.13.0'",
        )

    def _oversize(self, value: object, owner: str):
        self._require(
            value in ("fail", "skip"),
            f"{owner} sets 'oversize' to '{value}', not fail or skip",
        )

    def _paths(self, paths: object):
        self._require(isinstance(paths, dict), "'paths' must be a mapping")
        self._keys(paths, {"include", "exclude"}, "'paths'")
        for key, value in paths.items():
            self._strings(value, f"'paths.{key}'")

    def _custom(self, scopes: object) -> dict[str, dict]:
        self._require(isinstance(scopes, dict), "'scopes' must be a mapping")
        for name, scope in scopes.items():
            owner = f"The custom scope '{name}'"
            self._require(
                name not in self.catalog, f"{owner} reuses a built-in scope name"
            )
            self._require(isinstance(scope, dict), f"{owner} must be a mapping")
            self._keys(scope, {"fields", "packs"}, owner)
            self._strings(scope.get("fields"), f"{owner} 'fields'")
            self._require(len(scope["fields"]) > 0, f"{owner} must declare fields")
            self._require(
                isinstance(scope.get("packs"), dict) and len(scope["packs"]) > 0,
                f"{owner} must give a query for at least one pack",
            )
            for pack, rule in scope["packs"].items():
                self._require(
                    isinstance(rule, dict) and isinstance(rule.get("match"), str),
                    f"{owner} needs a 'match' query for the '{pack}' pack",
                )
                self._keys(
                    rule, {"match", "fields", "defaults"}, f"{owner} in '{pack}'"
                )
        return {name: {"fields": scope["fields"]} for name, scope in scopes.items()}

    def _gate(self, gate: object, scopes: dict[str, dict]):
        self._require(isinstance(gate, dict), "Every gate must be a mapping")
        owner = f"The gate '{gate.get('id', '?')}'"
        self._keys(
            gate,
            {
                "id",
                "rule",
                "scope",
                "allow",
                "state",
                "ask",
                "fail_above",
                "modes",
                "oversize",
            },
            owner,
        )
        missing = [
            key
            for key in ("id", "scope", "state", "ask", "fail_above")
            if key not in gate
        ]
        self._require(not missing, f"{owner} lacks {', '.join(missing)}")
        self._require(
            isinstance(gate["id"], str)
            and re.fullmatch(r"[A-Za-z0-9][\w.\-]*", gate["id"]),
            f"{owner} has an id that is not a plain name",
        )
        self._require(
            gate["scope"] in scopes, f"{owner} names an unknown scope '{gate['scope']}'"
        )
        self._strings(gate["state"], f"{owner} 'state'")
        unknown = [
            field
            for field in gate["state"]
            if field not in scopes[gate["scope"]]["fields"]
        ]
        self._require(
            not unknown and len(gate["state"]) > 0,
            f"{owner} sends fields {unknown} that the '{gate['scope']}' scope does not have; "
            f"it has {scopes[gate['scope']]['fields']}",
        )
        self._require(
            isinstance(gate["ask"], str) and gate["ask"].strip() != "",
            f"{owner} asks nothing",
        )
        self._require(
            isinstance(gate["fail_above"], (int, float))
            and not isinstance(gate["fail_above"], bool)
            and 0 <= gate["fail_above"] < 1,
            f"{owner} needs 'fail_above' of at least 0 and below 1",
        )
        self._strings(gate.get("modes", ["diff"]), f"{owner} 'modes'")
        self._require(
            set(gate.get("modes", ["diff"])) <= {"diff", "full"},
            f"{owner} names an unknown mode",
        )
        self._strings(gate.get("allow", []), f"{owner} 'allow'")
        self._oversize(gate.get("oversize", "fail"), owner)

    def _skip(self, entry: object, owner: str, names: list[str]):
        self._require(isinstance(entry, dict), f"{owner} must be a mapping")
        self._keys(entry, {"gates", "reason", "path", "name"}, owner)
        self._require(
            isinstance(entry.get("reason"), str) and entry["reason"].strip() != "",
            f"{owner} gives no reason",
        )
        self._strings(entry.get("gates"), f"{owner} 'gates'")
        self._require(len(entry["gates"]) > 0, f"{owner} names no gate")
        unknown = sorted(set(entry["gates"]) - set(names))
        self._require(not unknown, f"{owner} names unknown gates {unknown}")
        self._require(
            "path" in entry or "name" in entry,
            f"{owner} sets neither 'path' nor 'name', which would turn the gate off",
        )
        self._require(
            all(
                isinstance(entry[key], str) for key in ("path", "name") if key in entry
            ),
            f"{owner} needs 'path' and 'name' as text",
        )

    def _keys(self, data: dict, allowed: set[str], owner: str):
        extra = sorted(set(data) - allowed)
        self._require(not extra, f"{owner} has unknown keys {extra}")

    def _strings(self, value: object, owner: str):
        self._require(
            isinstance(value, list) and all(isinstance(item, str) for item in value),
            f"{owner} must be a list of strings",
        )

    def _require(self, condition: bool, message: str):
        if not condition:
            raise Exception(message)
