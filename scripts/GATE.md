<!-- lifecycle-template: GATE.md -->
# The merge gate contract

A gate is the one path by which a pull request reaches `main` in this
repository. GitHub refuses nothing on this plan: plain `gh pr merge` lands a
red, pending or check-less pull request. So the refusals live in a script the
repository carries itself, and the lifecycle rules (AGENTS.md, "Work
lifecycle", rule 7) forbid every other way of merging.

This document is the contract. Any script that meets every clause is a gate.
`merge-pr.py`, the generic gate copied from the same template, meets it; a
repository with a gate of its own keeps its verdict logic and meets the same
clauses. This file is a copy: change the template, not the copy.

## Clauses

1. **Dry run by default.** Without an explicit flag the gate inspects,
   reports and merges nothing. Merging is a second, deliberate invocation.
2. **The pull request is mergeable in the plain sense.** Open, not a draft,
   from this repository, targeting the default branch, with no conflicts. A
   mergeability GitHub has not computed yet is not "no conflicts".
3. **Checks are green, and exist.** Every reported check has completed and
   succeeded. Zero reported checks is refused unless the repository has no
   workflow files at the pull request's head, because otherwise "no checks"
   cannot be told from "CI never ran". Checks that all skipped are not a
   pass: nothing ran. Every check the touched paths trigger must be present,
   so a path-filtered workflow that should have run and did not is a refusal.
   A touched path is any path the diff adds, changes or deletes, under the
   name git stores; a moved file touches the path it left and the one it
   reached. A check the repository lists as advisory (a job its workflow
   marks `continue-on-error`, which still reports FAILURE) may have failed,
   but it must have finished; the gate prints each one it tolerated. Nothing
   is advisory unless the repository's configuration names it.
4. **Current base, where the repository asks for it.** A low-traffic
   repository requires the head to contain the tip of `main`, so the checks
   ran against the code that will exist after the merge. A high-traffic one
   may not, and says so in its configuration.
5. **Local checks run where the pull request is.** From the pull request's
   own worktree or a disposable one, at exactly the pull request's head, with
   a clean tree. Never from the shared main checkout.
6. **The diff is secret-scanned.** The same scanner the `pre-commit` hook
   runs, over what the pull request adds. This is how a commit made with
   `--no-verify` is caught. A pull request is judged by the rules at its own
   head: the gate, its settings, the scanner, the workflows. Two things keep
   that from being a way around them:
   - the gate prints a note naming every such path the diff touches (the
     gate script, its settings file, this contract, the configured scanner,
     anything under `.github/workflows/`), saying that the pull request
     changes the rules it is judged by. Whoever gives the word reads those
     changes first;
   - a diff that takes the scan away is refused: when the base branch has
     the scanner its settings name, and the tree at the head has no file at
     the path the head's settings name, nothing merges. A file the checkout
     merely holds there, ignored, is not the scanner. Only a repository
     whose base has no scanner either is passed unscanned, with a note.
7. **Two identical snapshots.** Head, base and check results are read before
   the local checks and again after. Any difference aborts: something moved
   while the gate was looking.
8. **Squash, with the head pinned and a receipt.** The merge names the exact
   head sha it verified, so a push that lands in between makes GitHub refuse.
   The squash message ends with a trailer:

   ```
   Gated-By: <gate path> lifecycle:v1 <head sha>
   ```

   A label can be changed afterwards; a commit message cannot. The sweeper
   reports any merged pull request whose commit lacks the trailer.
9. **`mergedAt` is read back.** The merge is believed only when GitHub
   reports the pull request MERGED with a merge time and a merge commit. An
   unconfirmed merge stops the gate with a distinct exit status and nothing
   is torn down: inspect before retrying.
10. **Teardown happens in the same run**, while the evidence is exact:
    - the local branch is deleted when its tip is contained in the merged
      head (equal, or behind it after an update-branch);
    - a worktree holding it is removed when it is clean, is not the main
      checkout, is not locked, is not listed in `worktrees.tsv`, and no
      process has its working directory inside it. Removal is never forced,
      and ignored files that cannot be regenerated are copied to
      `<git-common-dir>/worktree-backups/` first;
    - a worktree that `worktrees.tsv` lists is never removed and never
      marked, whatever it holds, and a branch it still has checked out stays
      (rule 11: the registry is the single sanction for a long-lived
      worktree). The registry is read as the classifier reads it: the copy
      on the base branch united with the main checkout's working copy, so a
      row that has not landed yet already protects. Run from a listed tree,
      the gate detaches it, as it does any tree it runs from, and writes no
      mark;
    - the worktree the gate was run from is never removed. When it holds the
      branch it is detached at the merged head. Whether it held the branch or
      was a disposable tree already at the head, it is marked `LANDED` in
      `<git-common-dir>/worktrees/<id>/lifecycle`, for the next session or
      the sweeper to remove. A tree that did not hold the branch is marked
      only where the mark is true: a linked worktree (never the main
      checkout), clean, with a HEAD contained in the merged head;
    - the remote branch is deleted when its tip is still contained in the
      merged head, unless GitHub already deleted it. A branch someone pushed
      to after the merge is kept and reported: those commits are in no pull
      request ref.
11. **Memory-only mode, and private notes.** For the daily `docs(memory)`
    pull request the gate additionally verifies that the diff touches nothing
    outside `.claude/memory/`. A file moved into the store is a deletion
    outside it, and is refused like any other. That is the only pull request
    merged without the operator's word, and this clause is what keeps the
    authorization that narrow. In every mode, a memory file whose frontmatter
    says `private: true` is refused: once a store is tracked, everything in
    it is published, so a note that must not be is marked, and moved to a
    path the repository ignores.
12. **Who may run it.** The operator, or an agent the operator told to merge
    its own pull request. Never another agent's.

## Exit status

| Status | Meaning |
|---|---|
| 0 | dry run passed, or merged and confirmed |
| 1 | refused; every reason is printed |
| 2 | uncertain: a merge was requested and could not be confirmed |

The status does not depend on who reads the output. When stdout closes under
the gate (`| head`, `| grep -q`), it stops printing and carries on: a
confirmed merge is still torn down in the same run, and the status is still
one of these three.

## Configuring the generic gate

`merge-pr.py` reads `merge-pr.json` from its own directory. Every key is
optional.

| Key | Default | Meaning |
|---|---|---|
| `base` | `main` | the branch pull requests target |
| `require_current_base` | `true` | clause 4 |
| `required_checks` | `[]` | check names that must be present and successful |
| `advisory_checks` | `[]` | check names that may fail once they have finished; a name also listed as required stays required |
| `path_filtered_checks` | `{}` | check name → path globs; the check is required when a touched path matches |
| `local_checks` | `[]` | shell commands run from the worktree, in order; any non-zero exit refuses |
| `secret_scan` | `.githooks/pre-commit` | the scanner, relative to the repository root |
| `memory_path` | `.claude/memory/` | the path memory-only mode allows |
