# PCA repository guide

This is an independent static Jekyll documentation repository. The parent
Dictiva application's runtime, database, hooks and deployment commands do not
apply. Read CONTRIBUTING.md and GOVERNANCE.md before changing the specification.

## Work lifecycle

- Preserve the operator's main checkout. Work from a clean, task-owned branch
  and sanctioned worktree based on freshly fetched origin/main.
- Changes go through a pull request. Merge only when the operator authorizes
  the agent to merge its own PR.
- The owning gate is `python3 scripts/merge-pr.py <PR>` (dry run), followed by
  `python3 scripts/merge-pr.py <PR> --execute`. Never merge directly through
  GitHub's UI, API or `gh pr merge`.
- The gate requires the **Validate documentation** check, an up-to-date base,
  a clean worktree at the PR head, the secret scan and local document checks.
  See scripts/GATE.md for its complete contract and cleanup behavior.
- The gate and secret scanner are unchanged System lifecycle templates;
  configure the gate through scripts/merge-pr.json. Do not change hooksPath.
- Before committing, run `sh .githooks/pre-commit` on staged changes. The gate
  also runs the scanner over the entire PR diff, regardless of hook wiring.

## Validation and publishing

Run `python3 scripts/validate.py` and `actionlint` before pushing workflow
changes. The Python check validates JSON examples and Atom generation without
leaving generated changes. PR CI also records the actual Node version of a
local `node24` JavaScript action. A warning about an older vendor runtime is
reported explicitly; documentation validation does not certify vendor patching.

GitHub Pages builds the root of main in legacy Jekyll mode. Merging publishes
documentation. The changelog workflow regenerates changelog.atom on relevant
main changes; do not dispatch it on a feature branch. Implementation-guide
snippets are illustrative, not a separately packaged application.
