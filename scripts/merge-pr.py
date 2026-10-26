#!/usr/bin/env python3
# lifecycle-template: merge-pr.py
"""The merge gate: the one path a pull request takes to the default branch.

  merge-pr.py <PR>                    dry run: inspect, run the local checks, print the verdict
  merge-pr.py <PR> --execute          the same, then squash-merge, read back, tear down
  merge-pr.py <PR> --memory-only      also require the diff to stay inside the memory path
  merge-pr.py <PR> --teardown-only    a pull request that is already merged: local teardown
                                      only (a dry run of it without --execute)

Run it from the pull request's own worktree, at the pull request's head, with a
clean tree. Exit status: 0 passed or merged, 1 refused, 2 uncertain.

This file is the repository's own. It was copied from a template and calls
nothing outside the repository. Do not edit the copy: change the template and
re-copy, or the drift check reports it as behind. What it must do, and why each
clause exists, is in GATE.md beside this file; per-repo settings live in
merge-pr.json next to it.

Python 3.9+, standard library only. Needs git and an authenticated gh.
"""
import argparse
import filecmp
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CONTRACT = "lifecycle:v1"
SUCCESS = {"SUCCESS"}
DID_NOT_RUN = {"SKIPPED", "NEUTRAL"}
# A check in one of these states may still change, so nothing is settled by it.
UNFINISHED = {"QUEUED", "IN_PROGRESS", "WAITING", "PENDING", "REQUESTED", "EXPECTED"}
DEFAULTS = {
    "base": "main",
    "require_current_base": True,
    "required_checks": [],
    "advisory_checks": [],
    "path_filtered_checks": {},
    "local_checks": [],
    "secret_scan": ".githooks/pre-commit",
    "memory_path": ".claude/memory/",
}
# Names a build or a cache writes: an ignored path whose last component is one
# of these is not worth copying before its worktree is removed. Globs, matched
# against the name as `git status` prints it (a directory ends in "/"). The
# worktree classifier on the operator's machine keeps the same list: a name
# that belongs in one belongs in both.
REGENERABLE = (
    "__pycache__/", ".pytest_cache/", ".ruff_cache/", ".mypy_cache/", ".tox/", ".venv/", "venv/",
    "node_modules/", ".next/", ".turbo/", ".cache/", ".parcel-cache/", "coverage/", "htmlcov/", ".nyc_output/",
    ".build/", "build/", "build-*/", "_build/", "dist/", "DerivedData/", ".swiftpm/", "*.egg-info/", ".eggs/", "*.app/",
    ".DS_Store", "*.pyc", "*.pyo", "*.tsbuildinfo", "next-env.d.ts", ".coverage", "*.swp",
)


class Refused(Exception):
    """The gate said no. Carries every reason, so one run shows them all."""

    def __init__(self, reasons):
        super().__init__("; ".join(reasons))
        self.reasons = list(reasons)


class Uncertain(Exception):
    """A merge was requested and GitHub did not confirm it."""


def run(args, cwd=None, check=True):
    proc = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:] or [""]
        raise RuntimeError(f"`{' '.join(args[:3])} …` exited {proc.returncode}: {tail[0]}")
    return proc


def git(*args, cwd=None):
    return run(["git", *args], cwd=cwd).stdout.strip()


def git_ok(*args, cwd=None):
    return run(["git", *args], cwd=cwd, check=False).returncode == 0


def gh_json(*args):
    return json.loads(run(["gh", *args]).stdout or "null")


READER_GONE = False


def say(text=""):
    """Print a line while somebody reads. A closed stdout silences the gate; it never stops it."""
    global READER_GONE
    if READER_GONE:
        return
    try:
        print(text, flush=True)
    except OSError:
        # `| head`, `| grep -q`: the reader left. After a merge what is left to
        # do is the teardown, and it cannot depend on an audience. stdout is
        # pointed at /dev/null so the interpreter's own flush at exit does not
        # fail as well and replace the exit status with 120.
        READER_GONE = True
        try:
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError):
            pass


class Repo:
    def __init__(self):
        self.top = git("rev-parse", "--show-toplevel")
        git_dir = os.path.realpath(git("rev-parse", "--absolute-git-dir"))
        self.common = os.path.realpath(os.path.join(self.top, git("rev-parse", "--git-common-dir", cwd=self.top)))
        # Only in the main checkout is the git directory the common one.
        self.is_main_checkout = git_dir == self.common
        url = run(["git", "remote", "get-url", "origin"], cwd=self.top, check=False).stdout.strip()
        match = re.search(r"github\.com[:/]+([^/]+/[^/]+?)(?:\.git)?/?$", url)
        self.slug = match.group(1) if match else None
        self.gate_id = os.path.relpath(os.path.realpath(__file__), os.path.realpath(self.top))


