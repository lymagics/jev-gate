# Jev Gate

[![EO principles respected here](https://www.elegantobjects.org/badge.svg)](https://www.elegantobjects.org)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/jev-gate?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/jev-gate)

Linters catch what a parser can see: a missing semicolon, an unused import,
a line that is too long. They can't tell you that `InvoiceBuilder` is named
after what it does rather than what it is, that a test called
`test_rejects_empty_cart` actually checks the total, or that an `except`
block quietly swallows an error. Those rules need a reader.

Jev Gate is that reader in your CI. You write each rule as a yes/no
question in a YAML file. Jev Gate finds the code the question is about,
asks [Jev](https://docs.typesafe.ai) for the probability that the answer is
"yes", and fails the pipeline when the probability is above your threshold.

It runs as a GitHub Action, in GitLab CI, or as a plain command.

## Contents

- [How it works](#how-it-works)
- [Quick start](#quick-start)
- [Writing a gate](#writing-a-gate)
- [Recipes](#recipes)
- [Options](#options)
- [Running outside GitHub](#running-outside-github)
- [Reference](#reference)
- [Development](#development)
- [How to report issues](#how-to-report-issues)

## How it works

Take one rule: *a class must be named after what it is, not what it does*.

```yaml
model: jev-1.13.0
gates:
  - id: class-named-after-a-doer
    scope: type
    state: [name]
    ask: Does the class name `name` describe what its objects do?
    fail_above: 0.85
```

When a pull request adds `class InvoiceBuilder` and `class Invoice`:

1. **Pick.** The `type` scope finds every class the pull request touches:
   `InvoiceBuilder` and `Invoice`.
2. **Ask.** For each one, Jev gets the question with `name` filled in and
   answers with a probability: 0.93 for `InvoiceBuilder`, 0.04 for
   `Invoice`.
3. **Compare.** 0.93 is above 0.85, so the gate fires on `InvoiceBuilder`
   and the pipeline fails. `Invoice` passes.

On GitHub the finding shows up as an annotation on the line of the class:

```text
src/billing/invoice_builder.py:12: error: class-named-after-a-doer: class-named-after-a-doer fired on InvoiceBuilder at src/billing/invoice_builder.py:12 with probability 0.934
jev-gate: 1 gate(s) in diff mode gave 2 verdict(s), 1 violation(s), exit code 1
```

Code decides *what* gets judged and *whether* the pipeline fails; Jev only
answers the question. The same file always picks the same candidates, and
you tune strictness with one number.

Jev Gate reads Python, Java, JavaScript, TypeScript, C#, C++, Ruby and Rust.

## Quick start

**1. Add a gates file** at `.github/jev-gates.yml`. Start with one or two
gates; [A complete gates file](#a-complete-gates-file) has more.

```yaml
model: jev-1.13.0
gates:
  - id: swallowed-exception
    scope: catch
    state: [handler]
    ask: Does `handler` drop the error without logging, rethrowing or returning it?
    fail_above: 0.9
```

**2. Add your Typesafe API key** as a repository secret named
`TYPESAFE_API_KEY`.

**3. Add a workflow** at `.github/workflows/jev-gate.yml`:

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

Replace `vX.Y.Z` with a [release](https://github.com/lymagics/jev-gate/releases)
tag. The Action then installs the same version of `jev-gate` from PyPI; any
other ref, such as a branch or a commit, builds it from source.

Two lines in that workflow matter:

- `fetch-depth: 0` brings in the full history, so the base commit is there
  to diff against.
- `ref: ...head.sha` checks out the real head of the pull request, so the
  merge commit GitHub creates doesn't get judged as one of your commits.

Open a pull request. Every gate that fires shows up as an annotation on the
line it is about, and the job fails.

## Writing a gate

A gate is one question about one kind of code:

```yaml
model: jev-1.13.0
gates:
  - id: assertion-misses-the-claim      # name shown in findings
    rule: testing.md 1.2                # optional: where the rule is written down
    scope: test                         # what kind of code to judge
    state: [phrase, assertion]          # which parts of it Jev sees
    ask: >-                             # the yes/no question, in terms of state
      `phrase` is what the test claims. Does `assertion` check something
      other than `phrase`?
    fail_above: 0.9                     # fire when P(yes) is above this
```

A few tips:

- **Phrase the question so "yes" means "broken".** The gate fires on a high
  probability of "yes".
- **Name every `state` field in the question**, in backticks, so Jev knows
  what each value is.
- **Send only the fields the question needs.** Less text means cheaper,
  sharper answers.
- **Start strict and loosen.** Begin with `fail_above: 0.9` and lower it
  once you trust the gate.

## Recipes

Every gates file below is complete and can be copied as is. The test suite
validates each one, so they stay in step with the code.

### One per scope

#### file: a module about the wrong thing

```yaml
model: jev-1.13.0
gates:
  - id: module-content-disagrees-with-path
    scope: file
    state: [path, text]
    ask: Does `text` hold code about a different subject than `path` names?
    fail_above: 0.9
```

#### hunk: code commented out instead of deleted

Diff mode only.

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

#### commit: behaviour changed without a test

Diff mode only.

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

#### test: a name the assertion doesn't back up

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

For `def test_rejects_empty_cart(): assert total(cart) == 0`, `phrase` is
`it rejects empty cart` and `assertion` is `assert total(cart) == 0`.

#### changed_test: a test weakened to make it pass

Diff mode only.

```yaml
model: jev-1.13.0
gates:
  - id: test-weakened
    scope: changed_test
    state: [before, after]
    ask: Does `after` check less than `before` did?
    fail_above: 0.8
```

#### type: a class named after a doer

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

#### function: a verb that returns a value

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

Fires on `def calculate(self) -> int`, passes `def total(self) -> int`.

#### variable: a compound name

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

Fires on `user_account_list`, passes `users`.

#### throw: an error that doesn't say what failed

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

Fires on `raise Exception("Error")`, passes
`raise Exception("The gates file 'gates.yml' cannot be read")`.

#### catch: a swallowed exception

```yaml
model: jev-1.13.0
gates:
  - id: swallowed-exception
    scope: catch
    state: [handler]
    ask: Does `handler` drop the error without logging, rethrowing or returning it?
    fail_above: 0.9
```

Fires on `except ValueError: pass`.

#### log: a secret written to the log

```yaml
model: jev-1.13.0
gates:
  - id: secret-in-log
    scope: log
    state: [statement]
    ask: Does `statement` write a password, token or key to the log?
    fail_above: 0.8
```

### A complete gates file

A starting point with five common gates.

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

## Options

### Diff mode and full mode

`diff` judges only what a change touches: the classes, tests and hunks a
pull request adds or edits. `full` judges every candidate in the
repository, which suits a weekly run:

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

A gate runs in both modes unless it says otherwise with `modes`. Here vague
test names are checked only on the weekly run, while compound type names
are checked everywhere:

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

Gates on diff-only scopes (`hunk`, `commit`, `changed_test`) are left out
of `full` runs.

### allow: names a gate never judges

The rule bans doer names, but `User` and `Computer` are fine:

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

What `allow` matches depends on the scope: the identifier for `type`,
`function` and `variable`, the raw test name for `test`, the path for
`file` and `hunk`, and the subject for `commit`.

### paths: which files to read

Check source and tests, but skip generated and vendored code. `**` crosses
directories.

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

### oversize: input too large for Jev

Some candidates, like a huge commit, are too large to send. By default
(`fail`) that stops the pipeline; `skip` reports a warning and moves on. Set
it for the whole file and override it per gate. Here only the commit gate
skips:

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

### Shared requests

Gates on the same candidate that send the same `state` fields share one
request to Jev, in any order. These two gates cost one request per test:

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

### Custom scopes

When no built-in scope fits, define one with a
[tree-sitter query](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/)
per language. `@candidate` marks the node to judge, other captures become
`state` fields, and captures starting with `_` are ignored.

This one judges BDD steps in Python, functions decorated with `@given`,
`@when` or `@then`:

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

## Running outside GitHub

### Command line

```sh
pip install jev-gate
export TYPESAFE_API_KEY=...
jev-gate --config .github/jev-gates.yml --mode diff --base origin/main --log plain
```

`--log plain` prints one `file:line: error: gate: text` line per finding,
like the sample in [How it works](#how-it-works). The default, `github`,
prints workflow commands that GitHub turns into annotations. `--root` sets
the repository directory if it isn't the current one.

### GitLab CI

Set `TYPESAFE_API_KEY` as a masked CI/CD variable, then add a job to
`.gitlab-ci.yml`:

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

- `GIT_DEPTH: 0` is needed in diff mode. GitLab clones only 20 commits by
  default, which can leave the base out of the history.
- In a merged results pipeline, `HEAD` is a synthetic merge commit that
  would be judged by the `commit` scope. Run the job in a plain merge
  request pipeline, or check out `$CI_MERGE_REQUEST_SOURCE_BRANCH_SHA`
  before calling `jev-gate`.

## Reference

### Action inputs and command options

| Input | Option | Default | Meaning |
| --- | --- | --- | --- |
| `config` | `--config` | `.github/jev-gates.yml` | Path to the gates file |
| `mode` | `--mode` | `diff` | `diff` or `full` |
| `base` | `--base` | | Commit to compare with; required in diff mode |
| `jobs` | `--jobs` | `8` | Requests sent to Jev in parallel |
| | `--root` | `.` | Repository directory |
| | `--log` | `github` | `github` or `plain` |

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | No gate fired |
| 1 | At least one gate fired |
| 2 | Jev Gate could not finish, for example a broken gates file |

### Gates file

| Key | Meaning |
| --- | --- |
| `model` | Pinned Jev version, such as `jev-1.13.0`. Aliases are refused. |
| `oversize` | `fail` (default) or `skip` |
| `paths` | `include` and `exclude` globs |
| `scopes` | Custom scopes |
| `gates` | The gates |

| Gate key | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Name shown in findings |
| `scope` | yes | What kind of code to judge |
| `state` | yes | Fields of the candidate Jev sees |
| `ask` | yes | The yes/no question |
| `fail_above` | yes | Fire when the probability is strictly above this |
| `rule` | no | Where the rule is written down; shown in findings |
| `allow` | no | Candidate names never judged |
| `modes` | no | `diff`, `full` or both (default) |
| `oversize` | no | Overrides the top-level `oversize` |

`where` filters are not supported yet.

### Built-in scopes

| Scope | Judges | Fields | Modes |
| --- | --- | --- | --- |
| `file` | A whole file | `path`, `text` | diff, full |
| `hunk` | One changed block of a diff | `path`, `before`, `after` | diff |
| `commit` | One commit | `subject`, `message`, `diff`, `tests` | diff |
| `test` | A test function | `phrase`, `message`, `assertion`, `source` | diff, full |
| `changed_test` | A test edited by the change | `before`, `after` | diff |
| `type` | A class, struct, interface or enum | `name` | diff, full |
| `function` | A public function or method | `name`, `returns` | diff, full |
| `variable` | A variable or parameter | `name` | diff, full |
| `throw` | A raise or throw | `message`, `statement` | diff, full |
| `catch` | An except or catch block | `handler` | diff, full |
| `log` | A logging call | `statement` | diff, full |

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
