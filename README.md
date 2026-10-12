# Jev Gate

A GitHub Action that fails a pipeline when code breaks a quality rule that
only a reader could check. Rules are yes/no questions in a YAML file; code
picks what each question applies to, [Jev](https://docs.typesafe.ai) answers
with a probability, and code compares it with a threshold.

## Contents

- [Usage](#usage)
- [Command line](#command-line)
- [GitLab CI](#gitlab-ci)
- [Gates file](#gates-file)
- [Custom scopes](#custom-scopes)
- [Examples](#examples)
  - [Built-in scopes](#built-in-scopes)
  - [Options](#options)
  - [A complete gates file](#a-complete-gates-file)
  - [Workflows](#workflows)
- [Development](#development)
- [How to report issues](#how-to-report-issues)

## Usage

```yaml
- uses: actions/checkout@v7
  with:
    fetch-depth: 0
    ref: ${{ github.event.pull_request.head.sha }}
- uses: lymagics/jev-gate@vX.Y.Z
  with:
    config: .github/jev-gates.yml
    mode: diff
    base: ${{ github.event.pull_request.base.sha }}
  env:
    TYPESAFE_API_KEY: ${{ secrets.TYPESAFE_API_KEY }}
```

Replace `vX.Y.Z` with a [release](https://github.com/lymagics/jev-gate/releases)
tag; the Action then installs the same version of `jev-gate` from PyPI. Any
other ref, such as a branch or a commit, builds the package from source.

`fetch-depth: 0` is required in `diff` mode: the base commit must be in the
history. Checking out the head commit keeps the merge commit of a pull
request out of the `commit` scope.

| Exit code | Meaning |
| --- | --- |
| 0 | No gate fired |
| 1 | At least one gate fired |
| 2 | The tool could not finish |

## Command line

Outside GitHub Actions, install the package from PyPI and call it directly:

```sh
pip install jev-gate
export TYPESAFE_API_KEY=...
jev-gate --config .github/jev-gates.yml --mode diff --base origin/main
```

It takes the same options as the Action, plus `--root`, the repository
directory, and `--log`, the output format: `github` (the default) prints
workflow commands that GitHub shows as annotations, and `plain` prints one
`file:line: error: gate: text` line per finding. It returns the same exit
codes.

## GitLab CI

Add a job to `.gitlab-ci.yml` and set `TYPESAFE_API_KEY` as a masked CI/CD
variable in the project settings:

```yaml
jev-gate:
  image: python:3.15
  variables:
    GIT_DEPTH: 0
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - pip install jev-gate==X.Y.Z
    - jev-gate --log plain --config .gitlab/jev-gates.yml --mode diff --base "$CI_MERGE_REQUEST_DIFF_BASE_SHA"
```

Replace `X.Y.Z` with a [release](https://github.com/lymagics/jev-gate/releases)
version.

`GIT_DEPTH: 0` is required in `diff` mode. GitLab clones only 20 commits by
default, which leaves the base out of the history and makes `merge-base` fail.

In a merged results pipeline, `HEAD` is a synthetic merge commit that would
land in the `commit` scope. Run the job in a plain merge request pipeline, or
check out `$CI_MERGE_REQUEST_SOURCE_BRANCH_SHA` before calling `jev-gate`.

The exit codes are the same: 0, 1 or 2.

## Gates file

Top-level keys:

| Key | Purpose |
| --- | --- |
| `model` | Pinned Jev version, such as `jev-1.13.0`. Aliases are refused. |
| `oversize` | `fail` (default) or `skip` |
| `paths` | `include` and `exclude` globs; `**` crosses directories |
| `scopes` | Custom syntax scopes (see below) |
| `gates` | The gates |

Gate keys: `id`, `rule`, `scope`, `allow`, `state`, `ask`, `fail_above`,
`modes`, `oversize`. A gate fires when the probability is strictly above
`fail_above`. `allow` lists candidate names the gate never judges: the
identifier for `type`, `function` and `variable`, the raw test name for
`test`, the path for `file` and `hunk`, and the subject for `commit`.
`where` filters are not supported yet.

Gates of one candidate that send the same `state` fields share one request.

Built-in scopes and the fields they offer to `state`:

| Scope | Fields | Modes |
| --- | --- | --- |
| `file` | `path`, `text` | diff, full |
| `hunk` | `path`, `before`, `after` | diff |
| `commit` | `subject`, `message`, `diff`, `tests` | diff |
| `test` | `phrase`, `message`, `assertion`, `source` | diff, full |
| `changed_test` | `before`, `after` | diff |
| `type` | `name` | diff, full |
| `function` | `name`, `returns` | diff, full |
| `variable` | `name` | diff, full |
| `throw` | `message`, `statement` | diff, full |
| `catch` | `handler` | diff, full |
| `log` | `statement` | diff, full |

## Custom scopes

A custom scope gives a tree-sitter query per language pack. Captures name
the fields; `@candidate` marks the node, and captures starting with `_`
are ignored. See [a custom scope](#a-custom-scope) for a gate that uses one.

## Examples

Every example below is a complete gates file. The test suite validates
each one, so they stay in step with the code.

### Built-in scopes

#### file

Catches a module whose content does not match its file name.

```yaml
model: jev-1.13.0
gates:
  - id: module-content-disagrees-with-path
    scope: file
    state: [path, text]
    ask: Does `text` hold code about a different subject than `path` names?
    fail_above: 0.9
```

#### hunk

Catches a change that comments code out instead of deleting it. Diff mode
only.

```yaml
model: jev-1.13.0
gates:
  - id: code-commented-out
    scope: hunk
    state: [path, before, after]
    ask: >-
      Comparing `before` with `after` in `path`, does the change turn working
      code into a comment instead of deleting it?
    fail_above: 0.85
```

#### commit

Catches a commit that changes behaviour without touching a test. Diff mode
only.

```yaml
model: jev-1.13.0
gates:
  - id: behaviour-changed-without-tests
    scope: commit
    state: [subject, message, diff, tests]
    ask: >-
      `subject` and `message` describe the commit and `diff` is its change.
      Does `diff` change behaviour while `tests` shows no test for it?
    fail_above: 0.9
```

#### test

Catches a test whose name promises something its assertion does not check.

```yaml
model: jev-1.13.0
gates:
  - id: assertion-misses-the-claim
    rule: testing.md 1.2
    scope: test
    state: [phrase, message, assertion, source]
    ask: >-
      `phrase` is what the test claims and `source` is its body. Do
      `assertion` and `message` check something other than `phrase`?
    fail_above: 0.9
```

#### changed_test

Catches an edited test that was weakened to make it pass. Diff mode only.

```yaml
model: jev-1.13.0
gates:
  - id: test-weakened
    scope: changed_test
    state: [before, after]
    ask: Does `after` check less than `before` did?
    fail_above: 0.8
```

#### type

Catches a class named after what it does rather than what it is.

```yaml
model: jev-1.13.0
gates:
  - id: class-named-after-a-doer
    rule: eo.md 2.1
    scope: type
    state: [name]
    ask: >-
      Does the class name `name` end in -er or -or and describe what its
      objects do rather than what they are?
    fail_above: 0.85
```

#### function

Catches a method named as a verb that returns a value.

```yaml
model: jev-1.13.0
gates:
  - id: builder-named-as-a-verb
    rule: eo.md 2.2
    scope: function
    state: [name, returns]
    ask: >-
      `returns` is the return type of `name`. Is `returns` something other
      than nothing while `name` is a verb?
    fail_above: 0.9
```

#### variable

Catches a variable with a compound name.

```yaml
model: jev-1.13.0
gates:
  - id: compound-variable-name
    rule: eo.md 2.3
    scope: variable
    state: [name]
    ask: Is `name` built from more than one noun?
    fail_above: 0.9
```

#### throw

Catches an error text that does not say what failed.

```yaml
model: jev-1.13.0
gates:
  - id: error-text-hides-what-failed
    scope: throw
    state: [message, statement]
    ask: >-
      `statement` raises an error with `message`. Does `message` fail to tell
      the reader what went wrong?
    fail_above: 0.9
```

#### catch

Catches a handler that swallows the error.

```yaml
model: jev-1.13.0
gates:
  - id: swallowed-exception
    scope: catch
    state: [handler]
    ask: Does `handler` drop the error without logging, rethrowing or returning it?
    fail_above: 0.9
```

#### log

Catches a log line that writes a secret.

```yaml
model: jev-1.13.0
gates:
  - id: secret-in-log
    scope: log
    state: [statement]
    ask: Does `statement` write a password, token or key to the log?
    fail_above: 0.8
```

### Options

#### allow

Catches doer class names, except the two names the rule permits.

```yaml
model: jev-1.13.0
gates:
  - id: class-named-after-a-doer-allowed
    scope: type
    state: [name]
    allow: [User, Computer]
    ask: Does the class name `name` describe what its objects do?
    fail_above: 0.85
```

#### Modes

Catches vague test names on a schedule only, and compound type names on
both pull requests and schedules. A gate without `modes` runs in both;
gates of diff-only scopes are left out of `full` runs.

```yaml
model: jev-1.13.0
gates:
  - id: vague-test-name
    scope: test
    state: [phrase]
    modes: [full]
    ask: Does `phrase` fail to name one behaviour of one object?
    fail_above: 0.9

  - id: compound-type-name
    scope: type
    state: [name]
    modes: [diff, full]
    ask: Is the type name `name` built from more than one noun?
    fail_above: 0.9
```

#### Oversize

Catches unclear commit subjects and skips commits too large to send, while
every other gate fails on oversize input as the top level says.

```yaml
model: jev-1.13.0
oversize: fail
gates:
  - id: commit-subject-hides-intent
    scope: commit
    state: [subject, diff]
    oversize: skip
    ask: Does `subject` fail to say why `diff` was made?
    fail_above: 0.95

  - id: file-mixes-concerns
    scope: file
    state: [text]
    ask: Does `text` mix more than one concern?
    fail_above: 0.9
```

The same file with `oversize: skip` at the top level skips oversize input
for every gate that does not set its own `oversize`.

#### Paths

Catches lying error texts in source and tests, but not in generated code
or vendored files.

```yaml
model: jev-1.13.0
paths:
  include: ["src/**", "tests/**"]
  exclude: ["**/generated/**", "src/vendor/**"]
gates:
  - id: error-text-lies
    scope: throw
    state: [message, statement]
    ask: Does `message` describe a different failure than `statement` raises?
    fail_above: 0.9
```

#### Shared requests

Catches failure messages that disagree with the test name and ones that
are empty of meaning, in one request per test, because both gates send
`[phrase, message]`.

```yaml
model: jev-1.13.0
gates:
  - id: failure-message-disagrees-with-name
    rule: testing.md 1.3
    scope: test
    state: [phrase, message]
    ask: >-
      `phrase` is what the test claims. `message` is the text shown when the
      test fails. Does `message` describe a different behaviour, or a
      different object, than `phrase`?
    fail_above: 0.9

  - id: failure-message-says-nothing
    scope: test
    state: [message, phrase]
    ask: Does `message` say nothing a reader of `phrase` would not already know?
    fail_above: 0.9
```

#### A custom scope

Catches BDD steps in Python whose phrase does not describe what the step
does.

```yaml
model: jev-1.13.0
scopes:
  bdd_step:
    fields: [phrase, source]
    packs:
      python:
        match: |
          ((decorated_definition
             (decorator) @_d
             definition: (function_definition name: (identifier) @phrase)) @candidate @source
           (#match? @_d "^@(given|when|then)"))
gates:
  - id: step-phrase-disagrees-with-body
    scope: bdd_step
    state: [phrase, source]
    ask: Does `source` do something other than `phrase` says?
    fail_above: 0.9
```

### A complete gates file

A starting point to copy to `.github/jev-gates.yml`.

```yaml
model: jev-1.13.0
oversize: fail

paths:
  include: ["src/**", "tests/**"]
  exclude: ["**/generated/**"]

gates:
  - id: failure-message-disagrees-with-name
    rule: testing.md 1.3
    scope: test
    state: [phrase, message]
    ask: >-
      `phrase` is what the test claims. `message` is the text shown when the
      test fails. Does `message` describe a different behaviour, or a
      different object, than `phrase`?
    fail_above: 0.90

  - id: class-named-after-a-doer
    rule: eo.md 2.1
    scope: type
    state: [name]
    allow: [User, Computer]
    ask: >-
      Does the class name `name` end in -er or -or and describe what its
      objects do rather than what they are?
    fail_above: 0.85

  - id: error-text-hides-what-failed
    scope: throw
    state: [message]
    ask: Does `message` fail to tell the reader what went wrong?
    fail_above: 0.90

  - id: swallowed-exception
    scope: catch
    state: [handler]
    ask: Does `handler` drop the error without logging, rethrowing or returning it?
    fail_above: 0.90

  - id: commit-subject-hides-intent
    scope: commit
    state: [subject, diff]
    oversize: skip
    ask: Does `subject` fail to say why `diff` was made?
    fail_above: 0.95
```

### Workflows

#### Diff mode on pull requests

Judges only what a pull request touches.

```yaml
name: Jev Gate

on:
  pull_request:

permissions:
  contents: read

jobs:
  gate:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
          ref: ${{ github.event.pull_request.head.sha }}
      - uses: lymagics/jev-gate@vX.Y.Z
        with:
          config: .github/jev-gates.yml
          mode: diff
          base: ${{ github.event.pull_request.base.sha }}
        env:
          TYPESAFE_API_KEY: ${{ secrets.TYPESAFE_API_KEY }}
```

#### Full mode on a schedule

Judges every candidate in the repository once a week.

```yaml
name: Jev Gate Full

on:
  schedule:
    - cron: "17 3 * * 1"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  gate:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v7
      - uses: lymagics/jev-gate@vX.Y.Z
        with:
          config: .github/jev-gates.yml
          mode: full
        env:
          TYPESAFE_API_KEY: ${{ secrets.TYPESAFE_API_KEY }}
```

## Development

```sh
uv venv .venv && uv pip install --python .venv -e ".[dev]"
make unit      # fast tests with coverage
make e2e       # deep tests
make black flake8 ruff
```

## How to report issues

### Enhancements

Open an issue labelled `enhancement` that describes the behaviour you want
and why it helps. You don't need to write code.

### Bugs in code

Open a pull request, not an issue. It must include a test that fails on the
current code, marked with `@pytest.mark.skip` so CI stays green:

```python
@pytest.mark.skip(reason="Reproduces #42, unskip once fixed")
def test_skips_hunk_with_only_whitespace_changes():
    ...
```

The fix can come in the same pull request or a later one, which removes the
skip. If you can't push to the repository, fork it first.

### Bugs outside code

For bugs a test can't reproduce (documentation, `action.yml` wiring,
packaging, CI workflows), open an issue labelled `bug` that gives the
expected behaviour, the actual behaviour and how to observe it.