def load_config():
    cfg = dict(DEFAULTS)
    path = Path(__file__).resolve().with_name("merge-pr.json")
    if path.exists():
        cfg.update(json.loads(path.read_text()))
    return cfg


# ------------------------------------------------------------------ inspection
def check_states(rollup):
    """statusCheckRollup -> sorted [(name, STATE)]; one vocabulary for check runs and commit statuses."""
    out = []
    for item in rollup or []:
        name = item.get("name") or item.get("context") or "?"
        if item.get("status") is not None:          # a check run
            state = item.get("conclusion") if item["status"] == "COMPLETED" else item["status"]
        else:                                        # a commit status
            state = item.get("state")
        out.append((name, (state or "PENDING").upper()))
    return sorted(out)


def marked_private(repo, head, path):
    """True when the file at `head` opens with frontmatter that says `private: true`, at any depth."""
    proc = subprocess.run(["git", "show", f"{head}:{path}"], cwd=repo.top,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    lines = proc.stdout.decode("utf-8", "replace").splitlines() if proc.returncode == 0 else []
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        if line.strip() == "---":
            return False
        if re.match(r"(?i)^\s*private\s*:\s*[\"']?true[\"']?\s*(#.*)?$", line):
            return True
    return False


def changed_paths(repo, span):
    """Every path the diff touches, both ends of a move, each as git stores the name."""
    # --no-renames: a moved file is also a deletion at its old path, and a rule
    # about where a diff may reach has to see that end too. -z: without it git
    # quotes a name that has a non-ASCII byte, and the quoted form matches no
    # prefix and no glob.
    proc = subprocess.run(["git", "diff", "--name-only", "-z", "--no-renames", span], cwd=repo.top,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-1:] or [""]
        raise RuntimeError(f"`git diff --name-only …` exited {proc.returncode}: {tail[0]}")
    return [os.fsdecode(raw) for raw in proc.stdout.split(b"\0") if raw]


def beside(repo, name):
    """A file next to this one, as git names it."""
    return os.path.join(os.path.dirname(repo.gate_id), name).replace(os.sep, "/")


def base_scanner(repo, base_sha):
    """The secret scanner the base branch configures, when the base has that file; else None."""
    path = DEFAULTS["secret_scan"]
    proc = run(["git", "show", f"{base_sha}:{beside(repo, 'merge-pr.json')}"], cwd=repo.top, check=False)
    if proc.returncode == 0:
        try:
            path = json.loads(proc.stdout).get("secret_scan", path)
        except (ValueError, AttributeError):
            pass
    return path if git_ok("cat-file", "-e", f"{base_sha}:{path}", cwd=repo.top) else None


def own_rules(repo, cfg, base_sha, changed):
    """The changed paths this run is judged by: the gate, its settings, its contract, the scanner, the workflows."""
    own = {repo.gate_id.replace(os.sep, "/"), beside(repo, "merge-pr.json"), beside(repo, "GATE.md"),
           cfg["secret_scan"], base_scanner(repo, base_sha)}
    return [path for path in changed if path in own or path.startswith(".github/workflows/")]


def snapshot(repo, cfg, number, memory_only):
    """Everything the verdict rests on, read fresh. Returns (state, reasons-to-refuse)."""
    base = cfg["base"]
    run(["git", "fetch", "--quiet", "origin", base], cwd=repo.top)
    pr = gh_json("pr", "view", str(number), "--repo", repo.slug, "--json",
                 "number,title,state,isDraft,headRefName,headRefOid,baseRefName,"
                 "isCrossRepository,mergeable,statusCheckRollup")
    head = pr["headRefOid"]
    base_sha = git("rev-parse", f"origin/{base}", cwd=repo.top)
    checks = check_states(pr.get("statusCheckRollup"))
    reasons = []

    # Clause 2: mergeable in the plain sense.
    if pr["state"] != "OPEN":
        reasons.append(f"the pull request is {pr['state']}, not OPEN")
    if pr.get("isDraft"):
        reasons.append("the pull request is a draft; draft is reserved for parked work")
    if pr.get("isCrossRepository"):
        reasons.append("the pull request comes from another repository")
    if pr["baseRefName"] != base:
        reasons.append(f"the pull request targets {pr['baseRefName']}, not {base}")
    if pr.get("mergeable") == "CONFLICTING":
        reasons.append(f"the pull request conflicts with {base}")
    elif pr.get("mergeable") != "MERGEABLE":
        reasons.append(f"GitHub has not computed mergeability yet ({pr.get('mergeable')}); run again in a moment")

    # Clause 5: where the gate is standing.
    if repo.is_main_checkout:
        reasons.append("this is the shared main checkout; run the gate from the pull request's own worktree")
    here = git("rev-parse", "HEAD", cwd=repo.top)
    if here != head:
        reasons.append(f"this worktree is at {here[:10]} and the pull request head is {head[:10]}")
    if git("status", "--porcelain", cwd=repo.top):
        reasons.append("this worktree has uncommitted or untracked changes")

    # Clause 3: checks are green, and exist. A check the repository lists as
    # advisory may have failed, but it must have finished: a result that can
    # still change is no result, and the two snapshots could not agree on it.
    by_name = dict(checks)
    advisory = set(cfg["advisory_checks"]) - set(cfg["required_checks"])
    failing, tolerated = [], []
    for name, state in checks:
        if state in SUCCESS | DID_NOT_RUN:
            continue
        if name in advisory and state not in UNFINISHED:
            tolerated.append(f"{name} is {state}")
        else:
            failing.append(f"{name} is {state}")
    if failing:
        reasons.append("checks are not all successful: " + "; ".join(failing))
    elif checks and not any(state in SUCCESS for name, state in checks if name not in advisory):
        reasons.append("every reported check was skipped, so nothing ran")
    for name in cfg["required_checks"]:
        if by_name.get(name) not in SUCCESS:
            reasons.append(f"required check '{name}' is {by_name.get(name, 'absent')}")

    changed, rules = [], []
    if git_ok("cat-file", "-e", head + "^{commit}", cwd=repo.top):
        if not checks and git("ls-tree", "-r", "--name-only", head, "--", ".github/workflows", cwd=repo.top):
            reasons.append("no checks are reported and this repository has workflow files; "
                           "that cannot be told from CI never having run")
        # Clause 4: current base.
        if cfg["require_current_base"] and not git_ok("merge-base", "--is-ancestor", base_sha, head, cwd=repo.top):
            reasons.append(f"the head does not contain the current {base} ({base_sha[:10]}); "
                           f"merge {base} in, push, and let the checks run again")
        changed = changed_paths(repo, f"{base_sha}...{head}")
        rules = own_rules(repo, cfg, base_sha, changed)
        for name, globs in cfg["path_filtered_checks"].items():
            touched = any(fnmatch.fnmatch(path, glob) for path in changed for glob in globs)
            if touched and by_name.get(name) not in SUCCESS:
                reasons.append(f"the diff touches paths that trigger '{name}', which is {by_name.get(name, 'absent')}")
        # Clause 11: memory-only.
        if memory_only:
            outside = [path for path in changed if not path.startswith(cfg["memory_path"])]
            if outside:
                reasons.append(f"memory-only: the diff touches paths outside {cfg['memory_path']}: "
                               + ", ".join(outside[:5]))
            if not changed:
                reasons.append("memory-only: the diff is empty")
        # Clause 11, in every mode: a note marked private is never published.
        private = [path for path in changed
                   if path.startswith(cfg["memory_path"]) and marked_private(repo, head, path)]
        if private:
            reasons.append("the diff publishes memory marked `private: true`: " + ", ".join(private[:5])
                           + ". Move it out of the tracked store, to a path this repository ignores")
    else:
        reasons.append(f"the pull request head {head[:10]} is not in this repository's object store; fetch it")

    state = {"head": head, "base": base_sha, "checks": checks, "tolerated": tolerated, "rules": rules,
             "title": pr["title"], "branch": pr["headRefName"]}
    return state, reasons


def note_rules(state):
    """Clause 6: the verdict is reached under the head's own rules, so say when the head changes them."""
    if state["rules"]:
        say("gate: NOTE this pull request changes the rules it is judged by: " + ", ".join(state["rules"]))
        say("gate: NOTE   this verdict was reached under the pull request's own version of them; "
            "read those changes before giving the word")


def local_phase(repo, cfg, state, memory_only):
    """Clauses 5 and 6: what only a checkout can verify. Returns reasons-to-refuse."""
    reasons = []
    span = f"{state['base']}...{state['head']}"
    if not git_ok("diff", "--check", span, cwd=repo.top):
        reasons.append("git diff --check found whitespace errors or conflict markers")

    scanner = os.path.join(repo.top, cfg["secret_scan"])
    on_base = base_scanner(repo, state["base"])
    if on_base and not git_ok("cat-file", "-e", f"{state['head']}:{cfg['secret_scan']}", cwd=repo.top):
        # A repository that never had a scanner is scanned by nothing, and says
        # so below. One whose base has it and whose head does not is a diff that
        # takes the scan away from itself. Asked of the head's tree, not of the
        # checkout: an ignored file left at that path is not the scanner.
        reasons.append(f"the secret scanner {on_base} exists on {cfg['base']} and this pull request's head "
                       f"has none at {cfg['secret_scan']}; a diff that removes its own scan is not merged unscanned")
    elif os.path.isfile(scanner):
        proc = run(["sh", scanner, "--range", span], cwd=repo.top, check=False)
        if proc.returncode != 0:
            reasons.append("the secret scan refused the diff:\n" + (proc.stderr or proc.stdout).strip())
        else:
            say("gate: secret scan passed")
    elif memory_only:
        reasons.append(f"memory-only needs the secret scanner, and {cfg['secret_scan']} does not exist")
    else:
        say(f"gate: NOTE no secret scanner at {cfg['secret_scan']}; the diff was not scanned")

    for command in cfg["local_checks"]:
        say(f"gate: local check: {command}")
        if subprocess.run(command, shell=True, cwd=repo.top).returncode != 0:
            reasons.append(f"local check failed: {command}")
            break
    return reasons


def squash_message(repo, state):
    """The squash body: what the commits said, their co-author trailers, and the receipt."""
    shas = git("rev-list", "--reverse", "--no-merges", f"{state['base']}..{state['head']}", cwd=repo.top).split()
    subjects, bodies, trailers = [], [], []
    for sha in shas:
        lines = git("show", "-s", "--format=%B", sha, cwd=repo.top).splitlines()
        subjects.append(lines[0] if lines else "")
        kept = []
        for line in lines[1:]:
            if re.match(r"(?i)^co-authored-by:\s*\S", line):
                if line.strip() not in trailers:
                    trailers.append(line.strip())
            else:
                kept.append(line)
        bodies.append("\n".join(kept).strip())
    body = bodies[0] if len(shas) == 1 else "\n".join(f"* {subject}" for subject in subjects)
    trailers.append(f"Gated-By: {repo.gate_id} {CONTRACT} {state['head']}")
    return (body + "\n\n" if body else "") + "\n".join(trailers)


def merge(repo, number, state, message):
    """Clauses 8 and 9: squash with the head pinned, then believe only the readback."""
    proc = run(["gh", "api", "--method", "PUT", f"repos/{repo.slug}/pulls/{number}/merge",
                "-f", f"sha={state['head']}", "-f", "merge_method=squash",
                "-f", f"commit_title={state['title']} (#{number})",
                "-f", f"commit_message={message}"], check=False)
    # A non-zero exit is data, not a verdict: gh has exited non-zero on merges
    # that happened and zero on ones that had not registered yet.
    seen = {}
    for _ in range(5):
        try:
            seen = gh_json("pr", "view", str(number), "--repo", repo.slug, "--json", "state,mergedAt,mergeCommit")
        except RuntimeError:
            seen = {"state": "unreadable"}   # a failed read after a merge request is doubt, not a refusal
        if seen.get("state") == "MERGED" and seen.get("mergedAt") and (seen.get("mergeCommit") or {}).get("oid"):
            return seen
        if proc.returncode != 0 and seen.get("state") == "OPEN":
            detail = (proc.stderr or proc.stdout).strip().splitlines()[-1:] or ["no message"]
            raise Refused([f"GitHub refused the merge: {detail[0]}"])
        time.sleep(1)
    raise Uncertain(f"merge requested, but the pull request reads {seen.get('state')} with "
                    f"mergedAt={seen.get('mergedAt')}. Inspect it before running anything again.")


# -------------------------------------------------------------------- teardown
def inside(child, parent):
    return child == parent or child.startswith(parent.rstrip(os.sep) + os.sep)


def worktrees(repo):
    out, cur = [], None
    for line in git("worktree", "list", "--porcelain", cwd=repo.top).splitlines():
        if line.startswith("worktree "):
            cur = {"path": line[9:], "branch": None, "main": not out, "locked": None}
            out.append(cur)
        elif cur and line.startswith("branch refs/heads/"):
            cur["branch"] = line[len("branch refs/heads/"):]
        elif cur and line.startswith("locked"):
            cur["locked"] = line[6:].strip() or "no reason given"
    return out


def busy_paths():
    """Working directories of every other process, or None when they cannot be listed."""
    try:
        proc = subprocess.run(["lsof", "-a", "-d", "cwd", "-Fpn"], text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        text = proc.stdout   # lsof exits 1 when it could not see some process, and still lists the rest
    except FileNotFoundError:
        text = ""
        for entry in Path("/proc").glob("[0-9]*"):
            try:
                text += f"p{entry.name}\nn{os.readlink(entry / 'cwd')}\n"
            except OSError:
                pass
    if not text:
        return None
    paths, pid = [], None
    for line in text.splitlines():
        if line.startswith("p"):
            pid = line[1:]
        elif line.startswith("n") and pid != str(os.getpid()):
            paths.append(os.path.realpath(line[1:]))
    return paths


def registered_trees(repo, base):
    """Rule 11: {real path: "kind K, owner O"} for every worktree that worktrees.tsv sanctions."""
    # Read as the worktree classifier reads it: the copy on the base branch
    # united with the main checkout's working copy. The checkout may sit on a
    # stale branch, and the base lacks a row that has not landed yet; a row can
    # only ever protect, so either copy naming a tree is enough.
    main = worktrees(repo)[0]["path"]
    proc = subprocess.run(["git", "show", f"origin/{base}:worktrees.tsv"], cwd=repo.top,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    copies = [proc.stdout] if proc.returncode == 0 else []
    try:
        copies.append(Path(main, "worktrees.tsv").read_bytes())
    except OSError:
        pass
    rows = {}
    for line in b"\n".join(copies).decode("utf-8", "replace").splitlines():
        fields = line.split("\t") + ["", "", ""]
        if not fields[0].strip() or fields[0].lstrip().startswith("#") or fields[0] == "path":
            continue
        path = os.path.join(os.path.expanduser("~"), fields[0][2:]) if fields[0].startswith("~/") else fields[0]
        rows[os.path.realpath(os.path.join(main, path))] = f"kind {fields[2] or '-'}, owner {fields[3] or '-'}"
    return rows


def registry_row(registered, path):
    """The row of worktrees.tsv that names the tree at `path`, however the row spells it; None when none does."""
    real = os.path.realpath(path)
    if real in registered:
        return registered[real]
    # realpath keeps the case that was typed, and whether .worktrees/casetree
    # is .worktrees/CaseTree is the volume's to say. So the filesystem is
    # asked, as the worktree classifier asks it with -ef: two names, one
    # directory. The comparison above still holds a tree whose directory is
    # gone, which no filesystem can be asked about.
    for listed, row in registered.items():
        try:
            if os.path.samefile(listed, real):
                return row
        except OSError:
            pass   # one of the two is not there, so they are not one directory
    return None


def hidden_edits(path):
    """Tracked files in the tree at `path` edited behind skip-worktree or assume-unchanged, by name."""
    # `git status` shows none of them, and `git worktree remove` reads the same
    # two bits, so it deletes such a file without --force. `ls-files -v` tags
    # the marked entries (lower case is assume-unchanged, S is skip-worktree)
    # and -s puts the blob the index holds beside each. A marked file is hidden
    # work only when it differs from that blob: one that is absent is what
    # sparse checkout leaves behind, and a symlink is a pointer. The worktree
    # classifier asks the same question the same way.
    proc = subprocess.run(["git", "ls-files", "-v", "-s", "-z"], cwd=path,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-1:] or [""]
        raise RuntimeError(f"`git ls-files -v …` exited {proc.returncode}: {tail[0]}")
    edited = []
    for entry in proc.stdout.split(b"\0"):
        meta, _, name = entry.partition(b"\t")
        fields = meta.split()
        if len(fields) < 3 or not (fields[0].islower() or fields[0] == b"S"):
            continue
        rel = os.fsdecode(name)
        full = os.path.join(path, rel)
        if os.path.islink(full) or not os.path.isfile(full):
            continue
        # hash-object runs the path's clean filters, so line endings and an LFS
        # pointer hash to what the index has and only an edit differs. A file
        # that could not be hashed has not been shown to be unedited: it counts.
        if run(["git", "hash-object", "--", rel], cwd=path, check=False).stdout.strip() != fields[2].decode():
            edited.append(name.decode("utf-8", "replace"))
    return edited


def among(hidden):
    """The end of a reason that calls a tree unclean: the edits `git status`, which its reader runs next, omits."""
    if not hidden:
        return ""
    more = f", +{len(hidden) - 3} more" if len(hidden) > 3 else ""
    return (f", among them {len(hidden)} that `git status` does not show (skip-worktree or assume-unchanged): "
            + ", ".join(hidden[:3]) + more)


def plan_teardown(repo, branch, merged_head, number, registered):
    """Clause 10 as a list of actions; nothing here changes anything."""
    if not git_ok("show-ref", "--verify", "--quiet", f"refs/heads/{branch}", cwd=repo.top):
        return [{"kind": "note", "text": f"no local branch {branch}"}]
    if not git_ok("cat-file", "-e", merged_head + "^{commit}", cwd=repo.top):
        run(["git", "fetch", "--quiet", "origin", f"refs/pull/{number}/head"], cwd=repo.top, check=False)
    # Contained, not equal: after an update-branch the local tip trails the merged head.
    if not git_ok("merge-base", "--is-ancestor", f"refs/heads/{branch}", merged_head, cwd=repo.top):
        return [{"kind": "keep-branch", "branch": branch,
                 "why": "it has commits the merged head does not contain; they would be lost"}]

    actions, blocked, busy, busy_read = [], False, None, False
    caller = os.path.realpath(os.getcwd())
    for tree in [t for t in worktrees(repo) if t["branch"] == branch]:
        exists = os.path.isdir(tree["path"])
        path = os.path.realpath(tree["path"]) if exists else tree["path"]
        hidden = hidden_edits(path) if exists else []
        dirty = not exists or bool(hidden or git("status", "--porcelain", cwd=path))
        row = registry_row(registered, tree["path"])
        why = None
        if row and (tree["main"] or dirty or not inside(caller, path)):
            # The registry is the single sanction for a long-lived tree, so
            # nothing a merge proves removes one or marks it for removal. Run
            # from it, the gate still lets go of the branch, as from any tree.
            why = f"listed in worktrees.tsv ({row})"
        elif tree["main"]:
            why = "it is the main checkout; the operator switches it back"
        elif inside(caller, path):
            if dirty:
                why = "the gate is running from it and it has uncommitted changes" + among(hidden)
            else:
                actions.append({"kind": "detach", "path": path, "registered": row})
                continue
        elif dirty:
            why = "it has uncommitted or untracked changes" + among(hidden)
        elif tree["locked"]:
            why = f"it is locked ({tree['locked']})"
        else:
            if not busy_read:
                busy, busy_read = busy_paths(), True
            if busy is None:
                why = "other processes could not be listed, so nobody can be proven absent"
            elif any(inside(p, path) for p in busy):
                why = "another process has its working directory inside it"
        if why:
            blocked = True
            actions.append({"kind": "keep-worktree", "path": path, "why": why, "registered": row})
        else:
            actions.append({"kind": "remove", "path": path})
    if blocked:
        actions.append({"kind": "keep-branch", "branch": branch, "why": "a worktree still has it checked out"})
    else:
        actions.append({"kind": "delete-branch", "branch": branch})
    return actions


def mark(path, number, head, merge_commit, gate_id):
    """Rule 6: write LANDED where the next session and the sweeper look for it."""
    git_dir = git("rev-parse", "--absolute-git-dir", cwd=path)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    Path(git_dir, "lifecycle").write_text(
        f"state\tLANDED\npr\t{number}\nhead\t{head}\nmerge\t{merge_commit}\nat\t{stamp}\nby\t{gate_id}\n")


def regenerable(rel):
    """True when the name alone says a build or a cache wrote this ignored path."""
    name = rel.rstrip("/").rsplit("/", 1)[-1] + ("/" if rel.endswith("/") else "")
    return any(fnmatch.fnmatchcase(name, glob) for glob in REGENERABLE) or ("/" + rel).endswith("/.meteor/local/")


def backup_ignored(repo, path, number):
    """`git worktree remove` deletes ignored files without a word; copy the ones nothing can rebuild."""
    # `status --ignored=matching` names the path an ignore pattern matched and
    # nothing above it. `ls-files --ignored --directory` also names every parent
    # that holds only ignored content, so a pkg/ with nothing in it but a
    # __pycache__/ was copied whole.
    listed = run(["git", "status", "--porcelain", "-z", "--untracked-files=normal", "--ignored=matching"],
                 cwd=path).stdout.split("\0")
    main = worktrees(repo)[0]["path"]
    keep = []
    for rel in (entry[3:] for entry in listed if entry.startswith("!! ")):
        src, twin = os.path.join(path, rel.rstrip("/")), os.path.join(main, rel)
        # A build or cache name, or a symlink: removal deletes the pointer, not
        # what it names.
        if regenerable(rel) or os.path.islink(src):
            continue
        # A file identical to the same path in the main checkout, which is where
        # a worktree's .env is copied from: the bytes stay there, and a backup
        # would only be one more copy of a secret.
        if os.path.isfile(src) and os.path.isfile(twin) and filecmp.cmp(src, twin, shallow=False):
            continue
        keep.append(rel)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = os.path.join(repo.common, "worktree-backups", f"merge-pr-{number}-{stamp}", os.path.basename(path))
    os.makedirs(dest, exist_ok=True)
    for rel in keep:
        src, dst = os.path.join(path, rel), os.path.join(dest, rel.rstrip("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst, follow_symlinks=False)
    Path(dest, "TEARDOWN.txt").write_text(f"pull request #{number}\nworktree {path}\n")
    return len(keep), dest


def teardown(repo, base, branch, merged_head, merge_commit, number, execute):
    """Clause 10. Every destructive step is the non-forcing form, so git itself is the last guard."""
    registered = registered_trees(repo, base)
    actions = plan_teardown(repo, branch, merged_head, number, registered)
    verb = "" if execute else "would "
    # The tree the gate runs from is marked whether or not it holds the branch.
    # A disposable tree detached at the head has commits that are on no origin
    # ref once the branch is deleted, and the mark is what says they landed. So
    # it is written only where that is proven: a clean tree with nothing the
    # merged head does not contain. First, so a later step that stops the
    # teardown does not cost the mark.
    here = os.path.realpath(repo.top)
    planned = {os.path.realpath(action["path"]) for action in actions if action.get("path")}
    if (not repo.is_main_checkout and not registry_row(registered, here) and here not in planned
            and not git("status", "--porcelain", cwd=here) and not hidden_edits(here)
            and git_ok("merge-base", "--is-ancestor", "HEAD", merged_head, cwd=here)):
        say(f"teardown: {verb}mark LANDED {here} (the gate runs from it, so it stays)")
        if execute:
            mark(here, number, merged_head, merge_commit, repo.gate_id)
    released = True
    for action in actions:
        kind = action["kind"]
        if kind == "note":
            say(f"teardown: {action['text']}")
        elif kind in ("keep-worktree", "keep-branch"):
            what = action.get("path") or f"branch {action['branch']}"
            say(f"teardown: {verb}keep {what}: {action['why']}")
            if (execute and kind == "keep-worktree" and not action.get("registered")
                    and os.path.isdir(action["path"])):
                mark(action["path"], number, merged_head, merge_commit, repo.gate_id)
        elif kind == "detach" and action.get("registered"):
            say(f"teardown: {verb}detach {action['path']} and leave it unmarked: "
                f"listed in worktrees.tsv ({action['registered']})")
            if execute:
                run(["git", "switch", "--quiet", "--detach"], cwd=action["path"])
        elif kind == "detach":
            say(f"teardown: {verb}detach and mark LANDED {action['path']} (the gate runs from it, so it stays)")
            if execute:
                run(["git", "switch", "--quiet", "--detach"], cwd=action["path"])
                mark(action["path"], number, merged_head, merge_commit, repo.gate_id)
        elif kind == "remove":
            say(f"teardown: {verb}remove worktree {action['path']}")
            if execute:
                try:
                    count, dest = backup_ignored(repo, action["path"], number)
                    if count:
                        say(f"teardown:   saved {count} ignored path(s) to {dest}")
                    run(["git", "worktree", "remove", action["path"]], cwd=repo.top)
                except (RuntimeError, OSError) as err:
                    released = False
                    say(f"teardown:   kept it: {err}")
        elif kind == "delete-branch":
            if not released:
                say(f"teardown: keep branch {action['branch']}: a worktree removal above did not complete")
                continue
            say(f"teardown: {verb}delete local branch {action['branch']}")
            if execute:
                # -D, because a squash merge is never an ancestor of the base;
                # containment in the merged head is the proof -d cannot see.
                run(["git", "branch", "-D", action["branch"]], cwd=repo.top)

    # The remote branch, on the same proof as the local one: its tip must be
    # contained in the merged head. A commit pushed to it after the merge is in
    # no pull request ref, so deleting the branch would leave it in one clone.
    ref = f"refs/heads/{branch}"
    listed = run(["git", "ls-remote", "--heads", "origin", ref], cwd=repo.top, check=False)
    tip = listed.stdout.split()[0] if listed.returncode == 0 and listed.stdout.strip() else None
    if listed.returncode != 0:
        say(f"teardown: {verb}keep origin/{branch}: origin could not be read")
    elif not tip:
        say(f"teardown: origin/{branch} is already gone")
    else:
        contained = tip == merged_head
        if not contained:
            if not git_ok("cat-file", "-e", merged_head + "^{commit}", cwd=repo.top):
                run(["git", "fetch", "--quiet", "origin", f"refs/pull/{number}/head"], cwd=repo.top, check=False)
            run(["git", "fetch", "--quiet", "origin", ref], cwd=repo.top, check=False)
            contained = git_ok("merge-base", "--is-ancestor", tip, merged_head, cwd=repo.top)
        if not contained:
            say(f"teardown: {verb}keep origin/{branch}: its tip {tip[:10]} could not be shown to be contained "
                f"in the merged head (a push after the merge, or a head that cannot be fetched)")
        else:
            say(f"teardown: {verb}delete origin/{branch}")
            if execute:
                # Leased on the tip just read: a push that lands between the
                # check and the delete makes the remote refuse.
                pushed = run(["git", "push", "--quiet", f"--force-with-lease={ref}:{tip}", "origin", f":{ref}"],
                             cwd=repo.top, check=False)
                if pushed.returncode != 0 and git_ok("ls-remote", "--exit-code", "--heads", "origin", ref,
                                                     cwd=repo.top):
                    say(f"teardown:   could not delete origin/{branch}: {pushed.stderr.strip().splitlines()[-1:]}")
    return actions


# ------------------------------------------------------------------------ main
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pr", type=int, help="pull request number")
    parser.add_argument("--execute", action="store_true", help="merge (or tear down); without it nothing changes")
    parser.add_argument("--memory-only", action="store_true", help="refuse a diff that leaves the memory path")
    parser.add_argument("--teardown-only", action="store_true", help="the pull request is merged; clean up locally")
    args = parser.parse_args(argv)

    repo, cfg = Repo(), load_config()
    result = {"pr": args.pr, "gate": repo.gate_id, "contract": CONTRACT,
              "mode": "execute" if args.execute else "dry-run"}
    try:
        if not repo.slug:
            raise Refused(["origin is not a GitHub remote"])

        if args.teardown_only:
            pr = gh_json("pr", "view", str(args.pr), "--repo", repo.slug, "--json",
                         "state,mergedAt,mergeCommit,headRefName,headRefOid")
            if pr.get("state") != "MERGED" or not pr.get("mergedAt"):
                raise Refused([f"the pull request is {pr.get('state')}; --teardown-only is for a merged one"])
            teardown(repo, cfg["base"], pr["headRefName"], pr["headRefOid"],
                     (pr.get("mergeCommit") or {}).get("oid", "-"), args.pr, args.execute)
            say(json.dumps(result))
            return 0

        first, reasons = snapshot(repo, cfg, args.pr, args.memory_only)
        say(f"gate: #{args.pr} {first['title']}")
        say(f"gate: head {first['head'][:10]} on {first['branch']}, base {first['base'][:10]}, "
            f"{len(first['checks'])} check(s) reported")
        for line in first["tolerated"]:
            say(f"gate: NOTE advisory check not successful, tolerated: {line}")
        note_rules(first)
        if reasons:
            raise Refused(reasons)
        reasons = local_phase(repo, cfg, first, args.memory_only)
        if reasons:
            raise Refused(reasons)
        second, reasons = snapshot(repo, cfg, args.pr, args.memory_only)
        if reasons:
            raise Refused(reasons)
        if second != first:
            raise Refused(["the pull request or the base changed while the gate was checking it; run again"])

        message = squash_message(repo, first)
        result.update(head=first["head"], base=first["base"], checks=len(first["checks"]))
        if not args.execute:
            say("gate: PASSED (dry run). --execute would squash-merge with this message:")
            say("\n".join("    " + line for line in [f"{first['title']} (#{args.pr})", "", *message.splitlines()]))
            # Again, beside the verdict: the local checks may have printed a screenful since the first time.
            note_rules(first)
            teardown(repo, cfg["base"], first["branch"], first["head"], "-", args.pr, False)
            say(json.dumps(result))
            return 0

        merged = merge(repo, args.pr, first, message)
        commit = merged["mergeCommit"]["oid"]
        say(f"gate: MERGED #{args.pr} at {merged['mergedAt']} as {commit[:10]}")
        result.update(merged_at=merged["mergedAt"], merge_commit=commit)
        try:
            teardown(repo, cfg["base"], first["branch"], first["head"], commit, args.pr, True)
        except (RuntimeError, OSError) as err:
            # The merge is done and confirmed; a teardown that stops halfway is
            # debris for the sweeper, not a failed merge.
            say(f"teardown: stopped early: {err}")
            result["teardown_error"] = str(err)
        say(json.dumps(result))
        return 0
    except Refused as refusal:
        say(f"gate: REFUSED #{args.pr}")
        for reason in refusal.reasons:
            say("  - " + reason.replace("\n", "\n    "))
        result["refused"] = refusal.reasons
        say(json.dumps(result))
        return 1
    except Uncertain as doubt:
        say(f"gate: UNCERTAIN #{args.pr}: {doubt}")
        result["uncertain"] = str(doubt)
        say(json.dumps(result))
        return 2
    except RuntimeError as err:
        # git or gh failed before any merge was requested: nothing was verified.
        say(f"gate: REFUSED #{args.pr}")
        say(f"  - could not inspect: {err}")
        result["refused"] = [str(err)]
        say(json.dumps(result))
        return 1


if __name__ == "__main__":
    sys.exit(main())
