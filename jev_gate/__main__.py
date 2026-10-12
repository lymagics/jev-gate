import os
import sys

from jev_gate.anywhere import Anywhere
from jev_gate.application import Application
from jev_gate.chosen_log import ChosenLog
from jev_gate.typesafe_connection import TypeSafeConnection


def main() -> int:
    log = ChosenLog(sys.argv[1:], sys.stdout)
    try:
        code = Application(
            sys.argv[1:],
            TypeSafeConnection(os.environ.get("TYPESAFE_API_KEY", "")),
            log,
        ).code()
    except Exception as e:
        reasons = []
        cause: BaseException | None = e
        while cause is not None:
            reasons.append(str(cause))
            cause = cause.__cause__
        log.error(Anywhere("jev-gate"), "jev-gate", " <- ".join(reasons))
        code = 2
    return code


if __name__ == "__main__":
    sys.exit(main())
