import argparse
import os

import yaml

from jev_gate.contracts import Connection, Log, Settings, Sources
from jev_gate.diff_sources import DiffSources
from jev_gate.directory import PackDirectory
from jev_gate.full_sources import FullSources
from jev_gate.gates_file import GatesFile
from jev_gate.git import GitRepository
from jev_gate.joined import Joined
from jev_gate.selection import Selection
from jev_gate.trial import Trial
from jev_gate.valid_gates_file import ValidGatesFile
from jev_gate.worktree import Worktree


class Application:
    def __init__(self, args: list[str], connection: Connection, log: Log):
        self.args = args
        self.connection = connection
        self.log = log

    def code(self) -> int:
        options = self._options()
        settings = self._settings(options.config)
        gates = settings.gates(options.mode)
        model = self.connection.model(settings.model())
        sources = self._sources(options, settings)
        candidates = Joined(
            [sources.candidates(scope) for scope in settings.scopes(options.mode)]
        )
        verdicts = Trial(gates, candidates, model, options.jobs).verdicts()
        for verdict in verdicts:
            verdict.report(self.log)
        code = max([verdict.code() for verdict in verdicts], default=0)
        self.log.info(
            f"jev-gate: {len(gates)} gate(s) in {options.mode} mode gave "
            f"{len(verdicts)} verdict(s), "
            f"{sum(1 for verdict in verdicts if verdict.code() == 1)} violation(s), "
            f"exit code {code}"
        )
        return code

    def _options(self) -> argparse.Namespace:
        parser = argparse.ArgumentParser(prog="jev-gate", exit_on_error=False)
        parser.add_argument("--config", default=".github/jev-gates.yml")
        parser.add_argument("--mode", choices=["diff", "full"], default="diff")
        parser.add_argument("--base", default="")
        parser.add_argument("--root", default=".")
        parser.add_argument("--jobs", type=int, default=8)
        parser.add_argument("--log", choices=["github", "plain"], default="github")
        try:
            options = parser.parse_args(self.args)
        except (argparse.ArgumentError, SystemExit) as e:
            raise Exception(f"The arguments {self.args} are not understood") from e
        if options.mode == "diff" and not options.base.strip():
            raise Exception(
                "Diff mode needs --base, the commit the change is compared with"
            )
        if options.jobs < 1:
            raise Exception("--jobs must be at least 1")
        return options

    def _settings(self, path: str) -> Settings:
        try:
            with open(path, encoding="utf-8") as stream:
                text = stream.read()
        except OSError as e:
            raise Exception(f"The gates file '{path}' cannot be read") from e
        with open(
            os.path.join(os.path.dirname(__file__), "scopes.yml"), encoding="utf-8"
        ) as stream:
            catalog = yaml.safe_load(stream)
        return ValidGatesFile(GatesFile(text, catalog), text, catalog)

    def _sources(self, options: argparse.Namespace, settings: Settings) -> Sources:
        repository = GitRepository(options.root)
        tree = Selection(Worktree(repository, options.root), settings.mask())
        packs = (
            PackDirectory(os.path.join(os.path.dirname(__file__), "packs"))
            .packs()
            .extended(settings.queries())
        )
        result: Sources = FullSources(tree, packs)
        if options.mode == "diff":
            try:
                base = repository.output("merge-base", options.base, "HEAD").strip()
            except Exception as e:
                raise Exception(
                    f"The base '{options.base}' is not in the history; fetch the "
                    "full history ('fetch-depth: 0' on GitHub, 'GIT_DEPTH: 0' on "
                    "GitLab)"
                ) from e
            result = DiffSources(repository, base, tree, packs)
        return result
